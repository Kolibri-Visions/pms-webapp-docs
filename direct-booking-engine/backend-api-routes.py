"""
Direct Booking Engine - Backend API Routes

Technology Stack:
- FastAPI 0.110+
- SQLAlchemy 2.0+ (async)
- Pydantic v2
- Stripe SDK
- Redis (Upstash)
- Celery (background tasks)

Version: 1.0.0
Last Updated: 2025-12-21
"""

# =============================================================================
# IMPORTS & CONFIGURATION
# =============================================================================

from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Annotated, Any, Optional
from uuid import UUID, uuid4

import stripe
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from redis import asyncio as aioredis
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

# Local imports (would be from project modules)
# from app.core.config import settings
# from app.core.security import get_current_user_optional
# from app.db.session import get_db
# from app.models import (
#     Booking, BookingStatus, CalendarAvailability, Guest, Property, PaymentTransaction
# )
# from app.services.email import send_email
# from app.services.events import publish_event
# from app.tasks.booking import cancel_expired_booking

# =============================================================================
# CONFIGURATION
# =============================================================================

# Stripe configuration
stripe.api_key = "sk_test_..."  # settings.STRIPE_SECRET_KEY
STRIPE_WEBHOOK_SECRET = "whsec_..."  # settings.STRIPE_WEBHOOK_SECRET

# Booking configuration
BOOKING_RESERVATION_TIMEOUT_MINUTES = 30
MAX_PAYMENT_RETRIES = 3
SERVICE_FEE_PERCENTAGE = Decimal("0.05")  # 5% service fee

# Redis client (would be injected)
# redis = aioredis.from_url(settings.REDIS_URL)


# =============================================================================
# ENUMS & MODELS
# =============================================================================

class BookingSource(str, Enum):
    DIRECT = "direct"
    AIRBNB = "airbnb"
    BOOKING_COM = "booking_com"
    EXPEDIA = "expedia"
    FEWO_DIREKT = "fewo_direkt"
    GOOGLE = "google"


class BookingStatus(str, Enum):
    INQUIRY = "inquiry"
    RESERVED = "reserved"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"


class PaymentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"
    EXPIRED = "expired"


# =============================================================================
# REQUEST/RESPONSE SCHEMAS
# =============================================================================

# ----- Property Search -----

class LocationFilter(BaseModel):
    lat: float
    lng: float
    radius_km: float = Field(default=25, ge=1, le=100)


class PropertyFilters(BaseModel):
    price_min: Optional[Decimal] = None
    price_max: Optional[Decimal] = None
    bedrooms_min: Optional[int] = None
    amenities: Optional[list[str]] = None
    property_types: Optional[list[str]] = None
    instant_book: Optional[bool] = None


class PropertySearchRequest(BaseModel):
    location: Optional[LocationFilter] = None
    check_in: Optional[date] = None
    check_out: Optional[date] = None
    guests: Optional[int] = Field(default=2, ge=1, le=16)
    filters: Optional[PropertyFilters] = None
    sort_by: Optional[str] = Field(default="rating_desc")
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=24, ge=1, le=100)

    @field_validator("check_out")
    @classmethod
    def check_out_after_check_in(cls, v: Optional[date], info) -> Optional[date]:
        check_in = info.data.get("check_in")
        if v and check_in and v <= check_in:
            raise ValueError("Check-out must be after check-in")
        return v


class PropertyImage(BaseModel):
    url: str
    thumbnail_url: Optional[str] = None
    caption: Optional[str] = None
    is_primary: bool = False


class PropertyAddress(BaseModel):
    city: str
    district: Optional[str] = None
    country: str
    full_address: Optional[str] = None  # Only shown after booking


class PropertyOwner(BaseModel):
    id: UUID
    first_name: str
    response_rate: Optional[int] = None
    response_time: Optional[str] = None


class PropertyResponse(BaseModel):
    id: UUID
    name: str
    description: str
    description_short: Optional[str] = None
    bedrooms: int
    bathrooms: Decimal
    max_guests: int
    size_sqm: Optional[int] = None
    property_type: str
    amenities: list[str]
    house_rules: list[str]
    check_in_time: str
    check_out_time: str
    images: list[PropertyImage]
    address: PropertyAddress
    rating: Decimal
    review_count: int
    instant_book: bool
    base_price: Decimal
    currency: str
    owner: PropertyOwner

    class Config:
        from_attributes = True


class PropertyListItem(BaseModel):
    id: UUID
    name: str
    description_short: Optional[str] = None
    thumbnail_url: Optional[str] = None
    bedrooms: int
    max_guests: int
    rating: Decimal
    review_count: int
    property_type: str
    amenities: list[str]
    instant_book: bool
    nightly_price: Decimal
    total_price: Optional[Decimal] = None
    currency: str
    address: PropertyAddress


class PaginationInfo(BaseModel):
    total: int
    page: int
    pages: int
    limit: int


class SearchMetadata(BaseModel):
    location_name: Optional[str] = None
    dates: Optional[dict] = None
    guests: int


class PropertySearchResponse(BaseModel):
    properties: list[PropertyListItem]
    pagination: PaginationInfo
    search_metadata: SearchMetadata


# ----- Availability Check -----

class AvailabilityCheckRequest(BaseModel):
    property_id: UUID
    check_in: date
    check_out: date

    @field_validator("check_in")
    @classmethod
    def check_in_not_in_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Check-in date cannot be in the past")
        return v

    @field_validator("check_out")
    @classmethod
    def check_out_after_check_in(cls, v: date, info) -> date:
        check_in = info.data.get("check_in")
        if check_in and v <= check_in:
            raise ValueError("Check-out must be after check-in")
        return v


class NightlyRate(BaseModel):
    date: date
    price: Decimal


class PriceBreakdown(BaseModel):
    nightly_rates: list[NightlyRate]
    subtotal: Decimal
    cleaning_fee: Decimal
    service_fee: Decimal
    taxes: Decimal
    total: Decimal
    currency: str


class AvailabilityCheckResponse(BaseModel):
    available: bool
    price_breakdown: Optional[PriceBreakdown] = None
    minimum_stay: int
    maximum_stay: int
    instant_book: bool
    cancellation_policy: str
    currency: str
    message: Optional[str] = None


