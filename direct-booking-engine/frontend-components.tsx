/**
 * Direct Booking Engine - Frontend Component Structure
 *
 * Technology Stack:
 * - Next.js 14+ (App Router, Server Components)
 * - TanStack Query (Server State)
 * - Zustand (Client State)
 * - Stripe Elements (Payment)
 * - shadcn/ui (Component Library)
 * - Tailwind CSS (Styling)
 *
 * Version: 1.0.0
 * Last Updated: 2025-12-21
 */

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

export interface Property {
  id: string;
  name: string;
  description: string;
  descriptionShort?: string;
  bedrooms: number;
  bathrooms: number;
  maxGuests: number;
  sizeSqm?: number;
  propertyType: 'apartment' | 'house' | 'villa' | 'studio' | 'loft';
  amenities: string[];
  houseRules: string[];
  checkInTime: string;
  checkOutTime: string;
  images: PropertyImage[];
  address: {
    city: string;
    district?: string;
    country: string;
    fullAddress?: string; // Only shown after booking
  };
  location?: {
    lat: number;
    lng: number;
  };
  rating: number;
  reviewCount: number;
  instantBook: boolean;
  basePrice: number;
  currency: string;
  owner: {
    id: string;
    firstName: string;
    responseRate?: number;
    responseTime?: string;
  };
}

export interface PropertyImage {
  url: string;
  thumbnailUrl?: string;
  caption?: string;
  altText?: string;
  isPrimary: boolean;
}

export interface CalendarDay {
  date: string; // YYYY-MM-DD
  available: boolean;
  status?: 'available' | 'booked' | 'blocked' | 'tentative';
  price: number;
  minStay: number;
  maxStay?: number;
}

export interface PriceBreakdown {
  nightlyRates: { date: string; price: number }[];
  subtotal: number;
  cleaningFee: number;
  serviceFee: number;
  taxes: number;
  total: number;
  currency: string;
}

export interface AvailabilityCheck {
  available: boolean;
  priceBreakdown: PriceBreakdown;
  minimumStay: number;
  maximumStay: number;
  instantBook: boolean;
  cancellationPolicy: string;
}

export interface GuestDetails {
  firstName: string;
  lastName: string;
  email: string;
  phone?: string;
  specialRequests?: string;
  createAccount: boolean;
}

export interface BookingCreate {
  propertyId: string;
  checkIn: string;
  checkOut: string;
  numGuests: number;
  guest: GuestDetails;
}

export interface BookingReserved {
  bookingId: string;
  bookingReference: string;
  status: 'reserved';
  paymentStatus: 'pending';
  totalPrice: number;
  currency: string;
  expiresAt: string;
  stripeClientSecret: string;
}

export interface BookingConfirmed {
  bookingId: string;
  bookingReference: string;
  status: 'confirmed';
  paymentStatus: 'paid';
  confirmedAt: string;
  property: Property;
  guest: GuestDetails;
  checkIn: string;
  checkOut: string;
  numGuests: number;
  numNights: number;
  pricing: PriceBreakdown;
  cancellationPolicy: {
    type: string;
    freeCancellationUntil: string;
    description: string;
  };
}

// =============================================================================
// ZUSTAND STORE - BOOKING FLOW STATE
// =============================================================================

import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface BookingFlowState {
  // Property selection
  propertyId: string | null;
  property: Property | null;

  // Dates
  checkIn: string | null;
  checkOut: string | null;

  // Guests
  numGuests: number;

  // Guest details
  guestDetails: GuestDetails;

  // Pricing
  priceBreakdown: PriceBreakdown | null;

  // Booking
  bookingId: string | null;
  bookingReference: string | null;
  stripeClientSecret: string | null;
  expiresAt: string | null;

  // Status
  status: 'idle' | 'loading' | 'reserved' | 'processing' | 'confirmed' | 'failed' | 'expired';
  error: string | null;

  // Actions
  setProperty: (property: Property) => void;
  setDates: (checkIn: string, checkOut: string) => void;
  setGuests: (numGuests: number) => void;
  updateGuestDetails: (details: Partial<GuestDetails>) => void;
  setPriceBreakdown: (breakdown: PriceBreakdown) => void;
  setBookingReserved: (booking: BookingReserved) => void;
  setStatus: (status: BookingFlowState['status']) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

const initialGuestDetails: GuestDetails = {
  firstName: '',
  lastName: '',
  email: '',
  phone: '',
  specialRequests: '',
  createAccount: false,
};

export const useBookingFlowStore = create<BookingFlowState>()(
  persist(
    (set) => ({
      // Initial state
      propertyId: null,
      property: null,
      checkIn: null,
      checkOut: null,
      numGuests: 2,
      guestDetails: initialGuestDetails,
      priceBreakdown: null,
      bookingId: null,
      bookingReference: null,
      stripeClientSecret: null,
      expiresAt: null,
      status: 'idle',
      error: null,

      // Actions
      setProperty: (property) =>
        set({ propertyId: property.id, property }),

      setDates: (checkIn, checkOut) =>
        set({ checkIn, checkOut }),

      setGuests: (numGuests) =>
        set({ numGuests }),

      updateGuestDetails: (details) =>
        set((state) => ({
          guestDetails: { ...state.guestDetails, ...details },
        })),

      setPriceBreakdown: (priceBreakdown) =>
        set({ priceBreakdown }),

      setBookingReserved: (booking) =>
        set({
          bookingId: booking.bookingId,
          bookingReference: booking.bookingReference,
          stripeClientSecret: booking.stripeClientSecret,
          expiresAt: booking.expiresAt,
          status: 'reserved',
        }),

      setStatus: (status) =>
        set({ status }),

      setError: (error) =>
        set({ error, status: error ? 'failed' : 'idle' }),

      reset: () =>
        set({
          propertyId: null,
          property: null,
          checkIn: null,
          checkOut: null,
          numGuests: 2,
          guestDetails: initialGuestDetails,
          priceBreakdown: null,
          bookingId: null,
          bookingReference: null,
          stripeClientSecret: null,
          expiresAt: null,
          status: 'idle',
          error: null,
        }),
    }),
    {
      name: 'booking-flow-storage',
      partialize: (state) => ({
        // Only persist essential booking data
        propertyId: state.propertyId,
        checkIn: state.checkIn,
        checkOut: state.checkOut,
        numGuests: state.numGuests,
        guestDetails: state.guestDetails,
        bookingId: state.bookingId,
        stripeClientSecret: state.stripeClientSecret,
        expiresAt: state.expiresAt,
        status: state.status,
      }),
    }
  )
);

// =============================================================================
// TANSTACK QUERY - API HOOKS
// =============================================================================

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

// API Client
const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'An error occurred' }));
    throw new Error(error.detail || error.message);
  }

  return response.json();
}

