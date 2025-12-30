"""
Booking.com Channel Adapter
===========================

Platform adapter for Booking.com API integration.

API Documentation: https://developers.booking.com/
Rate Limit: Variable (based on partnership tier)
Auth: OAuth 2.0 or Basic Auth (legacy)
Data Format: REST + XML (legacy endpoints)
"""

import hashlib
import hmac
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import httpx
import structlog

from .base_adapter import (
    ChannelAdapter,
    ChannelType,
    PlatformBooking,
    WebhookEvent,
    ChannelAdapterError,
)

logger = structlog.get_logger(__name__)


class BookingComAdapter(ChannelAdapter):
    """
    Adapter for Booking.com API.

    Booking.com uses a mix of REST and XML APIs:
    - XML API for availability and rate updates
    - REST API for reservation retrieval
    - Push notifications for real-time booking updates

    Key Endpoints:
    - POST /availability - Update room availability
    - GET /reservations - Get reservations
    - POST /rates - Update rates
    """

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.BOOKING_COM

    @property
    def base_url(self) -> str:
        return "https://distribution-xml.booking.com/2.0"

    @property
    def rest_base_url(self) -> str:
        return "https://partner.booking.com/json"

    # =========================================================================
    # AVAILABILITY MANAGEMENT
    # =========================================================================

    async def update_availability(
        self,
        property_id: str,
        start_date: date,
        end_date: date,
        available: bool,
        min_stay: Optional[int] = None,
        max_stay: Optional[int] = None
    ) -> None:
        """
        Update availability on Booking.com using OTA_HotelAvailNotifRQ.

        Booking.com uses XML format for availability updates.
        """
        self._log_request(
            "POST",
            "/availability",
            start_date=str(start_date),
            end_date=str(end_date),
            available=available
        )

        # Build XML request
        xml_request = self._build_availability_xml(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            available=available,
            min_stay=min_stay,
            max_stay=max_stay
        )

        response = await self._make_xml_request(
            endpoint="/availability",
            xml_body=xml_request
        )

        self._validate_xml_response(response)
        self._log_response(response, records_updated=1)

    def _build_availability_xml(
        self,
        property_id: str,
        start_date: date,
        end_date: date,
        available: bool,
        min_stay: Optional[int] = None,
        max_stay: Optional[int] = None
    ) -> str:
        """Build OTA_HotelAvailNotifRQ XML."""
        rooms_to_sell = "1" if available else "0"

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<OTA_HotelAvailNotifRQ xmlns="http://www.opentravel.org/OTA/2003/05"
                       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                       Version="1.0"
                       TimeStamp="{datetime.utcnow().isoformat()}Z">
    <AvailStatusMessages HotelCode="{property_id}">
        <AvailStatusMessage>
            <StatusApplicationControl Start="{start_date.isoformat()}"
                                       End="{end_date.isoformat()}"
                                       InvTypeCode="ROOM"
                                       RatePlanCode="DEFAULT"/>
            <LengthsOfStay>
                <LengthOfStay MinMaxMessageType="MinLOS" Time="{min_stay or 1}"/>
                {f'<LengthOfStay MinMaxMessageType="MaxLOS" Time="{max_stay}"/>' if max_stay else ''}
            </LengthsOfStay>
            <BookingLimit>{rooms_to_sell}</BookingLimit>
        </AvailStatusMessage>
    </AvailStatusMessages>