# ----- Calendar -----

class CalendarDay(BaseModel):
    date: date
    available: bool
    status: Optional[str] = None  # 'available', 'booked', 'blocked'
    price: Optional[Decimal] = None
    min_stay: Optional[int] = None


class CalendarResponse(BaseModel):
    calendar: list[CalendarDay]


# ----- Booking Creation -----

class GuestDetails(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=20)


class BookingCreateRequest(BaseModel):
    property_id: UUID
    check_in: date
    check_out: date
    num_guests: int = Field(ge=1, le=16)
    guest: GuestDetails
    special_requests: Optional[str] = Field(default=None, max_length=500)
    create_account: bool = False

    @field_validator("check_in")
    @classmethod
    def check_in_not_in_past(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("Check-in date cannot be in the past")
        return v

    @field_validator("check_out")
    @classmethod
    def check_out_after_check_in(cls, v: date, info) -> date:
        check_in = info.data.get("check_in")
        if check_in and v <= check_in:
            raise ValueError("Check-out must be after check-in")
        return v


class BookingReservedResponse(BaseModel):
    booking_id: UUID
    booking_reference: str
    status: BookingStatus
    payment_status: PaymentStatus
    total_price: Decimal
    currency: str
    expires_at: datetime
    stripe_client_secret: str


# ----- Booking Confirmation -----

class BookingConfirmRequest(BaseModel):
    payment_intent_id: str


class BookingConfirmedResponse(BaseModel):
    booking_id: UUID
    booking_reference: str
    status: BookingStatus
    payment_status: PaymentStatus
    confirmed_at: datetime


# ----- Booking Details -----

class BookingDetailsResponse(BaseModel):
    booking_id: UUID
    booking_reference: str
    status: BookingStatus
    payment_status: PaymentStatus
    property: PropertyResponse
    guest: GuestDetails
    check_in: date
    check_out: date
    num_guests: int
    num_nights: int
    special_requests: Optional[str] = None
    pricing: PriceBreakdown
    confirmed_at: Optional[datetime] = None
    cancellation_policy: dict


# ----- Booking Cancellation -----

class BookingCancelRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


class BookingCancelResponse(BaseModel):
    booking_id: UUID
    status: BookingStatus
    refund_status: Optional[str] = None
    refund_amount: Optional[Decimal] = None


# =============================================================================
# ROUTER
# =============================================================================

router = APIRouter(prefix="/api/v1", tags=["Direct Booking Engine"])


# =============================================================================
# PROPERTY ENDPOINTS
# =============================================================================

@router.post("/properties/search", response_model=PropertySearchResponse)
async def search_properties(
    request: PropertySearchRequest,
    db: AsyncSession = Depends(get_db),
) -> PropertySearchResponse:
    """
    Search for available properties with filters.

    Returns paginated list of properties matching the search criteria.
    If check-in/check-out dates are provided, only returns available properties
    and includes total price for the stay.
    """
    # Build base query
    query = select(Property).where(Property.status == "active")

    # Location filter (PostGIS)
    if request.location:
        # ST_DWithin for distance-based filtering
        query = query.where(
            func.ST_DWithin(
                Property.location,
                func.ST_MakePoint(request.location.lng, request.location.lat),
                request.location.radius_km * 1000  # Convert to meters
            )
        )

    # Guest capacity filter
    if request.guests:
        query = query.where(Property.max_guests >= request.guests)

    # Property filters
    if request.filters:
        if request.filters.price_min:
            query = query.where(Property.base_price >= request.filters.price_min)
        if request.filters.price_max:
            query = query.where(Property.base_price <= request.filters.price_max)
        if request.filters.bedrooms_min:
            query = query.where(Property.bedrooms >= request.filters.bedrooms_min)
        if request.filters.instant_book is not None:
            query = query.where(Property.instant_book_enabled == request.filters.instant_book)
        if request.filters.property_types:
            query = query.where(Property.property_type.in_(request.filters.property_types))
        if request.filters.amenities:
            # PostgreSQL array overlap
            query = query.where(Property.amenities.overlap(request.filters.amenities))

    # Availability filter (if dates provided)
    if request.check_in and request.check_out:
        # Subquery to find properties with ALL dates available
        date_range = [
            request.check_in + timedelta(days=i)
            for i in range((request.check_out - request.check_in).days)
        ]

        available_subquery = (
            select(CalendarAvailability.property_id)
            .where(
                and_(
                    CalendarAvailability.date.in_(date_range),
                    CalendarAvailability.available == True
                )
            )
            .group_by(CalendarAvailability.property_id)
            .having(func.count() == len(date_range))
        )

        query = query.where(Property.id.in_(available_subquery))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Sorting
    if request.sort_by == "price_asc":
        query = query.order_by(Property.base_price.asc())
    elif request.sort_by == "price_desc":
        query = query.order_by(Property.base_price.desc())
    elif request.sort_by == "rating_desc":
        query = query.order_by(Property.rating.desc().nullslast())
    # Add distance sorting if location provided
    elif request.sort_by == "distance" and request.location:
        query = query.order_by(
            func.ST_Distance(
                Property.location,
                func.ST_MakePoint(request.location.lng, request.location.lat)
            )
        )

    # Pagination
    offset = (request.page - 1) * request.limit
    query = query.offset(offset).limit(request.limit)

    # Execute
    result = await db.execute(query)
    properties = result.scalars().all()

    # Calculate total prices if dates provided
    property_items = []
    for prop in properties:
        item = PropertyListItem(
            id=prop.id,
            name=prop.name,
            description_short=prop.description[:150] + "..." if prop.description else None,
            thumbnail_url=prop.images[0]["url"] if prop.images else None,
            bedrooms=prop.bedrooms,
            max_guests=prop.max_guests,
            rating=prop.rating or Decimal("0"),
            review_count=prop.review_count or 0,
            property_type=prop.property_type,
            amenities=prop.amenities or [],
            instant_book=prop.instant_book_enabled,
            nightly_price=prop.base_price,
            currency=prop.currency,
            address=PropertyAddress(
                city=prop.address.get("city", ""),
                district=prop.address.get("district"),
                country=prop.address.get("country", ""),
            ),
        )

        # Calculate total price if dates provided
        if request.check_in and request.check_out:
            price_breakdown = await calculate_price_breakdown(
                db, prop.id, request.check_in, request.check_out
            )
            if price_breakdown:
                item.total_price = price_breakdown.total

        property_items.append(item)

    return PropertySearchResponse(
        properties=property_items,
        pagination=PaginationInfo(
            total=total,
            page=request.page,
            pages=(total + request.limit - 1) // request.limit,
            limit=request.limit,
        ),
        search_metadata=SearchMetadata(
            location_name=None,  # Would be resolved from geocoding
            dates={
                "check_in": request.check_in.isoformat() if request.check_in else None,
                "check_out": request.check_out.isoformat() if request.check_out else None,
                "nights": (request.check_out - request.check_in).days if request.check_in and request.check_out else None,
            } if request.check_in else None,
            guests=request.guests or 2,
        ),
    )


@router.get("/properties/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> PropertyResponse:
    """
    Get detailed information about a single property.
    """
    query = select(Property).where(
        and_(
            Property.id == property_id,
            Property.status == "active"
        )
    )
    result = await db.execute(query)
    property = result.scalar_one_or_none()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )

    # Get owner info
    owner_query = select(UserProfile).where(UserProfile.id == property.owner_id)
    owner_result = await db.execute(owner_query)
    owner = owner_result.scalar_one_or_none()

    return PropertyResponse(
        id=property.id,
        name=property.name,
        description=property.description,
        bedrooms=property.bedrooms,
        bathrooms=property.bathrooms,
        max_guests=property.max_guests,
        size_sqm=property.size_sqm,
        property_type=property.property_type,
        amenities=property.amenities or [],
        house_rules=property.house_rules or [],
        check_in_time=property.check_in_time.strftime("%H:%M") if property.check_in_time else "15:00",
        check_out_time=property.check_out_time.strftime("%H:%M") if property.check_out_time else "11:00",
        images=[PropertyImage(**img) for img in property.images] if property.images else [],
        address=PropertyAddress(
            city=property.address.get("city", ""),
            district=property.address.get("district"),
            country=property.address.get("country", ""),
            # full_address only shown after booking
        ),
        rating=property.rating or Decimal("0"),
        review_count=property.review_count or 0,
        instant_book=property.instant_book_enabled,
        base_price=property.base_price,
        currency=property.currency,
        owner=PropertyOwner(
            id=owner.id if owner else property.owner_id,
            first_name=owner.first_name if owner else "Host",
            response_rate=98,  # Would be calculated
            response_time="within an hour",  # Would be calculated
        ),
    )


@router.get("/properties/{property_id}/calendar", response_model=CalendarResponse)
async def get_property_calendar(
    property_id: UUID,
    start: str = Query(..., description="Start month (YYYY-MM)"),
    end: str = Query(..., description="End month (YYYY-MM)"),
    db: AsyncSession = Depends(get_db),
) -> CalendarResponse:
    """
    Get availability calendar for a property.

    Returns daily availability status and pricing for the requested date range.
    """
    # Parse month strings to date range
    start_date = datetime.strptime(start + "-01", "%Y-%m-%d").date()
    # Get last day of end month
    end_year, end_month = map(int, end.split("-"))
    if end_month == 12:
        end_date = date(end_year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(end_year, end_month + 1, 1) - timedelta(days=1)

    # Verify property exists
    prop_query = select(Property).where(Property.id == property_id)
    prop_result = await db.execute(prop_query)
    property = prop_result.scalar_one_or_none()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )

    # Get calendar data
    query = (
        select(CalendarAvailability)
        .where(
            and_(
                CalendarAvailability.property_id == property_id,
                CalendarAvailability.date >= start_date,
                CalendarAvailability.date <= end_date,
            )
        )
        .order_by(CalendarAvailability.date)
    )
    result = await db.execute(query)
    calendar_days = result.scalars().all()

    # Build response with all dates in range
    calendar_map = {day.date: day for day in calendar_days}
    response_days = []

    current_date = start_date
    while current_date <= end_date:
        calendar_day = calendar_map.get(current_date)

        if calendar_day:
            response_days.append(CalendarDay(
                date=current_date,
                available=calendar_day.available,
                status=calendar_day.availability_status,
                price=calendar_day.price,
                min_stay=calendar_day.min_stay,
            ))
        else:
            # Default to property base settings if no calendar entry
            response_days.append(CalendarDay(
                date=current_date,
                available=True,
                status="available",
                price=property.base_price,
                min_stay=property.min_stay or 1,
            ))

        current_date += timedelta(days=1)

    return CalendarResponse(calendar=response_days)


# =============================================================================
# AVAILABILITY CHECK ENDPOINT
# =============================================================================

@router.post("/bookings/check-availability", response_model=AvailabilityCheckResponse)
async def check_availability(
    request: AvailabilityCheckRequest,
    db: AsyncSession = Depends(get_db),
) -> AvailabilityCheckResponse:
    """
    Check availability and get pricing for a property and date range.

    This endpoint is called before creating a booking to validate
    that the dates are available and show the guest the total price.
    """
    # Get property
    prop_query = select(Property).where(Property.id == request.property_id)
    prop_result = await db.execute(prop_query)
    property = prop_result.scalar_one_or_none()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found"
        )

    # Calculate number of nights
    num_nights = (request.check_out - request.check_in).days

    # Check minimum stay
    min_stay = property.min_stay or 1
    if num_nights < min_stay:
        return AvailabilityCheckResponse(
            available=False,
            minimum_stay=min_stay,
            maximum_stay=property.max_stay or 365,
            instant_book=property.instant_book_enabled,
            cancellation_policy="moderate",
            currency=property.currency,
            message=f"Minimum stay is {min_stay} nights",
        )

    # Check each date in range
    date_range = [
        request.check_in + timedelta(days=i)
        for i in range(num_nights)
    ]

    calendar_query = (
        select(CalendarAvailability)
        .where(
            and_(
                CalendarAvailability.property_id == request.property_id,
                CalendarAvailability.date.in_(date_range),
            )
        )
    )
    calendar_result = await db.execute(calendar_query)
    calendar_days = {day.date: day for day in calendar_result.scalars().all()}

    # Check availability
    unavailable_dates = []
    for d in date_range:
        calendar_day = calendar_days.get(d)
        if calendar_day and not calendar_day.available:
            unavailable_dates.append(d)

    if unavailable_dates:
        return AvailabilityCheckResponse(
            available=False,
            minimum_stay=min_stay,
            maximum_stay=property.max_stay or 365,
            instant_book=property.instant_book_enabled,
            cancellation_policy="moderate",
            currency=property.currency,
            message=f"Some dates are not available: {', '.join(d.isoformat() for d in unavailable_dates[:3])}",
        )

    # Calculate pricing
    price_breakdown = await calculate_price_breakdown(
        db, request.property_id, request.check_in, request.check_out
    )

    return AvailabilityCheckResponse(
        available=True,
        price_breakdown=price_breakdown,
        minimum_stay=min_stay,
        maximum_stay=property.max_stay or 365,
        instant_book=property.instant_book_enabled,
        cancellation_policy="moderate",
        currency=property.currency,
    )


