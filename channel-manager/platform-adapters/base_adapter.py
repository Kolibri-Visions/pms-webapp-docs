"""
Base Channel Adapter
====================

Abstract base class defining the interface for all channel platform adapters.
Each platform adapter must implement this interface to ensure consistent
behavior across all integrated booking platforms.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx
import structlog

logger = structlog.get_logger(__name__)


class ChannelType(str, Enum):
    """Supported channel types."""
    AIRBNB = "airbnb"
    BOOKING_COM = "booking_com"
    EXPEDIA = "expedia"
    FEWO_DIREKT = "fewo_direkt"
    GOOGLE = "google"


@dataclass
class PlatformBooking:
    """Standardized booking data structure from any platform."""
    channel_booking_id: str
    listing_id: str
    status: str
    check_in: date
    check_out: date
    guest_first_name: str
    guest_last_name: str
    guest_email: str
    guest_phone: Optional[str]
    num_guests: int
    num_adults: int
    num_children: int
    num_infants: int
    total_price: Decimal
    currency: str
    booked_at: datetime
    updated_at: datetime
    special_requests: Optional[str]
    channel_guest_id: Optional[str] = None
    channel_data: Dict[str, Any] = None

    def __post_init__(self):
        if self.channel_data is None:
            self.channel_data = {}


@dataclass
class AvailabilityUpdate:
    """Availability update request."""
    start_date: date
    end_date: date
    available: bool
    min_stay: Optional[int] = None
    max_stay: Optional[int] = None


@dataclass
class PricingUpdate:
    """Pricing update request."""
    date: date
    price: Decimal
    currency: str = "EUR"


@dataclass
class WebhookEvent:
    """Standardized webhook event from any platform."""
    event_type: str
    event_id: str
    timestamp: datetime
    payload: Dict[str, Any]


class ChannelAdapterError(Exception):
    """Base exception for channel adapter errors."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_body: Optional[str] = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class AuthenticationError(ChannelAdapterError):
    """Raised when authentication fails (401, 403)."""
    pass


