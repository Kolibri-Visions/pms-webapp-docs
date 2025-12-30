# ADR-006: Frontend Framework Choice

**Status:** Accepted
**Date:** 2025-12-21
**Decision Makers:** System Architecture Team

---

## Context

We need to select a frontend framework for the PMS-Webapp that will:
- Serve property owners (dashboard, management)
- Serve guests (property search, direct booking)
- Provide excellent SEO for property listing pages
- Enable fast, responsive user experiences
- Integrate with FastAPI backend and Supabase Auth
- Support future mobile app development

## Decision Drivers

1. **SEO**: Property listing pages must be indexed by search engines
2. **Performance**: Fast initial load and interactions
3. **Developer Experience**: Productive development workflow
4. **Ecosystem**: Rich component libraries, good tooling
5. **Type Safety**: TypeScript support
6. **Hosting**: Easy, cost-effective deployment

## Options Considered

### Option 1: Next.js 14+ (App Router)

**Pros:**
- Server Components for fast initial loads
- Excellent SEO with SSR/SSG
- React Server Actions for form handling
- Built-in API routes (optional)
- Vercel deployment with edge caching
- Large ecosystem, mature framework
- TypeScript first-class support

**Cons:**
- React-specific (no Vue/Angular migration)
- App Router relatively new (some ecosystem catching up)
- Vercel-optimized (vendor affinity)

### Option 2: Nuxt 3 (Vue)

**Pros:**
- Vue 3 with Composition API
- SSR/SSG support
- Good performance
- Simpler learning curve than React

**Cons:**
- Smaller ecosystem than React
- Fewer component libraries
- Vue talent pool smaller

### Option 3: SvelteKit

**Pros:**
- Excellent performance (compiled)
- Simple, intuitive syntax
- Built-in SSR/SSG
- Smaller bundle sizes

**Cons:**
- Smallest ecosystem
- Fewer experienced developers
- Less mature tooling

### Option 4: Remix

**Pros:**
- Progressive enhancement focus
- Excellent data loading patterns
- Web standards-based

**Cons:**
- Smaller community than Next.js
- Fewer deployment options
- Less mature ecosystem

## Decision

**We choose Next.js 14+ with App Router** for the following reasons:

1. **Server Components**: React Server Components (RSC) enable fast initial loads with minimal JavaScript, perfect for SEO-critical property pages.

2. **SEO Excellence**: SSR and SSG options ensure property listings are fully indexed. Metadata API simplifies Open Graph/Twitter cards.

3. **React Ecosystem**: Access to the largest JavaScript component ecosystem (shadcn/ui, Radix, TanStack Query).

4. **Vercel Integration**: Seamless deployment with edge caching, image optimization, and analytics.

5. **TypeScript-First**: Full TypeScript support with excellent IDE integration.

6. **Industry Standard**: Large talent pool, extensive documentation, and community support.

## Consequences

### Positive

- Excellent SEO for property listings
- Fast Time to First Byte (TTFB) with RSC
- Rich component ecosystem
- Easy deployment and scaling
- Strong TypeScript support

### Negative

- React learning curve for new developers
- App Router patterns still evolving
- Some client-side libraries need adaptation for RSC

### Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| App Router breaking changes | Pin Next.js version, staged upgrades |
| Bundle size creep | Bundle analyzer, code splitting, lazy loading |
| Client/Server component confusion | Clear component organization, team training |
| Vercel lock-in | Standard Node.js; can self-host or use other platforms |

## Architecture

### Project Structure

```
src/
├── app/                      # App Router pages
│   ├── (marketing)/          # Public pages (no auth)
│   │   ├── page.tsx          # Landing page
│   │   ├── properties/
│   │   │   ├── page.tsx      # Search results
│   │   │   └── [id]/
│   │   │       └── page.tsx  # Property detail
│   │   └── layout.tsx
│   ├── (booking)/            # Booking flow
│   │   ├── checkout/
│   │   │   └── page.tsx
│   │   └── confirmation/
│   │       └── page.tsx
│   ├── (dashboard)/          # Owner dashboard (protected)
│   │   ├── layout.tsx        # Auth wrapper
│   │   ├── page.tsx          # Dashboard home
│   │   ├── properties/
│   │   ├── bookings/
│   │   ├── calendar/
│   │   ├── guests/
│   │   ├── channels/
│   │   └── settings/
│   ├── api/                  # API routes (optional)
│   │   └── webhooks/         # Stripe webhooks
│   └── layout.tsx            # Root layout
├── components/
│   ├── ui/                   # shadcn/ui components
│   ├── booking/              # Booking-related components
│   ├── dashboard/            # Dashboard components
│   └── shared/               # Shared components
├── lib/
│   ├── api.ts                # API client
│   ├── supabase/             # Supabase client setup
│   ├── stripe.ts             # Stripe integration
│   └── utils.ts              # Utilities
├── hooks/                    # Custom React hooks
├── types/                    # TypeScript types
└── styles/                   # Global styles
```