async def calculate_price_breakdown(
    db: AsyncSession,
    property_id: UUID,
    check_in: date,
    check_out: date,
) -> PriceBreakdown:
    """
    Calculate the complete price breakdown for a booking.

    Includes:
    - Nightly rates (from calendar or base price)
    - Cleaning fee
    - Service fee (percentage)
    - Taxes
    """
    # Get property
    prop_query = select(Property).where(Property.id == property_id)
    prop_result = await db.execute(prop_query)
    property = prop_result.scalar_one()

    # Get calendar prices
    num_nights = (check_out - check_in).days
    date_range = [check_in + timedelta(days=i) for i in range(num_nights)]

    calendar_query = (
        select(CalendarAvailability)
        .where(
            and_(
                CalendarAvailability.property_id == property_id,
                CalendarAvailability.date.in_(date_range),
            )
        )
    )
    calendar_result = await db.execute(calendar_query)
    calendar_days = {day.date: day for day in calendar_result.scalars().all()}

    # Build nightly rates
    nightly_rates = []
    subtotal = Decimal("0")

    for d in date_range:
        calendar_day = calendar_days.get(d)
        price = calendar_day.price if calendar_day and calendar_day.price else property.base_price
        nightly_rates.append(NightlyRate(date=d, price=price))
        subtotal += price

    # Calculate fees
    cleaning_fee = property.cleaning_fee or Decimal("0")
    service_fee = (subtotal + cleaning_fee) * SERVICE_FEE_PERCENTAGE

    # Calculate taxes (if applicable)
    taxes = Decimal("0")
    if property.tax_rate and not property.tax_included:
        taxes = (subtotal + cleaning_fee + service_fee) * (property.tax_rate / 100)

    total = subtotal + cleaning_fee + service_fee + taxes

    return PriceBreakdown(
        nightly_rates=nightly_rates,
        subtotal=subtotal,
        cleaning_fee=cleaning_fee,
        service_fee=service_fee.quantize(Decimal("0.01")),
        taxes=taxes.quantize(Decimal("0.01")),
        total=total.quantize(Decimal("0.01")),
        currency=property.currency,
    )