</OTA_HotelAvailNotifRQ>"""
        return xml

    async def get_availability(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, bool]:
        """
        Get availability from Booking.com.

        Uses OTA_HotelAvailRQ to retrieve current availability.
        """
        xml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<OTA_HotelAvailRQ xmlns="http://www.opentravel.org/OTA/2003/05"
                  Version="1.0"
                  TimeStamp="{datetime.utcnow().isoformat()}Z">
    <AvailRequestSegments>
        <AvailRequestSegment>
            <HotelSearchCriteria>
                <Criterion>
                    <HotelRef HotelCode="{property_id}"/>
                </Criterion>
            </HotelSearchCriteria>
            <StayDateRange Start="{start_date.isoformat()}" End="{end_date.isoformat()}"/>
        </AvailRequestSegment>
    </AvailRequestSegments>
</OTA_HotelAvailRQ>"""

        response = await self._make_xml_request(
            endpoint="/availability/get",
            xml_body=xml_request
        )

        return self._parse_availability_response(response.text)

    def _parse_availability_response(self, xml_text: str) -> Dict[date, bool]:
        """Parse OTA_HotelAvailRS XML response."""
        availability = {}

        root = ET.fromstring(xml_text)
        ns = {"ota": "http://www.opentravel.org/OTA/2003/05"}

        for avail_msg in root.findall(".//ota:AvailStatusMessage", ns):
            ctrl = avail_msg.find("ota:StatusApplicationControl", ns)
            if ctrl is not None:
                start = date.fromisoformat(ctrl.get("Start"))
                end = date.fromisoformat(ctrl.get("End"))
                limit = avail_msg.find("ota:BookingLimit", ns)
                is_available = int(limit.text) > 0 if limit is not None else True

                current = start
                while current <= end:
                    availability[current] = is_available
                    current += timedelta(days=1)

        return availability

    # =========================================================================
    # PRICING MANAGEMENT
    # =========================================================================

    async def update_pricing(
        self,
        property_id: str,
        date: date,
        price: Decimal,
        currency: str = "EUR"
    ) -> None:
        """Update pricing for a single date."""
        await self.update_pricing_bulk(
            property_id=property_id,
            date_prices={date: price},
            currency=currency
        )

    async def update_pricing_bulk(
        self,
        property_id: str,
        date_prices: Dict[date, Decimal],
        currency: str = "EUR"
    ) -> None:
        """
        Update pricing for multiple dates using OTA_HotelRatePlanNotifRQ.
        """
        self._log_request(
            "POST",
            "/rates",
            date_count=len(date_prices)
        )

        xml_request = self._build_rates_xml(
            property_id=property_id,
            date_prices=date_prices,
            currency=currency
        )

        response = await self._make_xml_request(
            endpoint="/rates",
            xml_body=xml_request
        )

        self._validate_xml_response(response)
        self._log_response(response, records_updated=len(date_prices))

    def _build_rates_xml(
        self,
        property_id: str,
        date_prices: Dict[date, Decimal],
        currency: str
    ) -> str:
        """Build OTA_HotelRatePlanNotifRQ XML."""
        rate_elements = []

        for rate_date, price in sorted(date_prices.items()):
            rate_elements.append(f"""
        <RatePlanNotifRQ>
            <RatePlans HotelCode="{property_id}">
                <RatePlan RatePlanCode="DEFAULT">
                    <Rates>
                        <Rate Start="{rate_date.isoformat()}" End="{rate_date.isoformat()}">
                            <BaseByGuestAmts>
                                <BaseByGuestAmt AmountAfterTax="{float(price):.2f}"
                                               CurrencyCode="{currency}"
                                               NumberOfGuests="2"/>
                            </BaseByGuestAmts>
                        </Rate>
                    </Rates>
                </RatePlan>
            </RatePlans>
        </RatePlanNotifRQ>""")

        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<OTA_HotelRatePlanNotifRQ xmlns="http://www.opentravel.org/OTA/2003/05"
                          Version="1.0"
                          TimeStamp="{datetime.utcnow().isoformat()}Z">
    {"".join(rate_elements)}
