"""
Expedia Channel Adapter
=======================

Platform adapter for Expedia Partner Central API integration.

API Documentation: https://developers.expediagroup.com/
Rate Limit: 50 requests/second
Auth: OAuth 2.0 Client Credentials Flow
"""

import hashlib
import hmac
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


class ExpediaAdapter(ChannelAdapter):
    """
    Adapter for Expedia Partner Central API.

    Expedia uses a REST API with OAuth 2.0 Client Credentials authentication.
    The API is shared across Expedia Group properties (Expedia, Hotels.com, Vrbo, etc.)

    Key Endpoints:
    - GET /properties/{propertyId}/bookings - Get bookings
    - PUT /properties/{propertyId}/availability - Update availability
    - PUT /properties/{propertyId}/rates - Update rates
    """

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.EXPEDIA

    @property
    def base_url(self) -> str:
        return "https://services.expediapartnercentral.com/properties"

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
        Update availability on Expedia.

        Uses the availability endpoint with room-level updates.
        """
        self._log_request(
            "PUT",
            f"/{property_id}/availability",
            start_date=str(start_date),
            end_date=str(end_date),
            available=available
        )

        # Build date ranges
        dates = []
        current = start_date
        while current < end_date:
            dates.append({
                "date": current.isoformat(),
                "available": available,
                "minLOS": min_stay or 1,
                "maxLOS": max_stay or 365
            })
            current += timedelta(days=1)

        payload = {
            "roomTypes": [
                {
                    "roomTypeId": "DEFAULT",  # Use default room type
                    "ratePlans": [
                        {
                            "ratePlanId": "DEFAULT",
                            "dates": dates
                        }
                    ]
                }
            ]
        }

        response = await self._make_request(
            method="PUT",
            endpoint=f"/{property_id}/availability",
            json=payload
        )

        self._log_response(response, records_updated=len(dates))

    async def get_availability(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, bool]:
        """Get availability from Expedia."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/{property_id}/availability",
            params={
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat()
            }
        )

        data = response.json()
        availability = {}

        for room_type in data.get("roomTypes", []):
            for rate_plan in room_type.get("ratePlans", []):
                for day in rate_plan.get("dates", []):
                    day_date = date.fromisoformat(day["date"])
                    availability[day_date] = day.get("available", True)

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
        Update pricing for multiple dates on Expedia.
        """
        self._log_request(
            "PUT",
            f"/{property_id}/rates",
            date_count=len(date_prices)
        )

        dates = []
        for rate_date, price in sorted(date_prices.items()):
            dates.append({
                "date": rate_date.isoformat(),
                "baseRate": {
                    "amount": float(price),
                    "currency": currency
                }
            })

        payload = {
            "roomTypes": [
                {
                    "roomTypeId": "DEFAULT",
                    "ratePlans": [
                        {
                            "ratePlanId": "DEFAULT",
                            "dates": dates
                        }
                    ]
                }
            ]
        }

        response = await self._make_request(
            method="PUT",
            endpoint=f"/{property_id}/rates",
            json=payload
        )

        self._log_response(response, records_updated=len(date_prices))

    async def get_pricing(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, Decimal]:
        """Get pricing from Expedia."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/{property_id}/rates",
            params={
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat()
            }
        )

        data = response.json()
        pricing = {}

        for room_type in data.get("roomTypes", []):
            for rate_plan in room_type.get("ratePlans", []):
                for day in rate_plan.get("dates", []):
                    day_date = date.fromisoformat(day["date"])
                    rate = day.get("baseRate", {})
                    if rate:
                        pricing[day_date] = Decimal(str(rate.get("amount", 0)))

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
        Get bookings from Expedia.

        Supports filtering by modified date and status.
        """
        params = {
            "pageSize": 100,
            "pageToken": None
        }

        if since:
            params["modifiedSince"] = since.isoformat() + "Z"
        if status:
            params["status"] = status

        all_bookings = []

        while True:
            response = await self._make_request(
                method="GET",
                endpoint=f"/{property_id}/bookings",
                params={k: v for k, v in params.items() if v is not None}
            )

            data = response.json()
            bookings_data = data.get("bookings", [])

            for booking_data in bookings_data:
                booking = self._map_booking_to_platform_booking(booking_data)
                all_bookings.append(booking)

            # Check for next page
            next_page = data.get("nextPageToken")
            if not next_page or len(bookings_data) < 100:
                break

            params["pageToken"] = next_page

        logger.info(
            "Retrieved Expedia bookings",
            property_id=property_id,
            count=len(all_bookings)
        )

        return all_bookings

    async def get_booking(
        self,
        property_id: str,
        booking_id: str
    ) -> PlatformBooking:
        """Get a single booking by ID."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/{property_id}/bookings/{booking_id}"
        )

        data = response.json()
        return self._map_booking_to_platform_booking(data)

    def _map_booking_to_platform_booking(self, booking: Dict[str, Any]) -> PlatformBooking:
        """Map Expedia booking to PlatformBooking."""
        guest = booking.get("primaryGuest", {})
        stay = booking.get("stayDates", {})
        payment = booking.get("payment", {})

        # Parse dates
        check_in = date.fromisoformat(stay.get("checkIn", ""))
        check_out = date.fromisoformat(stay.get("checkOut", ""))

        # Parse timestamps
        created_at = datetime.fromisoformat(
            booking.get("createdDateTime", datetime.utcnow().isoformat()).replace("Z", "+00:00")
        )
        modified_at = datetime.fromisoformat(
            booking.get("lastModifiedDateTime", created_at.isoformat()).replace("Z", "+00:00")
        )

        # Count guests
        guest_counts = booking.get("guestCounts", {})

        return PlatformBooking(
            channel_booking_id=str(booking.get("bookingId", "")),
            listing_id=str(booking.get("propertyId", "")),
            status=self._map_status(booking.get("status", "PENDING")),
            check_in=check_in,
            check_out=check_out,
            guest_first_name=guest.get("firstName", ""),
            guest_last_name=guest.get("lastName", ""),
            guest_email=guest.get("email", ""),
            guest_phone=guest.get("phone", {}).get("number", None),
            num_guests=guest_counts.get("adults", 1) + guest_counts.get("children", 0),
            num_adults=guest_counts.get("adults", 1),
            num_children=guest_counts.get("children", 0),
            num_infants=guest_counts.get("infants", 0),
            total_price=Decimal(str(payment.get("totalAmount", {}).get("amount", 0))),
            currency=payment.get("totalAmount", {}).get("currency", "EUR"),
            booked_at=created_at,
            updated_at=modified_at,
            special_requests=booking.get("specialRequests", None),
            channel_guest_id=str(guest.get("guestId", "")),
            channel_data=booking
        )

    def _map_status(self, expedia_status: str) -> str:
        """Map Expedia status to standardized status."""
        status_map = {
            "PENDING": "pending",
            "CONFIRMED": "confirmed",
            "CANCELLED": "cancelled",
            "COMPLETED": "checked_out",
            "NO_SHOW": "no_show",
            "IN_HOUSE": "checked_in"
        }
        return status_map.get(expedia_status.upper(), "pending")

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
        Verify Expedia webhook signature.

        Expedia uses HMAC-SHA256 for webhook signatures.
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
        """Parse Expedia webhook payload."""
        event_type = payload.get("eventType", "")
        event_id = payload.get("eventId", "")
        timestamp_str = payload.get("timestamp", datetime.utcnow().isoformat())

        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            timestamp = datetime.utcnow()

        return WebhookEvent(
            event_type=self._map_event_type(event_type),
            event_id=event_id,
            timestamp=timestamp,
            payload=payload
        )

    def _map_event_type(self, expedia_event_type: str) -> str:
        """Map Expedia event types to standardized types."""
        event_map = {
            "BOOKING_CREATED": "booking.created",
            "BOOKING_MODIFIED": "booking.updated",
            "BOOKING_CANCELLED": "booking.cancelled",
            "BOOKING_COMPLETED": "booking.checked_out",
            "BOOKING_NO_SHOW": "booking.no_show"
        }
        return event_map.get(expedia_event_type, expedia_event_type)

    # =========================================================================
    # PROPERTY MANAGEMENT
    # =========================================================================

    async def get_property(self, property_id: str) -> Dict[str, Any]:
        """Get property details."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/{property_id}"
        )
        return response.json()

    async def get_room_types(self, property_id: str) -> List[Dict[str, Any]]:
        """Get room types for a property."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/{property_id}/roomTypes"
        )
        return response.json().get("roomTypes", [])

    async def get_rate_plans(self, property_id: str) -> List[Dict[str, Any]]:
        """Get rate plans for a property."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/{property_id}/ratePlans"
        )
        return response.json().get("ratePlans", [])

    # =========================================================================
    # CONTENT SYNC
    # =========================================================================

    async def update_property_content(
        self,
        property_id: str,
        content: Dict[str, Any]
    ) -> None:
        """
        Update property content (description, amenities, images, etc.)
        """
        response = await self._make_request(
            method="PATCH",
            endpoint=f"/{property_id}",
            json=content
        )

        if response.status_code not in [200, 204]:
            raise ChannelAdapterError(
                f"Failed to update property content: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text
            )

    async def upload_image(
        self,
        property_id: str,
        image_url: str,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload an image to the property."""
        payload = {
            "imageUrl": image_url,
            "caption": caption
        }

        response = await self._make_request(
            method="POST",
            endpoint=f"/{property_id}/images",
            json=payload
        )

        return response.json()