# =============================================================================
# BOOKING CREATION ENDPOINT
# =============================================================================

@router.post("/bookings", response_model=BookingReservedResponse)
async def create_booking(
    request: BookingCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> BookingReservedResponse:
    """
    Create a new booking in RESERVED state.

    Flow:
    1. Validate property and availability
    2. Acquire distributed lock for calendar
    3. Create or get guest record
    4. Create Stripe PaymentIntent
    5. Create booking with status='reserved', payment_status='pending'
    6. Schedule auto-cancellation after 30 minutes
    7. Return client secret for Stripe payment

    Edge Cases:
    - Property not available: Return 409 Conflict
    - Race condition (double booking): Database constraint prevents, return 409
    - Stripe error: Clean up booking, return 500
    """
    # 1. Get property
    prop_query = select(Property).where(
        and_(
            Property.id == request.property_id,
            Property.status == "active"
        )
    )
    prop_result = await db.execute(prop_query)
    property = prop_result.scalar_one_or_none()

    if not property:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found or not available"
        )

    # 2. Acquire distributed lock for property calendar
    lock_key = f"booking:lock:{request.property_id}:{request.check_in}:{request.check_out}"
    lock = redis.lock(lock_key, timeout=60)  # 60 second lock

    try:
        if not await lock.acquire(blocking_timeout=5):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Another booking is being processed for these dates. Please try again."
            )

        # 3. Verify availability (with lock held)
        availability = await check_availability_internal(
            db, request.property_id, request.check_in, request.check_out
        )

        if not availability["available"]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Property is not available for selected dates"
            )

        # 4. Calculate pricing
        price_breakdown = await calculate_price_breakdown(
            db, request.property_id, request.check_in, request.check_out
        )

        # 5. Create or get guest
        guest = await create_or_get_guest(
            db,
            tenant_id=property.tenant_id,
            guest_details=request.guest,
            create_account=request.create_account,
        )

        # 6. Generate booking reference
        booking_reference = await generate_booking_reference(db)

        # 7. Create Stripe PaymentIntent
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=int(price_breakdown.total * 100),  # Stripe uses cents
                currency=price_breakdown.currency.lower(),
                metadata={
                    "property_id": str(request.property_id),
                    "booking_reference": booking_reference,
                    "guest_email": request.guest.email,
                    "check_in": request.check_in.isoformat(),
                    "check_out": request.check_out.isoformat(),
                },
                automatic_payment_methods={"enabled": True},
            )
        except stripe.error.StripeError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Payment initialization failed: {str(e)}"
            )

        # 8. Create booking record
        expires_at = datetime.utcnow() + timedelta(minutes=BOOKING_RESERVATION_TIMEOUT_MINUTES)

        booking = Booking(
            id=uuid4(),
            tenant_id=property.tenant_id,
            property_id=request.property_id,
            guest_id=guest.id,
            booking_reference=booking_reference,
            check_in=request.check_in,
            check_out=request.check_out,
            num_adults=request.num_guests,
            num_children=0,
            num_infants=0,
            num_pets=0,
            source=BookingSource.DIRECT.value,
            status=BookingStatus.RESERVED.value,
            payment_status=PaymentStatus.PENDING.value,
            nightly_rate=price_breakdown.subtotal / len(price_breakdown.nightly_rates),
            subtotal=price_breakdown.subtotal,
            cleaning_fee=price_breakdown.cleaning_fee,
            service_fee=price_breakdown.service_fee,
            tax_amount=price_breakdown.taxes,
            total_price=price_breakdown.total,
            currency=price_breakdown.currency,
            stripe_payment_intent_id=payment_intent.id,
            special_requests=request.special_requests,
            expires_at=expires_at,  # Custom field for reservation timeout
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(booking)

        # 9. Block calendar dates (tentatively)
        for d in [request.check_in + timedelta(days=i) for i in range((request.check_out - request.check_in).days)]:
            # Upsert calendar entry
            stmt = pg_insert(CalendarAvailability).values(
                id=uuid4(),
                property_id=request.property_id,
                date=d,
                available=False,
                availability_status="tentative",
                booking_id=booking.id,
                price=price_breakdown.nightly_rates[
                    (d - request.check_in).days
                ].price if (d - request.check_in).days < len(price_breakdown.nightly_rates) else property.base_price,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ).on_conflict_do_update(
                index_elements=["property_id", "date"],
                set_={
                    "available": False,
                    "availability_status": "tentative",
                    "booking_id": booking.id,
                    "updated_at": datetime.utcnow(),
                },
            )
            await db.execute(stmt)

        await db.commit()

        # 10. Schedule auto-cancellation
        background_tasks.add_task(
            schedule_booking_expiration,
            booking.id,
            BOOKING_RESERVATION_TIMEOUT_MINUTES * 60,
        )

        return BookingReservedResponse(
            booking_id=booking.id,
            booking_reference=booking.booking_reference,
            status=BookingStatus.RESERVED,
            payment_status=PaymentStatus.PENDING,
            total_price=price_breakdown.total,
            currency=price_breakdown.currency,
            expires_at=expires_at,
            stripe_client_secret=payment_intent.client_secret,
        )

    except IntegrityError:
        # Database constraint prevented double-booking
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Property is no longer available for selected dates. Please choose different dates."
        )
    finally:
        await lock.release()