### Key Pages

```tsx
// app/(marketing)/properties/[id]/page.tsx
// Property detail page - Server Component for SEO

import { getProperty } from '@/lib/api';
import { PropertyGallery } from '@/components/property/gallery';
import { BookingWidget } from '@/components/booking/widget';
import { Metadata } from 'next';

interface Props {
  params: { id: string };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const property = await getProperty(params.id);

  return {
    title: `${property.name} | PMS-Webapp`,
    description: property.description.slice(0, 160),
    openGraph: {
      title: property.name,
      description: property.description,
      images: [property.images[0].url],
    },
  };
}

export default async function PropertyPage({ params }: Props) {
  const property = await getProperty(params.id);

  return (
    <div className="container mx-auto">
      <PropertyGallery images={property.images} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <h1 className="text-3xl font-bold">{property.name}</h1>
          <p>{property.description}</p>
          {/* Amenities, location, etc. */}
        </div>
        <div>
          {/* Client Component for interactive booking */}
          <BookingWidget
            propertyId={property.id}
            basePrice={property.base_price}
            currency={property.currency}
          />
        </div>
      </div>
    </div>
  );
}
```

### Component Library

```tsx
// Using shadcn/ui with Tailwind CSS

// Example: Booking Card component
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { formatCurrency, formatDate } from '@/lib/utils';

interface BookingCardProps {
  booking: Booking;
}

export function BookingCard({ booking }: BookingCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-start">
          <CardTitle className="text-lg">{booking.property.name}</CardTitle>
          <Badge variant={getStatusVariant(booking.status)}>
            {booking.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Check-in</span>
            <span>{formatDate(booking.check_in)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Check-out</span>
            <span>{formatDate(booking.check_out)}</span>
          </div>
          <div className="flex justify-between font-medium">
            <span>Total</span>
            <span>{formatCurrency(booking.total_price, booking.currency)}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

### Data Fetching

```tsx
// Server Components: Direct fetch
async function PropertyList() {
  const properties = await api.properties.list();
  return <PropertyGrid properties={properties} />;
}

// Client Components: TanStack Query
'use client';

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function BookingsList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['bookings'],
    queryFn: () => api.bookings.list(),
  });

  if (isLoading) return <BookingsListSkeleton />;
  if (error) return <ErrorDisplay error={error} />;

  return (
    <div className="space-y-4">
      {data.map((booking) => (
        <BookingCard key={booking.id} booking={booking} />
      ))}
    </div>
  );
}
```

### Authentication

```tsx
// lib/supabase/middleware.ts
import { createServerClient } from '@supabase/ssr';
import { NextResponse, type NextRequest } from 'next/server';

export async function updateSession(request: NextRequest) {
  const response = NextResponse.next();

  const supabase = createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        get: (name) => request.cookies.get(name)?.value,
        set: (name, value, options) => response.cookies.set(name, value, options),
        remove: (name, options) => response.cookies.set(name, '', options),
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();

  // Protect dashboard routes
  if (request.nextUrl.pathname.startsWith('/dashboard') && !user) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return response;
}
```

## Tech Stack Summary

| Component | Technology |
|-----------|------------|
| Framework | Next.js 14+ |
| UI Components | shadcn/ui (Radix + Tailwind) |
| Styling | Tailwind CSS |
| State Management | TanStack Query (server state) |
| Forms | React Hook Form + Zod |
| Auth | Supabase Auth + SSR |
| Icons | Lucide Icons |
| Charts | Recharts |
| Calendar | react-day-picker |
| Hosting | Vercel |

## References

- [Next.js Documentation](https://nextjs.org/docs)
- [shadcn/ui](https://ui.shadcn.com/)
- [TanStack Query](https://tanstack.com/query)
- [Supabase Auth with Next.js](https://supabase.com/docs/guides/auth/server-side/nextjs)
