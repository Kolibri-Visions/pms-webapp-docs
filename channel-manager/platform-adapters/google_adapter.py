"""
Google Vacation Rentals Channel Adapter
=======================================

Platform adapter for Google Vacation Rentals / Hotel Ads API integration.

Google offers several integration paths:
1. Hotel Center - For property listings
2. Travel Partner API - For availability/pricing/booking
3. XML Feeds - For bulk data updates

API Documentation: https://developers.google.com/hotels
Rate Limit: 100 requests/second
Auth: Service Account (recommended) or OAuth 2.0
"""

import hashlib
import json
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


class GoogleVacationRentalsAdapter(ChannelAdapter):
    """
    Adapter for Google Vacation Rentals.

    Google uses multiple integration methods:
    - Travel Partner API for real-time updates
    - XML/ARI feeds for availability, rates, inventory
    - Hotel Center for property management

    This adapter primarily uses the Travel Partner API for
    real-time availability and pricing updates.
    """

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.GOOGLE

    @property
    def base_url(self) -> str:
        return "https://travelpartner.googleapis.com/v3"

    @property
    def hotel_center_url(self) -> str:
        return "https://hotelcenter.googleapis.com/v1"

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
        Update availability on Google using ARI (Availability, Rates, Inventory).

        Google accepts availability updates via the Transaction message format.
        """
        self._log_request(
            "POST",
            f"/accounts/{self._get_account_id()}/propertyPerformanceReportViews",
            start_date=str(start_date),
            end_date=str(end_date),
            available=available
        )

        # Build ARI transaction
        transaction = self._build_ari_transaction(
            property_id=property_id,
            start_date=start_date,
            end_date=end_date,
            available=available,
            min_stay=min_stay,
            max_stay=max_stay
        )

        response = await self._make_request(
            method="POST",
            endpoint=f"/accounts/{self._get_account_id()}/transactions",
            json=transaction
        )

        self._log_response(response, records_updated=1)

    def _build_ari_transaction(
        self,
        property_id: str,
        start_date: date,
        end_date: date,
        available: bool,
        min_stay: Optional[int] = None,
        max_stay: Optional[int] = None,
        price: Optional[Decimal] = None,
        currency: str = "EUR"
    ) -> Dict[str, Any]:
        """Build ARI transaction for Google."""
        # Generate inventory entries for each date
        inventory_entries = []
        current = start_date
        while current < end_date:
            entry = {
                "date": current.isoformat(),
                "availability": 1 if available else 0,
            }
            if min_stay:
                entry["minimumLengthOfStay"] = min_stay
            if max_stay:
                entry["maximumLengthOfStay"] = max_stay
            if price:
                entry["rate"] = {
                    "amount": float(price),
                    "currency": currency
                }
            inventory_entries.append(entry)
            current += timedelta(days=1)

        return {
            "propertyId": property_id,
            "roomType": "DEFAULT",
            "ratePlan": "DEFAULT",
            "inventoryUpdates": inventory_entries
        }

    async def get_availability(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, bool]:
        """
        Get availability from Google.

        Note: Google's API is primarily write-only for availability.
        This method queries our own records or uses the reporting API.
        """
        # Google doesn't have a direct availability query API
        # We rely on our internal state or use performance reports
        try:
            response = await self._make_request(
                method="GET",
                endpoint=f"/accounts/{self._get_account_id()}/properties/{property_id}/inventory",
                params={
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat()
                }
            )

            data = response.json()
            availability = {}

            for entry in data.get("inventory", []):
                entry_date = date.fromisoformat(entry["date"])
                availability[entry_date] = entry.get("availability", 0) > 0

            return availability

        except ChannelAdapterError:
            # Fallback: assume all dates are available if query fails
            logger.warning(
                "Could not query Google availability, returning empty",
                property_id=property_id
            )
            return {}

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
        Update pricing for multiple dates on Google.

        Uses the Rate Upload API for bulk rate updates.
        """
        self._log_request(
            "POST",
            f"/accounts/{self._get_account_id()}/transactions",
            date_count=len(date_prices)
        )

        # Build rate entries
        rate_entries = []
        for rate_date, price in sorted(date_prices.items()):
            rate_entries.append({
                "date": rate_date.isoformat(),
                "rate": {
                    "amount": float(price),
                    "currency": currency
                }
            })

        transaction = {
            "propertyId": property_id,
            "roomType": "DEFAULT",
            "ratePlan": "DEFAULT",
            "rateUpdates": rate_entries
        }

        response = await self._make_request(
            method="POST",
            endpoint=f"/accounts/{self._get_account_id()}/transactions",
            json=transaction
        )

        self._log_response(response, records_updated=len(date_prices))

    async def get_pricing(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, Decimal]:
        """
        Get pricing from Google.

        Note: Similar to availability, Google's API is write-focused.
        """
        try:
            response = await self._make_request(
                method="GET",
                endpoint=f"/accounts/{self._get_account_id()}/properties/{property_id}/rates",
                params={
                    "startDate": start_date.isoformat(),
                    "endDate": end_date.isoformat()
                }
            )

            data = response.json()
            pricing = {}

            for entry in data.get("rates", []):
                entry_date = date.fromisoformat(entry["date"])
                rate = entry.get("rate", {})
                pricing[entry_date] = Decimal(str(rate.get("amount", 0)))

            return pricing

        except ChannelAdapterError:
            logger.warning(
                "Could not query Google pricing, returning empty",
                property_id=property_id
            )
            return {}

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
        Get bookings from Google.

        Google Vacation Rentals bookings are typically managed through
        the Hotel Center or via the Property Performance API.

        Note: Direct booking retrieval may have limited support depending
        on the integration type (Free Booking Links vs Paid Ads).
        """
        params = {
            "propertyId": property_id,
            "pageSize": 100
        }

        if since:
            params["modifiedAfter"] = since.isoformat() + "Z"
        if status:
            params["status"] = status

        try:
            response = await self._make_request(
                method="GET",
                endpoint=f"/accounts/{self._get_account_id()}/bookings",
                params=params
            )

            data = response.json()
            bookings = []

            for booking_data in data.get("bookings", []):
                booking = self._map_booking_to_platform_booking(booking_data)
                bookings.append(booking)

            logger.info(
                "Retrieved Google bookings",
                property_id=property_id,
                count=len(bookings)
            )

            return bookings

        except ChannelAdapterError as e:
            # Google may not support direct booking queries
            logger.warning(
                "Could not retrieve Google bookings",
                error=str(e)
            )
            return []

    async def get_booking(
        self,
        property_id: str,
        booking_id: str
    ) -> PlatformBooking:
        """Get a single booking by ID."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/accounts/{self._get_account_id()}/bookings/{booking_id}"
        )

        data = response.json()
        return self._map_booking_to_platform_booking(data)

    def _map_booking_to_platform_booking(self, booking: Dict[str, Any]) -> PlatformBooking:
        """Map Google booking to PlatformBooking."""
        guest = booking.get("guest", {})
        stay = booking.get("stay", {})
        pricing = booking.get("pricing", {})

        check_in = date.fromisoformat(stay.get("checkIn", ""))
        check_out = date.fromisoformat(stay.get("checkOut", ""))

        created_at = datetime.fromisoformat(
            booking.get("createdTime", datetime.utcnow().isoformat()).replace("Z", "+00:00")
        )
        modified_at = datetime.fromisoformat(
            booking.get("modifiedTime", created_at.isoformat()).replace("Z", "+00:00")
        )

        return PlatformBooking(
            channel_booking_id=str(booking.get("bookingId", "")),
            listing_id=str(booking.get("propertyId", "")),
            status=self._map_status(booking.get("status", "CONFIRMED")),
            check_in=check_in,
            check_out=check_out,
            guest_first_name=guest.get("firstName", ""),
            guest_last_name=guest.get("lastName", ""),
            guest_email=guest.get("email", ""),
            guest_phone=guest.get("phone", None),
            num_guests=stay.get("numberOfGuests", 2),
            num_adults=stay.get("numberOfAdults", 2),
            num_children=stay.get("numberOfChildren", 0),
            num_infants=0,
            total_price=Decimal(str(pricing.get("totalPrice", {}).get("amount", 0))),
            currency=pricing.get("totalPrice", {}).get("currency", "EUR"),
            booked_at=created_at,
            updated_at=modified_at,
            special_requests=booking.get("specialRequests", None),
            channel_guest_id=str(guest.get("guestId", "")),
            channel_data=booking
        )

    def _map_status(self, google_status: str) -> str:
        """Map Google status to standardized status."""
        status_map = {
            "CONFIRMED": "confirmed",
            "CANCELLED": "cancelled",
            "COMPLETED": "checked_out",
            "NO_SHOW": "no_show"
        }
        return status_map.get(google_status.upper(), "confirmed")

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
        Verify Google webhook signature.

        Google uses JWT tokens for webhook authentication.
        This validates the token against Google's public keys.
        """
        # Google uses JWT validation rather than HMAC
        # In production, validate the JWT against Google's public keys
        try:
            import jwt
            from jwt import PyJWKClient

            jwks_client = PyJWKClient("https://www.googleapis.com/oauth2/v3/certs")
            signing_key = jwks_client.get_signing_key_from_jwt(signature)

            decoded = jwt.decode(
                signature,
                signing_key.key,
                algorithms=["RS256"],
                audience=secret  # Expected audience
            )

            return True

        except Exception as e:
            logger.error("Google JWT verification failed", error=str(e))
            return False

    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> WebhookEvent:
        """Parse Google webhook payload."""
        # Google sends notifications via Cloud Pub/Sub
        message = payload.get("message", {})
        data = message.get("data", {})

        # Decode base64 data if present
        if isinstance(data, str):
            import base64
            data = json.loads(base64.b64decode(data).decode())

        event_type = data.get("eventType", "")
        event_id = message.get("messageId", "")
        timestamp_str = message.get("publishTime", datetime.utcnow().isoformat())

        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except ValueError:
            timestamp = datetime.utcnow()

        return WebhookEvent(
            event_type=self._map_event_type(event_type),
            event_id=event_id,
            timestamp=timestamp,
            payload=data
        )

    def _map_event_type(self, google_event_type: str) -> str:
        """Map Google event types to standardized types."""
        event_map = {
            "BOOKING_CREATED": "booking.created",
            "BOOKING_MODIFIED": "booking.updated",
            "BOOKING_CANCELLED": "booking.cancelled",
            "REVIEW_RECEIVED": "review.created"
        }
        return event_map.get(google_event_type, google_event_type)

    # =========================================================================
    # XML FEED GENERATION
    # =========================================================================

    def generate_ari_xml_feed(
        self,
        property_id: str,
        availability_data: Dict[date, bool],
        pricing_data: Dict[date, Decimal],
        currency: str = "EUR"
    ) -> str:
        """
        Generate ARI (Availability, Rates, Inventory) XML feed.

        This format is used for batch updates to Google.
        """
        root = ET.Element("Transaction", {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "id": f"txn-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        })

        property_data = ET.SubElement(root, "PropertyDataSet")
        prop = ET.SubElement(property_data, "Property", {"id": property_id})

        room_data = ET.SubElement(prop, "RoomData", {"room_id": "DEFAULT"})

        # Add inventory/availability
        for avail_date, available in sorted(availability_data.items()):
            inventory = ET.SubElement(room_data, "Inventory")
            ET.SubElement(inventory, "Date").text = avail_date.isoformat()
            ET.SubElement(inventory, "Availability").text = str(1 if available else 0)

        # Add rates
        for rate_date, price in sorted(pricing_data.items()):
            rate = ET.SubElement(room_data, "Rate")
            ET.SubElement(rate, "Date").text = rate_date.isoformat()
            base_rate = ET.SubElement(rate, "BaseRate", {"currency": currency})
            base_rate.text = str(float(price))

        return ET.tostring(root, encoding="unicode", method="xml")

    async def upload_ari_feed(
        self,
        xml_feed: str
    ) -> Dict[str, Any]:
        """
        Upload ARI XML feed to Google.

        This is an alternative to real-time API updates for bulk operations.
        """
        response = await self._make_request(
            method="POST",
            endpoint=f"/accounts/{self._get_account_id()}/ariFeed",
            content=xml_feed,
            headers={"Content-Type": "application/xml"}
        )

        return response.json()

    # =========================================================================
    # HOTEL CENTER INTEGRATION
    # =========================================================================

    async def get_property(self, property_id: str) -> Dict[str, Any]:
        """Get property details from Hotel Center."""
        client = await self.get_client()

        response = await client.get(
            f"{self.hotel_center_url}/properties/{property_id}"
        )
        response.raise_for_status()

        return response.json()

    async def list_properties(self) -> List[Dict[str, Any]]:
        """List all properties in the account."""
        client = await self.get_client()

        response = await client.get(
            f"{self.hotel_center_url}/accounts/{self._get_account_id()}/properties"
        )
        response.raise_for_status()

        return response.json().get("properties", [])

    # =========================================================================
    # PERFORMANCE REPORTING
    # =========================================================================

    async def get_performance_report(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[str, Any]:
        """
        Get performance report for a property.

        Returns metrics like impressions, clicks, and bookings.
        """
        response = await self._make_request(
            method="POST",
            endpoint=f"/accounts/{self._get_account_id()}/propertyPerformanceReportViews:query",
            json={
                "propertyId": property_id,
                "dateRange": {
                    "startDate": {
                        "year": start_date.year,
                        "month": start_date.month,
                        "day": start_date.day
                    },
                    "endDate": {
                        "year": end_date.year,
                        "month": end_date.month,
                        "day": end_date.day
                    }
                }
            }
        )

        return response.json()

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _get_account_id(self) -> str:
        """Get the Google account ID from configuration."""
        # In production, this would come from the channel connection
        import os
        return os.getenv("GOOGLE_HOTEL_CENTER_ACCOUNT_ID", "")

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        content: Optional[str] = None,
        headers: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """Make request with Google-specific handling."""
        client = await self.get_client()

        request_headers = dict(self.headers)
        if headers:
            request_headers.update(headers)

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=json,
                params=params,
                content=content,
                headers=request_headers,
                **kwargs
            )

            if response.status_code >= 400:
                self._handle_error(response)

            return response

        except httpx.RequestError as e:
            logger.error(
                "Google API request failed",
                endpoint=endpoint,
                error=str(e)
            )
            raise ChannelAdapterError(f"Request failed: {e}")

    def _handle_error(self, response: httpx.Response) -> None:
        """Handle Google API errors."""
        try:
            error_data = response.json()
            error_message = error_data.get("error", {}).get("message", response.text)
        except json.JSONDecodeError:
            error_message = response.text

        if response.status_code == 401:
            raise ChannelAdapterError(
                "Google authentication failed",
                status_code=401,
                response_body=error_message
            )
        elif response.status_code == 403:
            raise ChannelAdapterError(
                "Google access forbidden",
                status_code=403,
                response_body=error_message
            )
        elif response.status_code == 429:
            raise ChannelAdapterError(
                "Google rate limit exceeded",
                status_code=429,
                response_body=error_message
            )
        else:
            raise ChannelAdapterError(
                f"Google API error: {response.status_code}",
                status_code=response.status_code,
                response_body=error_message
            )