async def check_availability_internal(
    db: AsyncSession,
    property_id: UUID,
    check_in: date,
    check_out: date,
) -> dict:
    """Internal availability check without HTTP response formatting."""
    num_nights = (check_out - check_in).days
    date_range = [check_in + timedelta(days=i) for i in range(num_nights)]

    # Check for existing bookings (confirmed or reserved)
    booking_query = select(Booking).where(
        and_(
            Booking.property_id == property_id,
            Booking.status.in_([BookingStatus.RESERVED.value, BookingStatus.CONFIRMED.value]),
            Booking.check_in < check_out,
            Booking.check_out > check_in,
        )
    )
    booking_result = await db.execute(booking_query)
    conflicting_booking = booking_result.scalar_one_or_none()

    if conflicting_booking:
        return {"available": False, "reason": "dates_booked"}

    # Check calendar blocks
    calendar_query = select(CalendarAvailability).where(
        and_(
            CalendarAvailability.property_id == property_id,
            CalendarAvailability.date.in_(date_range),
            CalendarAvailability.available == False,
        )
    )
    calendar_result = await db.execute(calendar_query)
    blocked_days = calendar_result.scalars().all()

    if blocked_days:
        return {"available": False, "reason": "dates_blocked"}

    return {"available": True}


async def create_or_get_guest(
    db: AsyncSession,
    tenant_id: UUID,
    guest_details: GuestDetails,
    create_account: bool = False,
) -> Guest:
    """Create a new guest or return existing one based on email."""
    # Check for existing guest by email within tenant
    query = select(Guest).where(
        and_(
            Guest.tenant_id == tenant_id,
            Guest.email == guest_details.email,
        )
    )
    result = await db.execute(query)
    existing_guest = result.scalar_one_or_none()

    if existing_guest:
        # Update guest details if needed
        existing_guest.first_name = guest_details.first_name
        existing_guest.last_name = guest_details.last_name
        if guest_details.phone:
            existing_guest.phone = guest_details.phone
        existing_guest.updated_at = datetime.utcnow()
        existing_guest.total_bookings = (existing_guest.total_bookings or 0) + 1
        return existing_guest

    # Create new guest
    guest = Guest(
        id=uuid4(),
        tenant_id=tenant_id,
        first_name=guest_details.first_name,
        last_name=guest_details.last_name,
        email=guest_details.email,
        phone=guest_details.phone,
        auth_user_id=None,  # No account yet
        source="direct",
        total_bookings=1,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(guest)

    return guest


async def generate_booking_reference(db: AsyncSession) -> str:
    """Generate a unique booking reference like PMS-2025-000123."""
    year = datetime.utcnow().year

    # Get the last booking number for this year
    query = select(func.max(Booking.booking_reference)).where(
        Booking.booking_reference.like(f"PMS-{year}-%")
    )
    result = await db.execute(query)
    last_ref = result.scalar_one_or_none()

    if last_ref:
        last_num = int(last_ref.split("-")[-1])
        new_num = last_num + 1
    else:
        new_num = 1

    return f"PMS-{year}-{new_num:06d}"


async def schedule_booking_expiration(booking_id: UUID, delay_seconds: int):
    """Schedule a background task to cancel the booking if not paid."""
    # In production, this would use Celery or similar
    # cancel_expired_booking.apply_async(
    #     args=[str(booking_id)],
    #     countdown=delay_seconds
    # )
    pass


# =============================================================================
# BOOKING CONFIRMATION ENDPOINT
# =============================================================================

@router.post("/bookings/{booking_id}/confirm", response_model=BookingConfirmedResponse)
async def confirm_booking(
    booking_id: UUID,
    request: BookingConfirmRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> BookingConfirmedResponse:
    """
    Confirm a booking after successful payment.

    Called by the frontend after Stripe confirms the payment.
    Also called by the Stripe webhook as a backup.

    This endpoint is idempotent - calling it multiple times
    with the same payment_intent_id has no additional effect.
    """
    # Get booking
    query = select(Booking).where(Booking.id == booking_id)
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Idempotency: Already confirmed
    if booking.status == BookingStatus.CONFIRMED.value and booking.payment_status == PaymentStatus.PAID.value:
        return BookingConfirmedResponse(
            booking_id=booking.id,
            booking_reference=booking.booking_reference,
            status=BookingStatus.CONFIRMED,
            payment_status=PaymentStatus.PAID,
            confirmed_at=booking.confirmed_at,
        )

    # Verify booking is in correct state
    if booking.status != BookingStatus.RESERVED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Booking cannot be confirmed from status: {booking.status}"
        )

    # Verify payment intent matches
    if booking.stripe_payment_intent_id != request.payment_intent_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment intent does not match booking"
        )

    # Verify payment with Stripe
    try:
        payment_intent = stripe.PaymentIntent.retrieve(request.payment_intent_id)
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to verify payment: {str(e)}"
        )

    if payment_intent.status != "succeeded":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment not completed. Status: {payment_intent.status}"
        )

    # Update booking status
    now = datetime.utcnow()
    booking.status = BookingStatus.CONFIRMED.value
    booking.payment_status = PaymentStatus.PAID.value
    booking.paid_amount = Decimal(payment_intent.amount_received) / 100
    booking.paid_at = now
    booking.confirmed_at = now
    booking.updated_at = now

    # Update calendar to confirmed (from tentative)
    date_range = [
        booking.check_in + timedelta(days=i)
        for i in range((booking.check_out - booking.check_in).days)
    ]

    calendar_update = (
        CalendarAvailability.__table__.update()
        .where(
            and_(
                CalendarAvailability.property_id == booking.property_id,
                CalendarAvailability.date.in_(date_range),
            )
        )
        .values(
            availability_status="booked",
            updated_at=now,
        )
    )
    await db.execute(calendar_update)

    # Create payment transaction record
    transaction = PaymentTransaction(
        id=uuid4(),
        tenant_id=booking.tenant_id,
        booking_id=booking.id,
        transaction_type="payment",
        amount=booking.total_price,
        currency=booking.currency,
        payment_method="card",  # Would get from Stripe
        status="completed",
        stripe_payment_intent_id=payment_intent.id,
        stripe_charge_id=payment_intent.latest_charge,
        created_at=now,
        completed_at=now,
    )
    db.add(transaction)

    await db.commit()

    # Background tasks
    background_tasks.add_task(
        send_booking_confirmation_email,
        booking.id,
    )
    background_tasks.add_task(
        publish_booking_event,
        booking.id,
        "booking.confirmed",
    )

    return BookingConfirmedResponse(
        booking_id=booking.id,
        booking_reference=booking.booking_reference,
        status=BookingStatus.CONFIRMED,
        payment_status=PaymentStatus.PAID,
        confirmed_at=now,
    )


