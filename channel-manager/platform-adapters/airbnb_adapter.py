"""
Airbnb Channel Adapter
======================

Platform adapter for Airbnb API integration.

API Documentation: https://www.airbnb.com/partner
Rate Limit: 10 requests/second per host
Auth: OAuth 2.0 Authorization Code Flow
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


class AirbnbAdapter(ChannelAdapter):
    """
    Adapter for Airbnb API.

    Endpoints:
    - GET /listings - Get listings
    - PUT /calendar - Update availability & pricing
    - GET /reservations - Get reservations
    - POST /webhooks - Configure webhooks

    Webhooks:
    - reservation.created
    - reservation.cancelled
    - reservation.updated
    """

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.AIRBNB

    @property
    def base_url(self) -> str:
        return "https://api.airbnb.com/v2"

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
        Update availability on Airbnb calendar.

        Uses the PUT /calendar endpoint to update availability for a date range.
        """
        self._log_request(
            "PUT",
            f"/listings/{property_id}/calendar",
            start_date=str(start_date),
            end_date=str(end_date),
            available=available
        )

        payload = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "available": available,
        }

        if min_stay is not None:
            payload["min_nights"] = min_stay
        if max_stay is not None:
            payload["max_nights"] = max_stay

        response = await self._make_request(
            method="PUT",
            endpoint=f"/listings/{property_id}/calendar",
            json=payload
        )

        self._log_response(response, records_updated=1)

    async def get_availability(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, bool]:
        """
        Get availability from Airbnb calendar.

        Returns a dictionary mapping each date to its availability status.
        """
        response = await self._make_request(
            method="GET",
            endpoint=f"/listings/{property_id}/calendar",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        data = response.json()
        calendar = data.get("calendar", {}).get("days", [])

        availability = {}
        for day in calendar:
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
        """
        Update pricing for a single date on Airbnb.
        """
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
        Update pricing for multiple dates in a single request.

        Airbnb's calendar endpoint accepts price updates alongside availability.
        """
        self._log_request(
            "PUT",
            f"/listings/{property_id}/calendar",
            date_count=len(date_prices)
        )

        # Group consecutive dates for efficiency
        sorted_dates = sorted(date_prices.keys())

        # For simplicity, update each date individually (Airbnb supports bulk)
        calendar_days = []
        for d, price in date_prices.items():
            calendar_days.append({
                "date": d.isoformat(),
                "price": float(price),
                "currency": currency
            })

        payload = {
            "calendar": {
                "days": calendar_days
            }
        }

        response = await self._make_request(
            method="PUT",
            endpoint=f"/listings/{property_id}/calendar",
            json=payload
        )

        self._log_response(response, records_updated=len(date_prices))

    async def get_pricing(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, Decimal]:
        """
        Get pricing from Airbnb calendar.
        """
        response = await self._make_request(
            method="GET",
            endpoint=f"/listings/{property_id}/calendar",
            params={
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            }
        )

        data = response.json()
        calendar = data.get("calendar", {}).get("days", [])

        pricing = {}
        for day in calendar:
            day_date = date.fromisoformat(day["date"])
            price = day.get("price", {})
            if isinstance(price, dict):
                pricing[day_date] = Decimal(str(price.get("amount", 0)))
            else:
                pricing[day_date] = Decimal(str(price))

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
        Get reservations from Airbnb.

        Args:
            property_id: Airbnb listing ID
            since: Only return reservations updated after this time
            status: Filter by status (pending, accepted, denied, cancelled)
        """
        params = {
            "listing_id": property_id,
            "_limit": 50,
            "_offset": 0
        }

        if since:
            params["_updated_at_min"] = since.isoformat()
        if status:
            params["status"] = status

        all_bookings = []
        offset = 0

        while True:
            params["_offset"] = offset

            response = await self._make_request(
                method="GET",
                endpoint="/reservations",
                params=params
            )

            data = response.json()
            reservations = data.get("reservations", [])

            if not reservations:
                break

            for res in reservations:
                booking = self._map_reservation_to_booking(res)
                all_bookings.append(booking)

            if len(reservations) < 50:
                break

            offset += 50

        logger.info(
            "Retrieved Airbnb bookings",
            property_id=property_id,
            count=len(all_bookings)
        )

        return all_bookings

    async def get_booking(
        self,
        property_id: str,
        booking_id: str
    ) -> PlatformBooking:
        """
        Get a single reservation by ID.
        """
        response = await self._make_request(
            method="GET",
            endpoint=f"/reservations/{booking_id}"
        )

        data = response.json()
        reservation = data.get("reservation", data)

        return self._map_reservation_to_booking(reservation)

    def _map_reservation_to_booking(self, reservation: Dict[str, Any]) -> PlatformBooking:
        """
        Map Airbnb reservation data to PlatformBooking.
        """
        guest = reservation.get("guest", {})
        pricing = reservation.get("pricing_quote", {})

        return PlatformBooking(
            channel_booking_id=str(reservation["confirmation_code"]),
            listing_id=str(reservation.get("listing_id", "")),
            status=reservation.get("status", "pending"),
            check_in=date.fromisoformat(reservation["start_date"]),
            check_out=date.fromisoformat(reservation["end_date"]),
            guest_first_name=guest.get("first_name", ""),
            guest_last_name=guest.get("last_name", ""),
            guest_email=guest.get("email", ""),
            guest_phone=guest.get("phone", None),
            num_guests=reservation.get("number_of_guests", 1),
            num_adults=reservation.get("number_of_adults", 1),
            num_children=reservation.get("number_of_children", 0),
            num_infants=reservation.get("number_of_infants", 0),
            total_price=Decimal(str(pricing.get("total", {}).get("amount", 0))),
            currency=pricing.get("total", {}).get("currency", "EUR"),
            booked_at=datetime.fromisoformat(reservation["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(reservation["updated_at"].replace("Z", "+00:00")),
            special_requests=reservation.get("guest_message", None),
            channel_guest_id=str(guest.get("id", "")),
            channel_data=reservation
        )

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
        Verify Airbnb webhook signature.

        Airbnb uses HMAC-SHA256 for webhook signatures.
        The signature is sent in the X-Airbnb-Signature header.
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
        """
        Parse Airbnb webhook payload into standardized event format.
        """
        event_type = payload.get("event_type", "")
        event_id = payload.get("event_id", "")
        timestamp_str = payload.get("timestamp", datetime.utcnow().isoformat())

        # Parse timestamp
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

    def _map_event_type(self, airbnb_event_type: str) -> str:
        """Map Airbnb event types to standardized event types."""
        event_map = {
            "reservation.created": "booking.created",
            "reservation.accepted": "booking.confirmed",
            "reservation.declined": "booking.declined",
            "reservation.cancelled": "booking.cancelled",
            "reservation.cancelled_by_host": "booking.cancelled",
            "reservation.cancelled_by_guest": "booking.cancelled",
            "reservation.updated": "booking.updated",
            "reservation.checkout_completed": "booking.checked_out"
        }
        return event_map.get(airbnb_event_type, airbnb_event_type)

    # =========================================================================
    # LISTING MANAGEMENT
    # =========================================================================

    async def get_listings(self) -> List[Dict[str, Any]]:
        """
        Get all listings for the authenticated user.
        """
        response = await self._make_request(
            method="GET",
            endpoint="/listings",
            params={"_limit": 50}
        )

        data = response.json()
        return data.get("listings", [])

    async def get_listing(self, listing_id: str) -> Dict[str, Any]:
        """
        Get details for a specific listing.
        """
        response = await self._make_request(
            method="GET",
            endpoint=f"/listings/{listing_id}"
        )

        data = response.json()
        return data.get("listing", data)

    # =========================================================================
    # WEBHOOK REGISTRATION
    # =========================================================================

    async def register_webhook(
        self,
        listing_id: str,
        webhook_url: str,
        events: List[str]
    ) -> Dict[str, Any]:
        """
        Register a webhook endpoint for receiving reservation events.

        Args:
            listing_id: Airbnb listing ID
            webhook_url: URL to receive webhook events
            events: List of event types to subscribe to

        Returns:
            Webhook registration response
        """
        payload = {
            "url": webhook_url,
            "listing_id": listing_id,
            "events": events
        }

        response = await self._make_request(
            method="POST",
            endpoint="/webhooks",
            json=payload
        )

        return response.json()

    async def delete_webhook(self, webhook_id: str) -> None:
        """Delete a registered webhook."""
        await self._make_request(
            method="DELETE",
            endpoint=f"/webhooks/{webhook_id}"
        )