class RateLimitError(ChannelAdapterError):
    """Raised when rate limit is exceeded (429)."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        super().__init__(message, 429)
        self.retry_after = retry_after


class ResourceNotFoundError(ChannelAdapterError):
    """Raised when resource is not found (404)."""
    pass


class ValidationError(ChannelAdapterError):
    """Raised when request validation fails (400)."""
    pass


class ChannelAdapter(ABC):
    """
    Abstract base class for all channel platform adapters.

    Each adapter must implement methods for:
    - Availability management (update, get)
    - Pricing management (update, get)
    - Booking retrieval
    - Webhook signature verification

    Adapters should handle:
    - Platform-specific API formats
    - Error handling and translation
    - Data mapping between platform and PMS schemas
    """

    def __init__(self, access_token: str, timeout: int = 30):
        """
        Initialize the adapter.

        Args:
            access_token: OAuth access token for API authentication
            timeout: HTTP request timeout in seconds
        """
        self.access_token = access_token
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    @abstractmethod
    def channel_type(self) -> ChannelType:
        """Return the channel type for this adapter."""
        pass

    @property
    @abstractmethod
    def base_url(self) -> str:
        """Return the base API URL for this platform."""
        pass

    @property
    def headers(self) -> Dict[str, str]:
        """Return default headers for API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=self.headers,
                timeout=self.timeout
            )
        return self._client

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    # =========================================================================
    # ABSTRACT METHODS - Must be implemented by each adapter
    # =========================================================================

    @abstractmethod
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
        Update availability on the platform.

        Args:
            property_id: Platform-specific property/listing ID
            start_date: Start date of the period
            end_date: End date of the period (exclusive)
            available: Whether dates are available for booking
            min_stay: Optional minimum stay requirement
            max_stay: Optional maximum stay limit

        Raises:
            ChannelAdapterError: On API errors
            AuthenticationError: On auth failures
            RateLimitError: On rate limit exceeded
        """
        pass

    @abstractmethod
    async def get_availability(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, bool]:
        """
        Get availability from the platform.

        Args:
            property_id: Platform-specific property/listing ID
            start_date: Start date of the period
            end_date: End date of the period

        Returns:
            Dictionary mapping dates to availability (True = available)
        """
        pass

    @abstractmethod
    async def update_pricing(
        self,
        property_id: str,
        date: date,
        price: Decimal,
        currency: str = "EUR"
    ) -> None:
        """
        Update pricing for a specific date.

        Args:
            property_id: Platform-specific property/listing ID
            date: The date to update pricing for
            price: The nightly price
            currency: Currency code (default: EUR)
        """
        pass

    @abstractmethod
    async def update_pricing_bulk(
        self,
        property_id: str,
        date_prices: Dict[date, Decimal],
        currency: str = "EUR"
    ) -> None:
        """
        Update pricing for multiple dates in a single request.

        Args:
            property_id: Platform-specific property/listing ID
            date_prices: Dictionary mapping dates to prices
            currency: Currency code (default: EUR)
        """
        pass

    @abstractmethod
    async def get_pricing(
        self,
        property_id: str,
        start_date: date,
        end_date: date
    ) -> Dict[date, Decimal]:
        """
        Get pricing from the platform.

        Args:
            property_id: Platform-specific property/listing ID
            start_date: Start date of the period
            end_date: End date of the period

        Returns:
            Dictionary mapping dates to prices
        """
        pass

    @abstractmethod
    async def get_bookings(
        self,
        property_id: str,
        since: Optional[datetime] = None,
        status: Optional[str] = None
    ) -> List[PlatformBooking]:
        """
        Get bookings from the platform.

        Args:
            property_id: Platform-specific property/listing ID
            since: Only return bookings updated after this time
            status: Optional status filter

        Returns:
            List of bookings in standardized format
        """
        pass

    @abstractmethod
    async def get_booking(
        self,
        property_id: str,
        booking_id: str
    ) -> PlatformBooking:
        """
        Get a single booking by ID.

        Args:
            property_id: Platform-specific property/listing ID
            booking_id: Platform-specific booking ID

        Returns:
            Booking in standardized format
        """
        pass

    @abstractmethod
    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify webhook signature.

        Args:
            payload: Raw webhook payload bytes
            signature: Signature from request header
            secret: Webhook secret for verification

        Returns:
            True if signature is valid
        """
        pass

    @abstractmethod
    def parse_webhook_event(
        self,
        payload: Dict[str, Any]
    ) -> WebhookEvent:
        """
        Parse a webhook payload into standardized event format.

        Args:
            payload: Raw webhook payload dictionary

        Returns:
            Standardized webhook event
        """
        pass

    # =========================================================================
    # HELPER METHODS - Shared across adapters
    # =========================================================================

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Make an HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (relative to base_url)
            json: JSON body
            params: Query parameters

        Returns:
            httpx.Response

        Raises:
            ChannelAdapterError: On API errors
        """
        client = await self.get_client()

        try:
            response = await client.request(
                method=method,
                url=endpoint,
                json=json,
                params=params,
                **kwargs
            )

            # Handle common error codes
            if response.status_code == 401:
                raise AuthenticationError(
                    "Authentication failed - token may be expired",
                    status_code=401,
                    response_body=response.text
                )
            elif response.status_code == 403:
                raise AuthenticationError(
                    "Access forbidden - insufficient permissions",
                    status_code=403,
                    response_body=response.text
                )
            elif response.status_code == 404:
                raise ResourceNotFoundError(
                    f"Resource not found: {endpoint}",
                    status_code=404,
                    response_body=response.text
                )
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(
                    "Rate limit exceeded",
                    retry_after=int(retry_after) if retry_after else None
                )
            elif response.status_code == 400:
                raise ValidationError(
                    f"Validation error: {response.text}",
                    status_code=400,
                    response_body=response.text
                )
            elif response.status_code >= 500:
                raise ChannelAdapterError(
                    f"Server error: {response.status_code}",
                    status_code=response.status_code,
                    response_body=response.text
                )

            response.raise_for_status()
            return response

        except httpx.RequestError as e:
            logger.error(
                "HTTP request failed",
                channel=self.channel_type.value,
                endpoint=endpoint,
                error=str(e)
            )
            raise ChannelAdapterError(f"Request failed: {e}")

    def _log_request(self, method: str, endpoint: str, **kwargs):
        """Log outgoing API request."""
        logger.info(
            "API request",
            channel=self.channel_type.value,
            method=method,
            endpoint=endpoint,
            **kwargs
        )

    def _log_response(self, response: httpx.Response, **kwargs):
        """Log API response."""
        logger.info(
            "API response",
            channel=self.channel_type.value,
            status_code=response.status_code,
            **kwargs
        )