async def send_booking_confirmation_email(booking_id: UUID):
    """Send confirmation email to guest."""
    # Implementation would use email service
    pass


async def publish_booking_event(booking_id: UUID, event_type: str):
    """Publish event for channel sync and other consumers."""
    # Implementation would publish to Redis Streams or event queue
    pass


# =============================================================================
# BOOKING DETAILS ENDPOINT
# =============================================================================

@router.get("/bookings/{booking_id}", response_model=BookingDetailsResponse)
async def get_booking(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> BookingDetailsResponse:
    """
    Get detailed booking information.

    After confirmation, includes full property address.
    """
    query = (
        select(Booking)
        .where(Booking.id == booking_id)
        .options(
            # Would use SQLAlchemy relationships
            # selectinload(Booking.property),
            # selectinload(Booking.guest),
        )
    )
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Get property
    prop_query = select(Property).where(Property.id == booking.property_id)
    prop_result = await db.execute(prop_query)
    property = prop_result.scalar_one()

    # Get guest
    guest_query = select(Guest).where(Guest.id == booking.guest_id)
    guest_result = await db.execute(guest_query)
    guest = guest_result.scalar_one()

    # Build price breakdown from booking data
    num_nights = (booking.check_out - booking.check_in).days
    avg_nightly = booking.subtotal / num_nights if num_nights > 0 else booking.nightly_rate

    price_breakdown = PriceBreakdown(
        nightly_rates=[
            NightlyRate(date=booking.check_in + timedelta(days=i), price=avg_nightly)
            for i in range(num_nights)
        ],
        subtotal=booking.subtotal,
        cleaning_fee=booking.cleaning_fee,
        service_fee=booking.service_fee,
        taxes=booking.tax_amount or Decimal("0"),
        total=booking.total_price,
        currency=booking.currency,
    )

    # Include full address only after confirmation
    address = PropertyAddress(
        city=property.address.get("city", ""),
        district=property.address.get("district"),
        country=property.address.get("country", ""),
    )
    if booking.status == BookingStatus.CONFIRMED.value:
        address.full_address = property.address.get("full_address")

    return BookingDetailsResponse(
        booking_id=booking.id,
        booking_reference=booking.booking_reference,
        status=BookingStatus(booking.status),
        payment_status=PaymentStatus(booking.payment_status),
        property=PropertyResponse(
            id=property.id,
            name=property.name,
            description=property.description,
            bedrooms=property.bedrooms,
            bathrooms=property.bathrooms,
            max_guests=property.max_guests,
            property_type=property.property_type,
            amenities=property.amenities or [],
            house_rules=property.house_rules or [],
            check_in_time=property.check_in_time.strftime("%H:%M") if property.check_in_time else "15:00",
            check_out_time=property.check_out_time.strftime("%H:%M") if property.check_out_time else "11:00",
            images=[PropertyImage(**img) for img in property.images] if property.images else [],
            address=address,
            rating=property.rating or Decimal("0"),
            review_count=property.review_count or 0,
            instant_book=property.instant_book_enabled,
            base_price=property.base_price,
            currency=property.currency,
            owner=PropertyOwner(
                id=property.owner_id,
                first_name="Host",
            ),
        ),
        guest=GuestDetails(
            first_name=guest.first_name,
            last_name=guest.last_name,
            email=guest.email,
            phone=guest.phone,
        ),
        check_in=booking.check_in,
        check_out=booking.check_out,
        num_guests=booking.num_adults + (booking.num_children or 0),
        num_nights=num_nights,
        special_requests=booking.special_requests,
        pricing=price_breakdown,
        confirmed_at=booking.confirmed_at,
        cancellation_policy={
            "type": "moderate",
            "free_cancellation_until": (booking.check_in - timedelta(days=7)).isoformat(),
            "description": "Free cancellation until 7 days before check-in",
        },
    )


# =============================================================================
# BOOKING CANCELLATION ENDPOINT
# =============================================================================

@router.post("/bookings/{booking_id}/cancel", response_model=BookingCancelResponse)
async def cancel_booking(
    booking_id: UUID,
    request: BookingCancelRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> BookingCancelResponse:
    """
    Cancel a booking.

    If payment was made, initiates refund based on cancellation policy.
    """
    query = select(Booking).where(Booking.id == booking_id)
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Check if cancellable
    if booking.status in [BookingStatus.CHECKED_IN.value, BookingStatus.CHECKED_OUT.value]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a booking that has already started or completed"
        )

    if booking.status == BookingStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled"
        )

    now = datetime.utcnow()
    refund_amount = None
    refund_status = None

    # Process refund if payment was made
    if booking.payment_status == PaymentStatus.PAID.value and booking.stripe_payment_intent_id:
        refund_amount = calculate_refund_amount(booking)

        if refund_amount > 0:
            try:
                # Create Stripe refund
                refund = stripe.Refund.create(
                    payment_intent=booking.stripe_payment_intent_id,
                    amount=int(refund_amount * 100),
                )
                refund_status = "processing" if refund.status == "pending" else "completed"

                # Record refund transaction
                transaction = PaymentTransaction(
                    id=uuid4(),
                    tenant_id=booking.tenant_id,
                    booking_id=booking.id,
                    transaction_type="refund",
                    amount=refund_amount,
                    currency=booking.currency,
                    status="completed",
                    stripe_refund_id=refund.id,
                    description=request.reason or "Guest cancellation",
                    created_at=now,
                    completed_at=now,
                )
                db.add(transaction)

            except stripe.error.StripeError as e:
                # Log error but continue with cancellation
                refund_status = "failed"

    # Update booking status
    booking.status = BookingStatus.CANCELLED.value
    booking.payment_status = PaymentStatus.REFUNDED.value if refund_amount else booking.payment_status
    booking.cancelled_at = now
    booking.cancellation_reason = request.reason
    booking.refund_amount = refund_amount
    booking.updated_at = now

    # Release calendar dates
    date_range = [
        booking.check_in + timedelta(days=i)
        for i in range((booking.check_out - booking.check_in).days)
    ]

    calendar_update = (
        CalendarAvailability.__table__.update()
        .where(
            and_(
                CalendarAvailability.property_id == booking.property_id,
                CalendarAvailability.date.in_(date_range),
                CalendarAvailability.booking_id == booking.id,
            )
        )
        .values(
            available=True,
            availability_status="available",
            booking_id=None,
            updated_at=now,
        )
    )
    await db.execute(calendar_update)

    await db.commit()

    # Background tasks
    background_tasks.add_task(
        send_cancellation_email,
        booking.id,
    )
    background_tasks.add_task(
        publish_booking_event,
        booking.id,
        "booking.cancelled",
    )

    return BookingCancelResponse(
        booking_id=booking.id,
        status=BookingStatus.CANCELLED,
        refund_status=refund_status,
        refund_amount=refund_amount,
    )