</OTA_HotelRatePlanNotifRQ>"""
        return xml

    async def get_pricing(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, Decimal]:
        """Get pricing from Booking.com."""
        xml_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<OTA_HotelRatePlanRQ xmlns="http://www.opentravel.org/OTA/2003/05"
                     Version="1.0"
                     TimeStamp="{datetime.utcnow().isoformat()}Z">
    <RatePlans>
        <RatePlan HotelCode="{property_id}">
            <DateRange Start="{start_date.isoformat()}" End="{end_date.isoformat()}"/>
        </RatePlan>
    </RatePlans>
</OTA_HotelRatePlanRQ>"""

        response = await self._make_xml_request(
            endpoint="/rates/get",
            xml_body=xml_request
        )

        return self._parse_rates_response(response.text)

    def _parse_rates_response(self, xml_text: str) -> Dict[date, Decimal]:
        """Parse OTA_HotelRatePlanRS XML response."""
        pricing = {}

        root = ET.fromstring(xml_text)
        ns = {"ota": "http://www.opentravel.org/OTA/2003/05"}

        for rate in root.findall(".//ota:Rate", ns):
            start = date.fromisoformat(rate.get("Start"))
            end = date.fromisoformat(rate.get("End"))
            amount_elem = rate.find(".//ota:BaseByGuestAmt", ns)

            if amount_elem is not None:
                amount = Decimal(amount_elem.get("AmountAfterTax", "0"))
                current = start
                while current <= end:
                    pricing[current] = amount
                    current += timedelta(days=1)

        return pricing

    # =========================================================================
    # BOOKING MANAGEMENT
    # =========================================================================

    async def get_bookings(
        self,
        property_id: str,
        since: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> List[PlatformBooking]:
        """
        Get reservations from Booking.com REST API.
        """
        params = {
            "hotel_id": property_id,
            "rows": 100,
            "page": 0
        }

        if since:
            params["changed_since"] = since.strftime("%Y-%m-%d %H:%M:%S")
        if status:
            params["status"] = status

        all_bookings = []
        page = 0

        client = await self.get_client()

        while True:
            params["page"] = page

            response = await client.get(
                f"{self.rest_base_url}/reservations",
                params=params
            )
            response.raise_for_status()

            data = response.json()
            reservations = data.get("reservations", [])

            if not reservations:
                break

            for res in reservations:
                booking = self._map_reservation_to_booking(res)
                all_bookings.append(booking)

            if len(reservations) < 100:
                break

            page += 1

        logger.info(
            "Retrieved Booking.com reservations",
            property_id=property_id,
            count=len(all_bookings)
        )

        return all_bookings

    async def get_booking(
        self,
        property_id: str,
        booking_id: str
    ) -> PlatformBooking:
        """Get a single reservation by ID."""
        client = await self.get_client()

        response = await client.get(
            f"{self.rest_base_url}/reservations/{booking_id}"
        )
        response.raise_for_status()

        data = response.json()
        return self._map_reservation_to_booking(data.get("reservation", data))

    def _map_reservation_to_booking(self, reservation: Dict[str, Any]) -> PlatformBooking:
        """Map Booking.com reservation to PlatformBooking."""
        guest = reservation.get("guest", {})
        room = reservation.get("room", {})

        # Parse dates
        check_in = datetime.strptime(
            reservation.get("arrival_date", ""),
            "%Y-%m-%d"
        ).date()
        check_out = datetime.strptime(
            reservation.get("departure_date", ""),
            "%Y-%m-%d"
        ).date()

        # Parse created/modified timestamps
        created_at = datetime.strptime(
            reservation.get("booked_at", datetime.utcnow().isoformat()),
            "%Y-%m-%dT%H:%M:%S"
        ) if reservation.get("booked_at") else datetime.utcnow()

        modified_at = datetime.strptime(
            reservation.get("modified_at", created_at.isoformat()),
            "%Y-%m-%dT%H:%M:%S"
        ) if reservation.get("modified_at") else created_at

        return PlatformBooking(
            channel_booking_id=str(reservation.get("reservation_id", "")),
            listing_id=str(reservation.get("hotel_id", "")),
            status=self._map_status(reservation.get("status", "new")),
            check_in=check_in,
            check_out=check_out,
            guest_first_name=guest.get("first_name", ""),
            guest_last_name=guest.get("last_name", ""),
            guest_email=guest.get("email", ""),
            guest_phone=guest.get("telephone", None),
            num_guests=room.get("number_of_guests", 2),
            num_adults=room.get("adults", 2),
            num_children=room.get("children", 0),
            num_infants=0,  # Booking.com doesn't separate infants
            total_price=Decimal(str(reservation.get("total_price", 0))),
            currency=reservation.get("currency_code", "EUR"),
            booked_at=created_at,
            updated_at=modified_at,
            special_requests=reservation.get("remarks", None),
            channel_guest_id=str(guest.get("guest_id", "")),
            channel_data=reservation
        )

    def _map_status(self, booking_com_status: str) -> str:
        """Map Booking.com status to standardized status."""
        status_map = {
            "new": "pending",
            "modified": "confirmed",
            "cancelled": "cancelled",
            "no_show": "no_show",
            "ok": "confirmed",
        }
        return status_map.get(booking_com_status.lower(), "pending")

    # =========================================================================
    # WEBHOOK HANDLING
    # =========================================================================

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify Booking.com webhook signature.

        Booking.com uses HMAC-SHA256 for push notification signatures.
        """
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> WebhookEvent:
        """Parse Booking.com push notification payload."""
        # Booking.com sends reservation updates as push notifications
        event_type = self._determine_event_type(payload)

        return WebhookEvent(
            event_type=event_type,
            event_id=str(payload.get("reservation_id", "")),
            timestamp=datetime.utcnow(),
            payload=payload
        )

    def _determine_event_type(self, payload: Dict[str, Any]) -> str:
        """Determine event type from payload."""
        status = payload.get("status", "").lower()

        if status == "new":
            return "booking.created"
        elif status == "modified":
            return "booking.updated"
        elif status == "cancelled":
            return "booking.cancelled"
        elif status == "no_show":
            return "booking.no_show"
        else:
            return "booking.updated"

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    async def _make_xml_request(
        self,
        endpoint: str,
        xml_body: str
    ) -> httpx.Response:
        """Make XML API request to Booking.com."""
        client = await self.get_client()

        headers = {
            "Content-Type": "application/xml",
            "Authorization": f"Bearer {self.access_token}"
        }

        response = await client.post(
            f"{self.base_url}{endpoint}",
            content=xml_body,
            headers=headers
        )

        if response.status_code >= 400:
            raise ChannelAdapterError(
                f"XML API error: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text
            )

        return response

    def _validate_xml_response(self, response: httpx.Response) -> None:
        """Validate XML response for errors."""
        if response.status_code != 200:
            raise ChannelAdapterError(
                f"Booking.com API error: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text
            )

        # Parse XML to check for OTA errors
        try:
            root = ET.fromstring(response.text)
            ns = {"ota": "http://www.opentravel.org/OTA/2003/05"}

            errors = root.findall(".//ota:Error", ns)
            if errors:
                error_msgs = [e.get("ShortText", "Unknown error") for e in errors]
                raise ChannelAdapterError(
                    f"Booking.com OTA errors: {', '.join(error_msgs)}",
                    response_body=response.text
                )

            warnings = root.findall(".//ota:Warning", ns)
            if warnings:
                for warning in warnings:
                    logger.warning(
                        "Booking.com API warning",
                        warning=warning.get("ShortText")
                    )

        except ET.ParseError as e:
            logger.error("Failed to parse XML response", error=str(e))
