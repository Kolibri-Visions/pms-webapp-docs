"""
FeWo-direkt (Vrbo) Channel Adapter
==================================

Platform adapter for FeWo-direkt / Vrbo API integration.

FeWo-direkt is the German brand of Vrbo (Vacation Rentals by Owner),
which is part of the Expedia Group.

API Documentation: https://developer.vrbo.com/
Rate Limit: 30 requests/second
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


class FeWoDirektAdapter(ChannelAdapter):
    """
    Adapter for FeWo-direkt / Vrbo API.

    The Vrbo API provides access to:
    - Calendar/availability management
    - Pricing management
    - Reservation management
    - Instant booking
    - Listing content management

    Key Endpoints:
    - GET /listings/{listingId} - Get listing details
    - PUT /listings/{listingId}/calendar - Update calendar
    - GET /reservations - Get reservations
    """

    @property
    def channel_type(self) -> ChannelType:
        return ChannelType.FEWO_DIREKT

    @property
    def base_url(self) -> str:
        return "https://api.vrbo.com/v2"

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
        Update availability on Vrbo calendar.

        Uses the calendar endpoint to set availability for a date range.
        """
        self._log_request(
            "PUT",
            f"/listings/{property_id}/calendar",
            start_date=str(start_date),
            end_date=str(end_date),
            available=available
        )

        # Build calendar entries
        calendar_entries = []
        current = start_date
        while current < end_date:
            entry = {
                "date": current.isoformat(),
                "availability": "AVAILABLE" if available else "UNAVAILABLE"
            }
            if min_stay is not None:
                entry["minimumStay"] = min_stay
            if max_stay is not None:
                entry["maximumStay"] = max_stay
            calendar_entries.append(entry)
            current += timedelta(days=1)

        payload = {
            "calendarEntries": calendar_entries
        }

        response = await self._make_request(
            method="PUT",
            endpoint=f"/listings/{property_id}/calendar",
            json=payload
        )

        self._log_response(response, records_updated=len(calendar_entries))

    async def get_availability(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, bool]:
        """Get availability from Vrbo calendar."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/listings/{property_id}/calendar",
            params={
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat()
            }
        )

        data = response.json()
        availability = {}

        for entry in data.get("calendarEntries", []):
            entry_date = date.fromisoformat(entry["date"])
            availability[entry_date] = entry.get("availability") == "AVAILABLE"

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
        Update pricing for multiple dates on Vrbo.
        """
        self._log_request(
            "PUT",
            f"/listings/{property_id}/rates",
            date_count=len(date_prices)
        )

        rate_entries = []
        for rate_date, price in sorted(date_prices.items()):
            rate_entries.append({
                "date": rate_date.isoformat(),
                "nightlyRate": {
                    "amount": float(price),
                    "currency": currency
                }
            })

        payload = {
            "rateEntries": rate_entries
        }

        response = await self._make_request(
            method="PUT",
            endpoint=f"/listings/{property_id}/rates",
            json=payload
        )

        self._log_response(response, records_updated=len(date_prices))

    async def get_pricing(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, Decimal]:
        """Get pricing from Vrbo."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/listings/{property_id}/rates",
            params={
                "startDate": start_date.isoformat(),
                "endDate": end_date.isoformat()
            }
        )

        data = response.json()
        pricing = {}

        for entry in data.get("rateEntries", []):
            entry_date = date.fromisoformat(entry["date"])
            rate = entry.get("nightlyRate", {})
            pricing[entry_date] = Decimal(str(rate.get("amount", 0)))

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
        Get reservations from Vrbo.

        Supports pagination and filtering.
        """
        params = {
            "listingId": property_id,
            "pageSize": 50,
            "cursor": None
        }

        if since:
            params["modifiedAfter"] = since.isoformat() + "Z"
        if status:
            params["status"] = status

        all_bookings = []

        while True:
            response = await self._make_request(
                method="GET",
                endpoint="/reservations",
                params={k: v for k, v in params.items() if v is not None}
            )

            data = response.json()
            reservations = data.get("reservations", [])

            for res in reservations:
                booking = self._map_reservation_to_booking(res)
                all_bookings.append(booking)

            # Check for next page
            next_cursor = data.get("pagination", {}).get("nextCursor")
            if not next_cursor or len(reservations) < 50:
                break

            params["cursor"] = next_cursor

        logger.info(
            "Retrieved Vrbo reservations",
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
        response = await self._make_request(
            method="GET",
            endpoint=f"/reservations/{booking_id}"
        )

        data = response.json()
        return self._map_reservation_to_booking(data)

    def _map_reservation_to_booking(self, reservation: Dict[str, Any]) -> PlatformBooking:
        """Map Vrbo reservation to PlatformBooking."""
        guest = reservation.get("guest", {})
        stay = reservation.get("stayDetails", {})
        pricing = reservation.get("pricing", {})

        # Parse dates
        check_in = date.fromisoformat(stay.get("checkIn", ""))
        check_out = date.fromisoformat(stay.get("checkOut", ""))

        # Parse timestamps
        created_at = datetime.fromisoformat(
            reservation.get("createdAt", datetime.utcnow().isoformat()).replace("Z", "+00:00")
        )
        modified_at = datetime.fromisoformat(
            reservation.get("modifiedAt", created_at.isoformat()).replace("Z", "+00:00")
        )

        # Guest counts
        guest_counts = stay.get("guests", {})

        return PlatformBooking(
            channel_booking_id=str(reservation.get("reservationId", "")),
            listing_id=str(reservation.get("listingId", "")),
            status=self._map_status(reservation.get("status", "tentative")),
            check_in=check_in,
            check_out=check_out,
            guest_first_name=guest.get("firstName", ""),
            guest_last_name=guest.get("lastName", ""),
            guest_email=guest.get("email", ""),
            guest_phone=guest.get("phone", None),
            num_guests=guest_counts.get("adults", 1) + guest_counts.get("children", 0),
            num_adults=guest_counts.get("adults", 1),
            num_children=guest_counts.get("children", 0),
            num_infants=guest_counts.get("infants", 0),
            total_price=Decimal(str(pricing.get("total", {}).get("amount", 0))),
            currency=pricing.get("total", {}).get("currency", "EUR"),
            booked_at=created_at,
            updated_at=modified_at,
            special_requests=reservation.get("guestMessage", None),
            channel_guest_id=str(guest.get("guestId", "")),
            channel_data=reservation
        )

    def _map_status(self, vrbo_status: str) -> str:
        """Map Vrbo status to standardized status."""
        status_map = {
            "tentative": "pending",
            "booked": "confirmed",
            "confirmed": "confirmed",
            "cancelled": "cancelled",
            "cancelled_by_guest": "cancelled",
            "cancelled_by_owner": "cancelled",
            "declined": "declined",
            "expired": "cancelled"
        }
        return status_map.get(vrbo_status.lower(), "pending")

    # =========================================================================
    # INSTANT BOOKING
    # =========================================================================

    async def accept_instant_booking(
        self,
        reservation_id: str
    ) -> Dict[str, Any]:
        """
        Accept an instant booking.

        Vrbo supports instant booking which automatically confirms bookings.
        """
        response = await self._make_request(
            method="POST",
            endpoint=f"/reservations/{reservation_id}/accept"
        )

        return response.json()

    async def decline_booking(
        self,
        reservation_id: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Decline a booking request.
        """
        response = await self._make_request(
            method="POST",
            endpoint=f"/reservations/{reservation_id}/decline",
            json={"reason": reason}
        )

        return response.json()

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
        Verify Vrbo webhook signature.

        Vrbo uses HMAC-SHA256 for webhook signatures.
        The signature is in the X-Vrbo-Signature header.
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
        """Parse Vrbo webhook payload."""
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

    def _map_event_type(self, vrbo_event_type: str) -> str:
        """Map Vrbo event types to standardized types."""
        event_map = {
            "RESERVATION_CREATED": "booking.created",
            "RESERVATION_MODIFIED": "booking.updated",
            "RESERVATION_CANCELLED": "booking.cancelled",
            "INSTANT_BOOK_CREATED": "booking.created",
            "INQUIRY_CREATED": "inquiry.created",
            "MESSAGE_RECEIVED": "message.received"
        }
        return event_map.get(vrbo_event_type, vrbo_event_type)

    # =========================================================================
    # LISTING MANAGEMENT
    # =========================================================================

    async def get_listing(self, listing_id: str) -> Dict[str, Any]:
        """Get listing details."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/listings/{listing_id}"
        )
        return response.json()

    async def get_listings(self) -> List[Dict[str, Any]]:
        """Get all listings for the authenticated user."""
        response = await self._make_request(
            method="GET",
            endpoint="/listings"
        )
        return response.json().get("listings", [])

    async def update_listing(
        self,
        listing_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update listing details."""
        response = await self._make_request(
            method="PATCH",
            endpoint=f"/listings/{listing_id}",
            json=updates
        )
        return response.json()

    # =========================================================================
    # MESSAGING
    # =========================================================================

    async def send_message(
        self,
        reservation_id: str,
        message: str
    ) -> Dict[str, Any]:
        """Send a message to a guest."""
        response = await self._make_request(
            method="POST",
            endpoint=f"/reservations/{reservation_id}/messages",
            json={"content": message}
        )
        return response.json()

    async def get_messages(
        self,
        reservation_id: str
    ) -> List[Dict[str, Any]]:
        """Get messages for a reservation."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/reservations/{reservation_id}/messages"
        )
        return response.json().get("messages", [])

    # =========================================================================
    # REVIEWS
    # =========================================================================

    async def get_reviews(
        self,
        listing_id: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get reviews for a listing."""
        response = await self._make_request(
            method="GET",
            endpoint=f"/listings/{listing_id}/reviews",
            params={"limit": limit}
        )
        return response.json().get("reviews", [])

    async def respond_to_review(
        self,
        listing_id: str,
        review_id: str,
        response_text: str
    ) -> Dict[str, Any]:
        """Respond to a guest review."""
        response = await self._make_request(
            method="POST",
            endpoint=f"/listings/{listing_id}/reviews/{review_id}/response",
            json={"response": response_text}
        )
        return response.json()