def calculate_refund_amount(booking: Booking) -> Decimal:
    """
    Calculate refund amount based on cancellation policy.

    Moderate policy:
    - Full refund if cancelled 7+ days before check-in
    - 50% refund if cancelled 3-6 days before check-in
    - No refund if cancelled < 3 days before check-in
    """
    days_until_checkin = (booking.check_in - date.today()).days

    if days_until_checkin >= 7:
        return booking.total_price
    elif days_until_checkin >= 3:
        return booking.total_price * Decimal("0.5")
    else:
        return Decimal("0")


async def send_cancellation_email(booking_id: UUID):
    """Send cancellation confirmation email to guest."""
    pass


# =============================================================================
# STRIPE WEBHOOK ENDPOINT
# =============================================================================

@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
) -> JSONResponse:
    """
    Handle Stripe webhook events.

    Events handled:
    - payment_intent.succeeded: Confirm booking (backup to frontend confirmation)
    - payment_intent.payment_failed: Mark payment as failed
    - charge.refunded: Update refund status

    Idempotency:
    - Event IDs are cached in Redis to prevent double-processing
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Idempotency check
    event_id = event.id
    if await redis.exists(f"stripe_event:{event_id}"):
        return JSONResponse({"status": "already_processed"})

    # Handle events
    if event.type == "payment_intent.succeeded":
        payment_intent = event.data.object

        # Find booking by payment_intent_id
        query = select(Booking).where(
            Booking.stripe_payment_intent_id == payment_intent.id
        )
        result = await db.execute(query)
        booking = result.scalar_one_or_none()

        if booking and booking.status == BookingStatus.RESERVED.value:
            # Confirm booking (same logic as /confirm endpoint)
            booking.status = BookingStatus.CONFIRMED.value
            booking.payment_status = PaymentStatus.PAID.value
            booking.paid_amount = Decimal(payment_intent.amount_received) / 100
            booking.paid_at = datetime.utcnow()
            booking.confirmed_at = datetime.utcnow()
            booking.updated_at = datetime.utcnow()

            # Update calendar
            date_range = [
                booking.check_in + timedelta(days=i)
                for i in range((booking.check_out - booking.check_in).days)
            ]

            calendar_update = (
                CalendarAvailability.__table__.update()
                .where(
                    and_(
                        CalendarAvailability.property_id == booking.property_id,
                        CalendarAvailability.date.in_(date_range),
                    )
                )
                .values(
                    availability_status="booked",
                    updated_at=datetime.utcnow(),
                )
            )
            await db.execute(calendar_update)

            await db.commit()

            background_tasks.add_task(send_booking_confirmation_email, booking.id)
            background_tasks.add_task(publish_booking_event, booking.id, "booking.confirmed")

    elif event.type == "payment_intent.payment_failed":
        payment_intent = event.data.object

        query = select(Booking).where(
            Booking.stripe_payment_intent_id == payment_intent.id
        )
        result = await db.execute(query)
        booking = result.scalar_one_or_none()

        if booking:
            booking.payment_status = PaymentStatus.FAILED.value
            booking.updated_at = datetime.utcnow()
            await db.commit()

            # Could send payment failure email here

    elif event.type == "charge.refunded":
        charge = event.data.object

        # Find booking and update refund status
        query = select(Booking).where(
            Booking.stripe_charge_id == charge.id
        )
        result = await db.execute(query)
        booking = result.scalar_one_or_none()

        if booking:
            booking.payment_status = PaymentStatus.REFUNDED.value
            booking.refund_amount = Decimal(charge.amount_refunded) / 100
            booking.updated_at = datetime.utcnow()
            await db.commit()

    # Mark event as processed
    await redis.setex(f"stripe_event:{event_id}", 86400, "processed")  # 24h TTL

    return JSONResponse({"status": "success"})


# =============================================================================
# BACKGROUND TASK: CANCEL EXPIRED BOOKINGS
# =============================================================================

async def cancel_expired_booking_task(booking_id: UUID, db: AsyncSession):
    """
    Background task to cancel a booking if payment not completed within timeout.

    Called by Celery worker after BOOKING_RESERVATION_TIMEOUT_MINUTES.
    """
    query = select(Booking).where(Booking.id == booking_id)
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        return

    # Only cancel if still in reserved/pending state
    if booking.status != BookingStatus.RESERVED.value:
        return

    if booking.payment_status != PaymentStatus.PENDING.value:
        return

    now = datetime.utcnow()

    # Cancel the booking
    booking.status = BookingStatus.CANCELLED.value
    booking.payment_status = PaymentStatus.EXPIRED.value
    booking.cancelled_at = now
    booking.cancellation_reason = "Payment timeout"
    booking.updated_at = now

    # Release calendar dates
    date_range = [
        booking.check_in + timedelta(days=i)
        for i in range((booking.check_out - booking.check_in).days)
    ]

    calendar_update = (
        CalendarAvailability.__table__.update()
        .where(
            and_(
                CalendarAvailability.property_id == booking.property_id,
                CalendarAvailability.date.in_(date_range),
                CalendarAvailability.booking_id == booking.id,
            )
        )
        .values(
            available=True,
            availability_status="available",
            booking_id=None,
            updated_at=now,
        )
    )
    await db.execute(calendar_update)

    # Cancel Stripe PaymentIntent if still pending
    if booking.stripe_payment_intent_id:
        try:
            stripe.PaymentIntent.cancel(booking.stripe_payment_intent_id)
        except stripe.error.StripeError:
            pass  # Ignore errors, payment intent may already be cancelled

    await db.commit()

    # Send expiration email
    # await send_booking_expired_email(booking.id)


# =============================================================================
# GUEST INVITATION ENDPOINT (Optional Account Creation)
# =============================================================================

@router.post("/guests/{guest_id}/invite")
async def invite_guest(
    guest_id: UUID,
    message: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),  # Property owner
) -> dict:
    """
    Send an invitation to a guest to create an account.

    Called by property owner after a booking is confirmed.
    Sends a magic link email that allows the guest to create an account
    and link it to their existing bookings.
    """
    # Get guest
    query = select(Guest).where(Guest.id == guest_id)
    result = await db.execute(query)
    guest = result.scalar_one_or_none()

    if not guest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Guest not found"
        )

    # Check if guest already has an account
    if guest.auth_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Guest already has an account"
        )

    # Generate invitation token
    import secrets
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Create invitation record
    invitation = GuestInvitation(
        id=uuid4(),
        guest_id=guest.id,
        token_hash=token_hash,
        invited_by=current_user.id,
        email=guest.email,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(days=7),
        sent_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(invitation)
    await db.commit()

    # Send invitation email with magic link
    # await send_guest_invitation_email(
    #     email=guest.email,
    #     guest_name=guest.first_name,
    #     invitation_token=token,
    #     custom_message=message,
    # )

    return {
        "invitation_id": invitation.id,
        "status": "sent",
        "expires_at": invitation.expires_at.isoformat(),
    }


# =============================================================================
# ADDITIONAL UTILITY ENDPOINTS
# =============================================================================

@router.post("/bookings/{booking_id}/resend-confirmation")
async def resend_confirmation_email(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Resend the booking confirmation email."""
    query = select(Booking).where(Booking.id == booking_id)
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    if booking.status != BookingStatus.CONFIRMED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only resend confirmation for confirmed bookings"
        )

    # await send_booking_confirmation_email(booking.id)

    return {"status": "sent"}