// Property Search Query
interface SearchParams {
  location?: { lat: number; lng: number; radiusKm?: number };
  checkIn?: string;
  checkOut?: string;
  guests?: number;
  filters?: {
    priceMin?: number;
    priceMax?: number;
    bedroomsMin?: number;
    amenities?: string[];
    propertyTypes?: string[];
    instantBook?: boolean;
  };
  sortBy?: 'price_asc' | 'price_desc' | 'rating_desc' | 'distance';
  page?: number;
  limit?: number;
}

interface SearchResponse {
  properties: Property[];
  pagination: {
    total: number;
    page: number;
    pages: number;
    limit: number;
  };
  searchMetadata: {
    locationName: string;
    dates: { checkIn: string; checkOut: string; nights: number };
    guests: number;
  };
}

export function usePropertySearch(params: SearchParams) {
  return useQuery({
    queryKey: ['properties', 'search', params],
    queryFn: () =>
      fetchApi<SearchResponse>('/properties/search', {
        method: 'POST',
        body: JSON.stringify(params),
      }),
    staleTime: 60 * 1000, // 1 minute
  });
}

// Property Detail Query
export function useProperty(propertyId: string) {
  return useQuery({
    queryKey: ['properties', propertyId],
    queryFn: () => fetchApi<Property>(`/properties/${propertyId}`),
    enabled: !!propertyId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Property Calendar Query
export function usePropertyCalendar(propertyId: string, startMonth: string, endMonth: string) {
  return useQuery({
    queryKey: ['properties', propertyId, 'calendar', startMonth, endMonth],
    queryFn: () =>
      fetchApi<{ calendar: CalendarDay[] }>(
        `/properties/${propertyId}/calendar?start=${startMonth}&end=${endMonth}`
      ),
    enabled: !!propertyId,
    staleTime: 30 * 1000, // 30 seconds - availability changes frequently
  });
}

// Availability Check Query
interface AvailabilityParams {
  propertyId: string;
  checkIn: string;
  checkOut: string;
}

export function useAvailabilityCheck(params: AvailabilityParams | null) {
  return useQuery({
    queryKey: ['availability', params],
    queryFn: () =>
      fetchApi<AvailabilityCheck>('/bookings/check-availability', {
        method: 'POST',
        body: JSON.stringify({
          property_id: params!.propertyId,
          check_in: params!.checkIn,
          check_out: params!.checkOut,
        }),
      }),
    enabled: !!params?.propertyId && !!params?.checkIn && !!params?.checkOut,
    staleTime: 10 * 1000, // 10 seconds
    retry: 1,
  });
}

// Create Booking Mutation
export function useCreateBooking() {
  const queryClient = useQueryClient();
  const store = useBookingFlowStore();

  return useMutation({
    mutationFn: (data: BookingCreate) =>
      fetchApi<BookingReserved>('/bookings', {
        method: 'POST',
        body: JSON.stringify({
          property_id: data.propertyId,
          check_in: data.checkIn,
          check_out: data.checkOut,
          num_guests: data.numGuests,
          guest: {
            first_name: data.guest.firstName,
            last_name: data.guest.lastName,
            email: data.guest.email,
            phone: data.guest.phone,
          },
          special_requests: data.guest.specialRequests,
          create_account: data.guest.createAccount,
        }),
      }),
    onSuccess: (booking) => {
      store.setBookingReserved(booking);
      // Invalidate availability for this property
      queryClient.invalidateQueries({ queryKey: ['availability'] });
      queryClient.invalidateQueries({ queryKey: ['properties', store.propertyId, 'calendar'] });
    },
    onError: (error: Error) => {
      store.setError(error.message);
    },
  });
}

// Confirm Booking Mutation
export function useConfirmBooking() {
  const store = useBookingFlowStore();

  return useMutation({
    mutationFn: ({ bookingId, paymentIntentId }: { bookingId: string; paymentIntentId: string }) =>
      fetchApi<BookingConfirmed>(`/bookings/${bookingId}/confirm`, {
        method: 'POST',
        body: JSON.stringify({ payment_intent_id: paymentIntentId }),
      }),
    onSuccess: () => {
      store.setStatus('confirmed');
    },
    onError: (error: Error) => {
      store.setError(error.message);
    },
  });
}

// Get Booking Details Query
export function useBookingDetails(bookingId: string | null) {
  return useQuery({
    queryKey: ['bookings', bookingId],
    queryFn: () => fetchApi<BookingConfirmed>(`/bookings/${bookingId}`),
    enabled: !!bookingId,
  });
}

// =============================================================================
// COMPONENTS - PROPERTY SEARCH (Step 1)
// =============================================================================

import React, { useState, useCallback, useMemo } from 'react';
import { format, addDays, differenceInDays } from 'date-fns';
import { Calendar } from '@/components/ui/calendar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Card, CardContent, CardFooter } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import { CalendarIcon, MapPinIcon, StarIcon, UsersIcon, SearchIcon } from 'lucide-react';

// Search Bar Component
interface SearchBarProps {
  onSearch: (params: SearchParams) => void;
  initialValues?: Partial<SearchParams>;
  loading?: boolean;
}

export function SearchBar({ onSearch, initialValues, loading }: SearchBarProps) {
  const [location, setLocation] = useState(initialValues?.location || null);
  const [locationQuery, setLocationQuery] = useState('');
  const [checkIn, setCheckIn] = useState<Date | undefined>(
    initialValues?.checkIn ? new Date(initialValues.checkIn) : undefined
  );
  const [checkOut, setCheckOut] = useState<Date | undefined>(
    initialValues?.checkOut ? new Date(initialValues.checkOut) : undefined
  );
  const [guests, setGuests] = useState(initialValues?.guests || 2);

  const handleSearch = useCallback(() => {
    onSearch({
      location: location || undefined,
      checkIn: checkIn ? format(checkIn, 'yyyy-MM-dd') : undefined,
      checkOut: checkOut ? format(checkOut, 'yyyy-MM-dd') : undefined,
      guests,
    });
  }, [location, checkIn, checkOut, guests, onSearch]);

  return (
    <div className="flex flex-col md:flex-row gap-2 p-4 bg-white rounded-xl shadow-lg border">
      {/* Location Input */}
      <div className="flex-1 min-w-[200px]">
        <label className="text-sm text-muted-foreground">Location</label>
        <div className="relative">
          <MapPinIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Where are you going?"
            value={locationQuery}
            onChange={(e) => setLocationQuery(e.target.value)}
            className="pl-10"
          />
        </div>
      </div>

      {/* Check-in Date */}
      <div className="flex-1 min-w-[150px]">
        <label className="text-sm text-muted-foreground">Check-in</label>
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className={cn(
                'w-full justify-start text-left font-normal',
                !checkIn && 'text-muted-foreground'
              )}
            >
              <CalendarIcon className="mr-2 h-4 w-4" />
              {checkIn ? format(checkIn, 'MMM d, yyyy') : 'Add dates'}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={checkIn}
              onSelect={(date) => {
                setCheckIn(date);
                if (date && (!checkOut || date >= checkOut)) {
                  setCheckOut(addDays(date, 1));
                }
              }}
              disabled={(date) => date < new Date()}
              initialFocus
            />
          </PopoverContent>
        </Popover>
      </div>

      {/* Check-out Date */}
      <div className="flex-1 min-w-[150px]">
        <label className="text-sm text-muted-foreground">Check-out</label>
        <Popover>
          <PopoverTrigger asChild>
            <Button
              variant="outline"
              className={cn(
                'w-full justify-start text-left font-normal',
                !checkOut && 'text-muted-foreground'
              )}
            >
              <CalendarIcon className="mr-2 h-4 w-4" />
              {checkOut ? format(checkOut, 'MMM d, yyyy') : 'Add dates'}
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-auto p-0" align="start">
            <Calendar
              mode="single"
              selected={checkOut}
              onSelect={setCheckOut}
              disabled={(date) => date <= (checkIn || new Date())}
              initialFocus
            />
          </PopoverContent>
        </Popover>
      </div>

      {/* Guests */}
      <div className="min-w-[120px]">
        <label className="text-sm text-muted-foreground">Guests</label>
        <Select value={guests.toString()} onValueChange={(v) => setGuests(parseInt(v))}>
          <SelectTrigger>
            <UsersIcon className="mr-2 h-4 w-4" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {[1, 2, 3, 4, 5, 6, 7, 8, 10, 12, 16].map((n) => (
              <SelectItem key={n} value={n.toString()}>
                {n} {n === 1 ? 'guest' : 'guests'}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Search Button */}
      <div className="flex items-end">
        <Button onClick={handleSearch} disabled={loading} className="w-full md:w-auto">
          <SearchIcon className="mr-2 h-4 w-4" />
          Search
        </Button>
      </div>
    </div>
  );
}

// Property Card Component
interface PropertyCardProps {
  property: Property;
  checkIn?: string;
  checkOut?: string;
  totalPrice?: number;
  onClick?: () => void;
}

export function PropertyCard({
  property,
  checkIn,
  checkOut,
  totalPrice,
  onClick,
}: PropertyCardProps) {
  const nights = checkIn && checkOut ? differenceInDays(new Date(checkOut), new Date(checkIn)) : null;

  return (
    <Card
      className="overflow-hidden cursor-pointer hover:shadow-lg transition-shadow"
      onClick={onClick}
    >
      {/* Image */}
      <div className="relative aspect-[4/3]">
        <img
          src={property.images.find((i) => i.isPrimary)?.url || property.images[0]?.url}
          alt={property.name}
          className="w-full h-full object-cover"
        />
        {property.instantBook && (
          <Badge className="absolute top-2 left-2" variant="secondary">
            Instant Book
          </Badge>
        )}
      </div>

      <CardContent className="p-4">
        {/* Rating & Location */}
        <div className="flex items-center gap-1 text-sm text-muted-foreground mb-1">
          <StarIcon className="h-4 w-4 fill-yellow-400 text-yellow-400" />
          <span className="font-medium text-foreground">{property.rating.toFixed(1)}</span>
          <span>({property.reviewCount})</span>
          <span className="mx-1">-</span>
          <span>{property.address.city}</span>
        </div>

        {/* Name */}
        <h3 className="font-semibold text-lg line-clamp-1">{property.name}</h3>

        {/* Details */}
        <p className="text-sm text-muted-foreground">
          {property.bedrooms} BR - {property.maxGuests} guests
        </p>
      </CardContent>

      <CardFooter className="px-4 pb-4 pt-0 flex justify-between items-end">
        <div>
          <span className="font-semibold text-lg">
            {property.currency === 'EUR' ? '€' : property.currency}
            {property.basePrice}
          </span>
          <span className="text-muted-foreground"> / night</span>
        </div>
        {totalPrice && nights && (
          <div className="text-right">
            <span className="text-sm text-muted-foreground">
              {property.currency === 'EUR' ? '€' : property.currency}
              {totalPrice} total
            </span>
          </div>
        )}
      </CardFooter>
    </Card>
  );
}

// Property Card Skeleton
export function PropertyCardSkeleton() {
  return (
    <Card className="overflow-hidden">
      <Skeleton className="aspect-[4/3]" />
      <CardContent className="p-4">
        <Skeleton className="h-4 w-1/2 mb-2" />
        <Skeleton className="h-6 w-3/4 mb-2" />
        <Skeleton className="h-4 w-1/3" />
      </CardContent>
      <CardFooter className="px-4 pb-4 pt-0">
        <Skeleton className="h-6 w-1/4" />
      </CardFooter>
    </Card>
  );
}

// =============================================================================
// COMPONENTS - PROPERTY DETAIL (Step 2)
// =============================================================================

// Availability Calendar Component
interface AvailabilityCalendarProps {
  propertyId: string;
  selectedCheckIn: Date | null;
  selectedCheckOut: Date | null;
  onDateSelect: (checkIn: Date, checkOut: Date | null) => void;
  minStay?: number;
  className?: string;
}

export function AvailabilityCalendar({
  propertyId,
  selectedCheckIn,
  selectedCheckOut,
  onDateSelect,
  minStay = 1,
  className,
}: AvailabilityCalendarProps) {
  const [currentMonth, setCurrentMonth] = useState(new Date());
  const startMonth = format(currentMonth, 'yyyy-MM');
  const endMonth = format(addDays(currentMonth, 60), 'yyyy-MM');

  const { data, isLoading } = usePropertyCalendar(propertyId, startMonth, endMonth);

  const calendarDays = useMemo(() => {
    if (!data?.calendar) return new Map<string, CalendarDay>();
    return new Map(data.calendar.map((day) => [day.date, day]));
  }, [data]);

  const isDateDisabled = useCallback(
    (date: Date) => {
      const dateStr = format(date, 'yyyy-MM-dd');
      const day = calendarDays.get(dateStr);
      if (!day) return true;
      if (!day.available) return true;
      if (date < new Date()) return true;
      return false;
    },
    [calendarDays]
  );

  const getDayContent = useCallback(
    (date: Date) => {
      const dateStr = format(date, 'yyyy-MM-dd');
      const day = calendarDays.get(dateStr);
      if (!day) return null;

      const isSelected =
        (selectedCheckIn && format(selectedCheckIn, 'yyyy-MM-dd') === dateStr) ||
        (selectedCheckOut && format(selectedCheckOut, 'yyyy-MM-dd') === dateStr);

      const isInRange =
        selectedCheckIn &&
        selectedCheckOut &&
        date > selectedCheckIn &&
        date < selectedCheckOut;

      return (
        <div
          className={cn(
            'relative w-full h-full flex flex-col items-center justify-center',
            isSelected && 'bg-primary text-primary-foreground rounded-md',
            isInRange && 'bg-primary/10',
            !day.available && 'bg-muted line-through text-muted-foreground'
          )}
        >
          <span>{date.getDate()}</span>
          {day.available && (
            <span className="text-xs text-muted-foreground">
              {day.price}
            </span>
          )}
        </div>
      );
    },
    [calendarDays, selectedCheckIn, selectedCheckOut]
  );

  const handleDateClick = useCallback(
    (date: Date | undefined) => {
      if (!date) return;

      // First click: set check-in
      if (!selectedCheckIn || (selectedCheckIn && selectedCheckOut)) {
        onDateSelect(date, null);
        return;
      }

      // Second click: set check-out (must be after check-in)
      if (date > selectedCheckIn) {
        const nights = differenceInDays(date, selectedCheckIn);
        if (nights < minStay) {
          // Show error or adjust date
          return;
        }
        onDateSelect(selectedCheckIn, date);
      } else {
        // Clicked before check-in, reset
        onDateSelect(date, null);
      }
    },
    [selectedCheckIn, selectedCheckOut, minStay, onDateSelect]
  );

  if (isLoading) {
    return (
      <div className={cn('space-y-2', className)}>
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className={cn('space-y-4', className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">Availability</h3>
        {minStay > 1 && (
          <span className="text-sm text-muted-foreground">
            Minimum stay: {minStay} nights
          </span>
        )}
      </div>

      <Calendar
        mode="single"
        selected={selectedCheckIn || undefined}
        onSelect={handleDateClick}
        disabled={isDateDisabled}
        numberOfMonths={2}
        className="rounded-md border"
        components={{
          DayContent: ({ date }) => getDayContent(date),
        }}
      />

      <div className="flex gap-4 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-primary rounded" />
          <span>Selected</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-white border rounded" />
          <span>Available</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-muted rounded" />
          <span>Unavailable</span>
        </div>
      </div>
    </div>
  );
}

// Pricing Breakdown Component
interface PricingBreakdownProps {
  breakdown: PriceBreakdown | null;
  isLoading?: boolean;
  className?: string;
}

export function PricingBreakdown({ breakdown, isLoading, className }: PricingBreakdownProps) {
  if (isLoading) {
    return (
      <div className={cn('space-y-3', className)}>
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-6 w-full" />
      </div>
    );
  }

  if (!breakdown) {
    return (
      <div className={cn('text-muted-foreground text-sm', className)}>
        Select dates to see pricing
      </div>
    );
  }

  const currencySymbol = breakdown.currency === 'EUR' ? '€' : breakdown.currency;
  const nights = breakdown.nightlyRates.length;

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex justify-between text-sm">
        <span>
          {currencySymbol}
          {Math.round(breakdown.subtotal / nights)} x {nights} nights
        </span>
        <span>
          {currencySymbol}
          {breakdown.subtotal}
        </span>
      </div>

      {breakdown.cleaningFee > 0 && (
        <div className="flex justify-between text-sm">
          <span>Cleaning fee</span>
          <span>
            {currencySymbol}
            {breakdown.cleaningFee}
          </span>
        </div>
      )}

      {breakdown.serviceFee > 0 && (
        <div className="flex justify-between text-sm">
          <span>Service fee</span>
          <span>
            {currencySymbol}
            {breakdown.serviceFee}
          </span>
        </div>
      )}

      {breakdown.taxes > 0 && (
        <div className="flex justify-between text-sm">
          <span>Taxes</span>
          <span>
            {currencySymbol}
            {breakdown.taxes}
          </span>
        </div>
      )}

      <div className="border-t pt-3 flex justify-between font-semibold">
        <span>Total</span>
        <span>
          {currencySymbol}
          {breakdown.total}
        </span>
      </div>
    </div>
  );
}

// Booking Widget (Sticky Sidebar)
interface BookingWidgetProps {
  property: Property;
  checkIn: Date | null;
  checkOut: Date | null;
  guests: number;
  onDatesChange: (checkIn: Date, checkOut: Date | null) => void;
  onGuestsChange: (guests: number) => void;
  onBookNow: () => void;
  className?: string;
}

export function BookingWidget({
  property,
  checkIn,
  checkOut,
  guests,
  onDatesChange,
  onGuestsChange,
  onBookNow,
  className,
}: BookingWidgetProps) {
  const availabilityParams = useMemo(() => {
    if (!checkIn || !checkOut) return null;
    return {
      propertyId: property.id,
      checkIn: format(checkIn, 'yyyy-MM-dd'),
      checkOut: format(checkOut, 'yyyy-MM-dd'),
    };
  }, [property.id, checkIn, checkOut]);

  const { data: availability, isLoading } = useAvailabilityCheck(availabilityParams);

  const currencySymbol = property.currency === 'EUR' ? '€' : property.currency;

  return (
    <Card className={cn('sticky top-4', className)}>
      <CardContent className="p-6 space-y-4">
        {/* Price Header */}
        <div>
          <span className="text-2xl font-bold">
            {currencySymbol}
            {property.basePrice}
          </span>
          <span className="text-muted-foreground"> / night</span>
          <div className="flex items-center gap-1 text-sm mt-1">
            <StarIcon className="h-4 w-4 fill-yellow-400 text-yellow-400" />
            <span>{property.rating.toFixed(1)}</span>
            <span className="text-muted-foreground">({property.reviewCount} reviews)</span>
          </div>
        </div>

        {/* Date Selection */}
        <div className="grid grid-cols-2 border rounded-lg overflow-hidden">
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="ghost"
                className="rounded-none border-r h-auto py-3 flex flex-col items-start"
              >
                <span className="text-xs font-medium">CHECK-IN</span>
                <span className={cn(!checkIn && 'text-muted-foreground')}>
                  {checkIn ? format(checkIn, 'MMM d, yyyy') : 'Add date'}
                </span>
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={checkIn || undefined}
                onSelect={(date) => date && onDatesChange(date, checkOut)}
                disabled={(date) => date < new Date()}
                initialFocus
              />
            </PopoverContent>
          </Popover>

          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="ghost"
                className="rounded-none h-auto py-3 flex flex-col items-start"
              >
                <span className="text-xs font-medium">CHECK-OUT</span>
                <span className={cn(!checkOut && 'text-muted-foreground')}>
                  {checkOut ? format(checkOut, 'MMM d, yyyy') : 'Add date'}
                </span>
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={checkOut || undefined}
                onSelect={(date) => checkIn && date && onDatesChange(checkIn, date)}
                disabled={(date) => date <= (checkIn || new Date())}
                initialFocus
              />
            </PopoverContent>
          </Popover>
        </div>

        {/* Guests */}
        <div className="border rounded-lg p-3">
          <label className="text-xs font-medium">GUESTS</label>
          <Select value={guests.toString()} onValueChange={(v) => onGuestsChange(parseInt(v))}>
            <SelectTrigger className="border-0 p-0 h-auto">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Array.from({ length: property.maxGuests }, (_, i) => i + 1).map((n) => (
                <SelectItem key={n} value={n.toString()}>
                  {n} {n === 1 ? 'guest' : 'guests'}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Pricing Breakdown */}
        <PricingBreakdown breakdown={availability?.priceBreakdown || null} isLoading={isLoading} />

        {/* Book Now Button */}
        <Button
          className="w-full"
          size="lg"
          onClick={onBookNow}
          disabled={!checkIn || !checkOut || !availability?.available}
        >
          {availability?.available === false
            ? 'Not Available'
            : property.instantBook
            ? 'Book Now'
            : 'Request to Book'}
        </Button>

        {availability?.available && (
          <p className="text-center text-sm text-muted-foreground">
            You won't be charged yet
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// COMPONENTS - GUEST DETAILS FORM (Step 3)
// =============================================================================

import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';

const guestDetailsSchema = z.object({
  firstName: z.string().min(1, 'First name is required').max(50),
  lastName: z.string().min(1, 'Last name is required').max(50),
  email: z.string().email('Please enter a valid email address'),
  phone: z.string().optional(),
  specialRequests: z.string().max(500, 'Maximum 500 characters').optional(),
  createAccount: z.boolean().default(false),
});

type GuestDetailsFormData = z.infer<typeof guestDetailsSchema>;

interface GuestDetailsFormProps {
  initialValues?: Partial<GuestDetailsFormData>;
  onSubmit: (data: GuestDetailsFormData) => void;
  isSubmitting?: boolean;
}

export function GuestDetailsForm({ initialValues, onSubmit, isSubmitting }: GuestDetailsFormProps) {
  const form = useForm<GuestDetailsFormData>({
    resolver: zodResolver(guestDetailsSchema),
    defaultValues: {
      firstName: '',
      lastName: '',
      email: '',
      phone: '',
      specialRequests: '',
      createAccount: false,
      ...initialValues,
    },
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Your Information</h2>

          <div className="grid grid-cols-2 gap-4">
            <FormField
              control={form.control}
              name="firstName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>First Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="John" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            <FormField
              control={form.control}
              name="lastName"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Last Name *</FormLabel>
                  <FormControl>
                    <Input placeholder="Doe" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>

          <FormField
            control={form.control}
            name="email"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Email Address *</FormLabel>
                <FormControl>
                  <Input type="email" placeholder="john.doe@example.com" {...field} />
                </FormControl>
                <FormDescription>Confirmation will be sent here</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="phone"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Phone Number</FormLabel>
                <FormControl>
                  <Input type="tel" placeholder="+49 171 234 5678" {...field} />
                </FormControl>
                <FormDescription>For urgent booking updates (optional)</FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Special Requests</h2>

          <FormField
            control={form.control}
            name="specialRequests"
            render={({ field }) => (
              <FormItem>
                <FormControl>
                  <Textarea
                    placeholder="Any special requests or notes for your host..."
                    className="min-h-[100px]"
                    {...field}
                  />
                </FormControl>
                <FormDescription>
                  Special requests are not guaranteed but the host will do their best to accommodate
                </FormDescription>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <div className="space-y-4">
          <h2 className="text-xl font-semibold">Account Options</h2>

          <FormField
            control={form.control}
            name="createAccount"
            render={({ field }) => (
              <FormItem className="flex flex-row items-start space-x-3 space-y-0 rounded-md border p-4">
                <FormControl>
                  <Checkbox checked={field.value} onCheckedChange={field.onChange} />
                </FormControl>
                <div className="space-y-1 leading-none">
                  <FormLabel>Create an account for future bookings</FormLabel>
                  <FormDescription>
                    Manage your bookings easily, receive personalized recommendations, and faster
                    checkout for future stays
                  </FormDescription>
                </div>
              </FormItem>
            )}
          />
        </div>

        <div className="pt-4">
          <p className="text-sm text-muted-foreground mb-4">
            By continuing, you agree to our{' '}
            <a href="/terms" className="underline">
              Terms of Service
            </a>{' '}
            and{' '}
            <a href="/privacy" className="underline">
              Privacy Policy
            </a>
          </p>

          <Button type="submit" className="w-full" size="lg" disabled={isSubmitting}>
            {isSubmitting ? 'Creating booking...' : 'Continue to Payment'}
          </Button>
        </div>
      </form>
    </Form>
  );
}

// Booking Summary Component
interface BookingSummaryProps {
  property: Property;
  checkIn: string;
  checkOut: string;
  guests: number;
  priceBreakdown: PriceBreakdown | null;
  onEdit?: () => void;
  className?: string;
}

export function BookingSummary({
  property,
  checkIn,
  checkOut,
  guests,
  priceBreakdown,
  onEdit,
  className,
}: BookingSummaryProps) {
  const nights = differenceInDays(new Date(checkOut), new Date(checkIn));
  const checkInDate = new Date(checkIn);
  const checkOutDate = new Date(checkOut);

  return (
    <Card className={className}>
      <CardContent className="p-6 space-y-4">
        <h2 className="text-xl font-semibold">Booking Summary</h2>

        {/* Property */}
        <div className="flex gap-4">
          <img
            src={property.images.find((i) => i.isPrimary)?.url || property.images[0]?.url}
            alt={property.name}
            className="w-24 h-20 object-cover rounded-lg"
          />
          <div>
            <h3 className="font-medium">{property.name}</h3>
            <p className="text-sm text-muted-foreground">{property.address.city}</p>
            <div className="flex items-center gap-1 text-sm">
              <StarIcon className="h-3 w-3 fill-yellow-400 text-yellow-400" />
              <span>{property.rating.toFixed(1)}</span>
              <span className="text-muted-foreground">({property.reviewCount})</span>
            </div>
          </div>
        </div>

        <div className="border-t pt-4 space-y-2">
          {/* Check-in */}
          <div>
            <span className="text-sm text-muted-foreground">Check-in</span>
            <p className="font-medium">
              {format(checkInDate, 'EEE, MMM d, yyyy')}
              <span className="text-muted-foreground font-normal ml-2">
                {property.checkInTime}
              </span>
            </p>
          </div>

          {/* Check-out */}
          <div>
            <span className="text-sm text-muted-foreground">Check-out</span>
            <p className="font-medium">
              {format(checkOutDate, 'EEE, MMM d, yyyy')}
              <span className="text-muted-foreground font-normal ml-2">
                {property.checkOutTime}
              </span>
            </p>
          </div>

          {/* Guests & Nights */}
          <div className="flex gap-4">
            <div>
              <span className="text-sm text-muted-foreground">Guests</span>
              <p className="font-medium">{guests}</p>
            </div>
            <div>
              <span className="text-sm text-muted-foreground">Nights</span>
              <p className="font-medium">{nights}</p>
            </div>
          </div>
        </div>

        {/* Price Details */}
        <div className="border-t pt-4">
          <h3 className="font-medium mb-3">Price Details</h3>
          <PricingBreakdown breakdown={priceBreakdown} />
        </div>

        {onEdit && (
          <Button variant="link" className="p-0 h-auto" onClick={onEdit}>
            Edit dates or guests
          </Button>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// COMPONENTS - PAYMENT (Step 4)
// =============================================================================

import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js';
import { LockIcon, AlertCircleIcon } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

// Initialize Stripe
const stripePromise = loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY!);

// Payment Timer Component
interface PaymentTimerProps {
  expiresAt: string;
  onExpired: () => void;
}

export function PaymentTimer({ expiresAt, onExpired }: PaymentTimerProps) {
  const [timeLeft, setTimeLeft] = useState<number>(0);

  React.useEffect(() => {
    const updateTimer = () => {
      const now = new Date().getTime();
      const expires = new Date(expiresAt).getTime();
      const remaining = Math.max(0, expires - now);
      setTimeLeft(remaining);

      if (remaining === 0) {
        onExpired();
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [expiresAt, onExpired]);

  const minutes = Math.floor(timeLeft / 60000);
  const seconds = Math.floor((timeLeft % 60000) / 1000);

  const isUrgent = minutes < 5;
  const isVeryUrgent = minutes < 1;

  return (
    <div
      className={cn(
        'flex items-center gap-2 text-sm font-medium',
        isVeryUrgent && 'text-destructive',
        isUrgent && !isVeryUrgent && 'text-amber-600'
      )}
    >
      <span>Complete payment within</span>
      <span className="font-mono">
        {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
      </span>
    </div>
  );
}

// Stripe Payment Form (Inner Component)
interface StripePaymentFormInnerProps {
  bookingId: string;
  amount: number;
  currency: string;
  onSuccess: () => void;
  onError: (error: string) => void;
}

function StripePaymentFormInner({
  bookingId,
  amount,
  currency,
  onSuccess,
  onError,
}: StripePaymentFormInnerProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const [termsAccepted, setTermsAccepted] = useState(false);

  const confirmBooking = useConfirmBooking();
  const MAX_RETRIES = 3;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!stripe || !elements) {
      return;
    }

    if (!termsAccepted) {
      setError('Please accept the terms and conditions');
      return;
    }

    setIsProcessing(true);
    setError(null);

    try {
      const { error: submitError, paymentIntent } = await stripe.confirmPayment({
        elements,
        redirect: 'if_required',
        confirmParams: {
          return_url: `${window.location.origin}/booking/${bookingId}/confirmation`,
        },
      });

      if (submitError) {
        // Handle error
        if (retryCount < MAX_RETRIES - 1) {
          setRetryCount((prev) => prev + 1);
          setError(`Payment failed. ${submitError.message}. Attempt ${retryCount + 1}/${MAX_RETRIES}`);
        } else {
          setError(`Payment failed after ${MAX_RETRIES} attempts. ${submitError.message}`);
          onError(submitError.message || 'Payment failed');
        }
        setIsProcessing(false);
        return;
      }

      if (paymentIntent && paymentIntent.status === 'succeeded') {
        // Confirm booking with backend
        await confirmBooking.mutateAsync({
          bookingId,
          paymentIntentId: paymentIntent.id,
        });

        onSuccess();
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Payment failed';
      setError(errorMessage);
      onError(errorMessage);
    } finally {
      setIsProcessing(false);
    }
  };

  const currencySymbol = currency === 'EUR' ? '€' : currency;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <Alert variant="destructive">
          <AlertCircleIcon className="h-4 w-4" />
          <AlertTitle>Payment Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Payment Information</h2>

        <PaymentElement
          options={{
            layout: 'tabs',
          }}
        />
      </div>

      <div className="space-y-3">
        <div className="flex items-start space-x-3">
          <Checkbox
            id="terms"
            checked={termsAccepted}
            onCheckedChange={(checked) => setTermsAccepted(checked === true)}
          />
          <label htmlFor="terms" className="text-sm leading-relaxed">
            I agree to the{' '}
            <a href="/terms" className="underline">
              Terms of Service
            </a>
            ,{' '}
            <a href="/privacy" className="underline">
              Privacy Policy
            </a>
            , and{' '}
            <a href="#" className="underline">
              House Rules
            </a>
          </label>
        </div>

        <div className="flex items-start space-x-3">
          <Checkbox id="cancellation" checked={termsAccepted} disabled />
          <label htmlFor="cancellation" className="text-sm">
            I understand the cancellation policy
          </label>
        </div>
      </div>

      <Button
        type="submit"
        className="w-full"
        size="lg"
        disabled={!stripe || isProcessing || !termsAccepted}
      >
        {isProcessing ? (
          <>Processing...</>
        ) : (
          <>
            <LockIcon className="mr-2 h-4 w-4" />
            Pay {currencySymbol}
            {amount} & Confirm Booking
          </>
        )}
      </Button>

      <p className="text-center text-sm text-muted-foreground">
        Your payment is secure and encrypted. Powered by Stripe.
      </p>
    </form>
  );
}

// Stripe Payment Form Wrapper
interface StripePaymentFormProps {
  clientSecret: string;
  bookingId: string;
  amount: number;
  currency: string;
  expiresAt: string;
  onSuccess: () => void;
  onError: (error: string) => void;
  onExpired: () => void;
}

export function StripePaymentForm({
  clientSecret,
  bookingId,
  amount,
  currency,
  expiresAt,
  onSuccess,
  onError,
  onExpired,
}: StripePaymentFormProps) {
  const appearance = {
    theme: 'stripe' as const,
    variables: {
      colorPrimary: '#0f172a',
      borderRadius: '8px',
    },
  };

  return (
    <div className="space-y-6">
      <PaymentTimer expiresAt={expiresAt} onExpired={onExpired} />

      <Elements stripe={stripePromise} options={{ clientSecret, appearance }}>
        <StripePaymentFormInner
          bookingId={bookingId}
          amount={amount}
          currency={currency}
          onSuccess={onSuccess}
          onError={onError}
        />
      </Elements>
    </div>
  );
}

// =============================================================================
// COMPONENTS - CONFIRMATION (Step 5)
// =============================================================================

import { CheckCircleIcon, CalendarPlusIcon, PrinterIcon, MailIcon } from 'lucide-react';

interface BookingConfirmationProps {
  booking: BookingConfirmed;
  onAddToCalendar: () => void;
  onPrint: () => void;
  onResendEmail: () => void;
  onCreateAccount?: () => void;
}

export function BookingConfirmation({
  booking,
  onAddToCalendar,
  onPrint,
  onResendEmail,
  onCreateAccount,
}: BookingConfirmationProps) {
  const checkInDate = new Date(booking.checkIn);
  const checkOutDate = new Date(booking.checkOut);

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Success Header */}
      <div className="text-center py-8 bg-green-50 rounded-xl">
        <CheckCircleIcon className="h-16 w-16 text-green-600 mx-auto mb-4" />
        <h1 className="text-3xl font-bold mb-2">Booking Confirmed!</h1>
        <p className="text-lg text-muted-foreground">
          Thank you, {booking.guest.firstName}! Your booking is complete.
        </p>
        <p className="font-mono text-lg mt-4">
          Confirmation #{booking.bookingReference}
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          A confirmation email has been sent to {booking.guest.email}
        </p>
      </div>

      {/* Booking Details */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardContent className="p-6 space-y-4">
            <h2 className="text-xl font-semibold">Booking Details</h2>

            <div>
              <span className="text-sm text-muted-foreground">Check-in</span>
              <p className="font-medium">
                {format(checkInDate, 'EEEE, MMMM d, yyyy')}
              </p>
              <p className="text-muted-foreground">
                {booking.property.checkInTime} - 10:00 PM
              </p>
            </div>

            <div>
              <span className="text-sm text-muted-foreground">Check-out</span>
              <p className="font-medium">
                {format(checkOutDate, 'EEEE, MMMM d, yyyy')}
              </p>
              <p className="text-muted-foreground">
                Until {booking.property.checkOutTime}
              </p>
            </div>

            <div className="flex gap-4">
              <div>
                <span className="text-sm text-muted-foreground">Guests</span>
                <p className="font-medium">{booking.numGuests}</p>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">Nights</span>
                <p className="font-medium">{booking.numNights}</p>
              </div>
            </div>

            <div className="border-t pt-4">
              <span className="text-sm text-muted-foreground">Total Paid</span>
              <p className="text-2xl font-bold">
                {booking.pricing.currency === 'EUR' ? '€' : booking.pricing.currency}
                {booking.pricing.total}
              </p>
            </div>

            <div className="border-t pt-4">
              <h3 className="font-medium mb-2">Guest</h3>
              <p>
                {booking.guest.firstName} {booking.guest.lastName}
              </p>
              <p className="text-muted-foreground">{booking.guest.email}</p>
              {booking.guest.phone && (
                <p className="text-muted-foreground">{booking.guest.phone}</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-6 space-y-4">
            <h2 className="text-xl font-semibold">Property</h2>

            <img
              src={
                booking.property.images.find((i) => i.isPrimary)?.url ||
                booking.property.images[0]?.url
              }
              alt={booking.property.name}
              className="w-full h-40 object-cover rounded-lg"
            />

            <div>
              <h3 className="font-semibold text-lg">{booking.property.name}</h3>
              <p className="text-muted-foreground">{booking.property.address.city}</p>
              {booking.property.address.fullAddress && (
                <p className="text-sm mt-2">{booking.property.address.fullAddress}</p>
              )}
            </div>

            <div className="border-t pt-4">
              <h3 className="font-medium mb-2">Host</h3>
              <p>{booking.property.owner.firstName}</p>
              <p className="text-sm text-muted-foreground">
                Response time: {booking.property.owner.responseTime}
              </p>
              <Button variant="outline" className="mt-2">
                Contact Host
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Next Steps */}
      <Card>
        <CardContent className="p-6">
          <h2 className="text-xl font-semibold mb-4">Next Steps</h2>
          <ol className="space-y-3 list-decimal list-inside text-muted-foreground">
            <li>Check your email for detailed check-in instructions</li>
            <li>The host will contact you within 24 hours</li>
            <li>Check-in instructions will be sent 24 hours before arrival</li>
          </ol>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex flex-wrap gap-4 justify-center">
        <Button variant="outline" onClick={onAddToCalendar}>
          <CalendarPlusIcon className="mr-2 h-4 w-4" />
          Add to Calendar
        </Button>
        <Button variant="outline" onClick={onPrint}>
          <PrinterIcon className="mr-2 h-4 w-4" />
          Print Confirmation
        </Button>
        <Button variant="outline" onClick={onResendEmail}>
          <MailIcon className="mr-2 h-4 w-4" />
          Resend Email
        </Button>
      </div>

      {/* Account Creation CTA */}
      {onCreateAccount && (
        <Card className="bg-muted/50">
          <CardContent className="p-6 text-center">
            <h3 className="font-semibold mb-2">Want to manage your booking easily?</h3>
            <p className="text-muted-foreground mb-4">
              Create an account to view all your bookings in one place
            </p>
            <Button onClick={onCreateAccount}>Create Account</Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// =============================================================================
// PAGE COMPONENTS (Next.js App Router)
// =============================================================================

// These would be in separate files in the actual app structure:
// - app/properties/page.tsx
// - app/properties/[id]/page.tsx
// - app/booking/[propertyId]/details/page.tsx
// - app/booking/[bookingId]/payment/page.tsx
// - app/booking/[bookingId]/confirmation/page.tsx

// Example page structure for reference:

/*
// app/properties/page.tsx
import { Suspense } from 'react';
import { SearchBar, PropertyCard, PropertyCardSkeleton } from './components';
import { PropertySearchResults } from './search-results';

export default function PropertiesPage({
  searchParams,
}: {
  searchParams: { [key: string]: string | string[] | undefined };
}) {
  return (
    <div className="container py-8">
      <SearchBar
        onSearch={(params) => {
          // Update URL with search params
        }}
        initialValues={{
          checkIn: searchParams.check_in as string,
          checkOut: searchParams.check_out as string,
          guests: parseInt(searchParams.guests as string) || 2,
        }}
      />

      <Suspense
        fallback={
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mt-8">
            {Array.from({ length: 6 }).map((_, i) => (
              <PropertyCardSkeleton key={i} />
            ))}
          </div>
        }
      >
        <PropertySearchResults searchParams={searchParams} />
      </Suspense>
    </div>
  );
}
*/

export {};