@router.get("/bookings/{booking_id}/calendar-export")
async def export_calendar(
    booking_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generate an .ics file for the booking."""
    query = select(Booking).where(Booking.id == booking_id)
    result = await db.execute(query)
    booking = result.scalar_one_or_none()

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    # Get property name
    prop_query = select(Property).where(Property.id == booking.property_id)
    prop_result = await db.execute(prop_query)
    property = prop_result.scalar_one()

    # Generate ICS content
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//PMS-Webapp//Booking//EN
BEGIN:VEVENT
UID:{booking.id}@pms-webapp.com
DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}
DTSTART;VALUE=DATE:{booking.check_in.strftime('%Y%m%d')}
DTEND;VALUE=DATE:{booking.check_out.strftime('%Y%m%d')}
SUMMARY:Stay at {property.name}
DESCRIPTION:Booking Reference: {booking.booking_reference}
LOCATION:{property.address.get('city', '')}, {property.address.get('country', '')}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""

    from fastapi.responses import Response
    return Response(
        content=ics_content,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="booking-{booking.booking_reference}.ics"'
        }
    )


# =============================================================================
# DEPENDENCY STUBS (Would be in separate modules)
# =============================================================================

async def get_db():
    """Database session dependency."""
    # In production: yield session from async session maker
    pass


async def get_redis():
    """Redis client dependency."""
    # In production: return Redis client
    pass


def get_current_user():
    """Current authenticated user dependency."""
    # In production: decode JWT and return user
    pass


def get_current_user_optional():
    """Optional current user (for guest checkout)."""
    pass
