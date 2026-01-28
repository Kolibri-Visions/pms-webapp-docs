/**
 * LuxeStay Property Detail Page - Demo Implementation
 *
 * This is a reference implementation showing how to use LuxeStay components
 * for the Property Detail page redesign.
 *
 * Phase 3 Features:
 * 1. Hero Section with Cover Image
 * 2. Times & Prices Card with Input fields
 * 3. Amenities Card with Gold Checkboxes
 */

"use client";

import { useState } from "react";
import { Card, Input, Button } from "@/app/components/luxe";
import { Clock, Sparkles, MapPin, Bed, Users, Home as HomeIcon } from "lucide-react";

interface PropertyDetailDemoProps {
  property: {
    id: string;
    name: string;
    internal_name?: string;
    property_type: string;
    max_guests: number;
    bedrooms: number;
    bathrooms: number;
    address_line1: string;
    city: string;
    postal_code: string;
    country: string;
    check_in_time: string;
    check_out_time: string;
    base_price: string;
    currency: string;
    cleaning_fee: string;
    security_deposit: string;
  };
  coverImageUrl?: string;
}

export default function PropertyDetailDemo({ property, coverImageUrl }: PropertyDetailDemoProps) {
  const [selectedAmenities, setSelectedAmenities] = useState<string[]>([
    "wifi",
    "pool",
    "kitchen",
    "parking",
    "air_conditioning",
    "tv",
    "washer",
    "heating",
  ]);

  const availableAmenities = [
    { id: "wifi", label: "WiFi", icon: "📶" },
    { id: "pool", label: "Pool", icon: "🏊" },
    { id: "kitchen", label: "Küche", icon: "🍳" },
    { id: "parking", label: "Parkplatz", icon: "🚗" },
    { id: "air_conditioning", label: "Klimaanlage", icon: "❄️" },
    { id: "tv", label: "TV", icon: "📺" },
    { id: "washer", label: "Waschmaschine", icon: "🧺" },
    { id: "heating", label: "Heizung", icon: "🔥" },
    { id: "gym", label: "Fitnessstudio", icon: "💪" },
    { id: "balcony", label: "Balkon", icon: "🌿" },
    { id: "garden", label: "Garten", icon: "🌳" },
    { id: "bbq", label: "Grill", icon: "🍖" },
  ];

  const toggleAmenity = (amenityId: string) => {
    setSelectedAmenities(prev =>
      prev.includes(amenityId)
        ? prev.filter(id => id !== amenityId)
        : [...prev, amenityId]
    );
  };

  return (
    <div className="space-y-6">
      {/* ========================================
          PHASE 3.1: HERO SECTION
          ======================================== */}
      <Card variant="elevated">
        <div className="grid grid-cols-1 lg:grid-cols-[400px_1fr] gap-6">
          {/* Cover Image */}
          <div className="relative bg-luxe-cream rounded-lg overflow-hidden aspect-video lg:aspect-[4/3]">
            {coverImageUrl ? (
              <img
                src={coverImageUrl}
                alt={property.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex items-center justify-center">
                <HomeIcon className="w-20 h-20 text-luxe-gold opacity-40" />
              </div>
            )}
            {/* Gold overlay badge */}
            <div className="absolute top-3 right-3 bg-luxe-gold text-white px-3 py-1 rounded-full text-xs font-semibold shadow-luxe-md">
              Premium
            </div>
          </div>

          {/* Property Summary */}
          <div className="flex flex-col gap-4">
            <div>
              <h1 className="text-3xl font-bold text-luxe-navy mb-2">
                {property.name}
              </h1>
              <p className="text-sm text-luxe-gray">
                {property.internal_name && `${property.internal_name} • `}
                <span className="capitalize">{property.property_type}</span>
              </p>
            </div>

            {/* Key Facts - 3 columns */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-luxe-cream-dark">
              <div>
                <div className="flex items-center gap-2 text-luxe-gold mb-1">
                  <Users className="w-4 h-4" />
                  <span className="text-xs font-semibold uppercase tracking-wide">Gäste</span>
                </div>
                <div className="text-2xl font-bold text-luxe-navy">
                  {property.max_guests}
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2 text-luxe-gold mb-1">
                  <Bed className="w-4 h-4" />
                  <span className="text-xs font-semibold uppercase tracking-wide">Zimmer</span>
                </div>
                <div className="text-2xl font-bold text-luxe-navy">
                  {property.bedrooms}
                </div>
              </div>
              <div>
                <div className="flex items-center gap-2 text-luxe-gold mb-1">
                  <MapPin className="w-4 h-4" />
                  <span className="text-xs font-semibold uppercase tracking-wide">Lage</span>
                </div>
                <div className="text-sm font-medium text-luxe-navy">
                  {property.city}
                </div>
              </div>
            </div>

            {/* Address */}
            <div className="bg-luxe-cream rounded-lg p-4">
              <div className="text-xs font-bold text-luxe-gold uppercase tracking-wider mb-2">
                Adresse
              </div>
              <div className="text-sm text-luxe-navy space-y-1">
                <div>{property.address_line1}</div>
                <div>{property.postal_code} {property.city}</div>
                <div>{property.country}</div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 pt-2">
              <Button variant="gold" size="sm">
                Bearbeiten
              </Button>
              <Button variant="secondary" size="sm">
                Medien
              </Button>
              <Button variant="ghost" size="sm">
                Preisplan
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* ========================================
          CONTENT GRID: 2 COLUMNS
          ======================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* ========================================
            PHASE 3.2: TIMES & PRICES CARD
            ======================================== */}
        <Card icon={Clock} title="Zeiten & Preise">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Check-in Zeit"
              type="time"
              defaultValue={property.check_in_time}
            />
            <Input
              label="Check-out Zeit"
              type="time"
              defaultValue={property.check_out_time}
            />
            <Input
              label="Währung"
              defaultValue={property.currency}
              disabled
            />
            <Input
              label="Basispreis / Nacht"
              type="number"
              defaultValue={property.base_price}
              hint={`in ${property.currency}`}
            />
            <Input
              label="Reinigungsgebühr"
              type="number"
              defaultValue={property.cleaning_fee}
            />
            <Input
              label="Kaution"
              type="number"
              defaultValue={property.security_deposit}
            />
          </div>

          {/* Save Button */}
          <div className="mt-6 flex justify-end">
            <Button variant="primary">
              Änderungen speichern
            </Button>
          </div>
        </Card>

        {/* Capacity Card (using same pattern) */}
        <Card icon={Bed} title="Kapazität">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Max. Gäste"
              type="number"
              defaultValue={String(property.max_guests)}
            />
            <Input
              label="Schlafzimmer"
              type="number"
              defaultValue={String(property.bedrooms)}
            />
            <Input
              label="Betten"
              type="number"
              defaultValue="4"
            />
            <Input
              label="Badezimmer"
              type="number"
              defaultValue={String(property.bathrooms)}
            />
          </div>

          {/* Save Button */}
          <div className="mt-6 flex justify-end">
            <Button variant="primary">
              Änderungen speichern
            </Button>
          </div>
        </Card>
      </div>

      {/* ========================================
          PHASE 3.3: AMENITIES CARD (FULL WIDTH)
          ======================================== */}
      <Card
        icon={Sparkles}
        title="Ausstattung"
        headerAction={
          <span className="text-sm font-medium text-luxe-gray">
            Ausgewählt: <span className="text-luxe-gold">{selectedAmenities.length}</span>
          </span>
        }
        variant="elevated"
      >
        {/* Gold-Checkboxed Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {availableAmenities.map((amenity) => {
            const isSelected = selectedAmenities.includes(amenity.id);
            return (
              <label
                key={amenity.id}
                className={`flex items-center gap-3 p-3 rounded-lg border-2 cursor-pointer transition-all duration-150 ${
                  isSelected
                    ? "border-luxe-gold bg-luxe-gold/5"
                    : "border-luxe-cream-dark hover:border-luxe-gray-light hover:bg-luxe-cream"
                }`}
              >
                <input
                  type="checkbox"
                  checked={isSelected}
                  onChange={() => toggleAmenity(amenity.id)}
                  className="w-5 h-5 text-luxe-gold rounded border-luxe-gray focus:ring-luxe-gold focus:ring-2"
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{amenity.icon}</span>
                    <span className={`text-sm font-medium truncate ${
                      isSelected ? "text-luxe-navy" : "text-luxe-gray"
                    }`}>
                      {amenity.label}
                    </span>
                  </div>
                </div>
              </label>
            );
          })}
        </div>

        {/* Save Button */}
        <div className="mt-6 flex justify-end gap-2">
          <Button variant="secondary">
            Abbrechen
          </Button>
          <Button variant="gold">
            {selectedAmenities.length} Ausstattungen speichern
          </Button>
        </div>
      </Card>

      {/* Additional Info Cards (same pattern) */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Buchungsregeln">
          <div className="grid grid-cols-2 gap-4">
            <Input
              label="Mindestaufenthalt"
              type="number"
              defaultValue="2"
              hint="Nächte"
            />
            <Input
              label="Maximalaufenthalt"
              type="number"
              defaultValue="30"
              hint="Nächte"
            />
            <Input
              label="Vorlaufzeit"
              type="number"
              defaultValue="1"
              hint="Tage"
            />
            <Input
              label="Buchungsfenster"
              type="number"
              defaultValue="365"
              hint="Tage"
            />
          </div>
        </Card>

        <Card title="Steuern">
          <div className="space-y-4">
            <Input
              label="Steuersatz"
              type="number"
              defaultValue="19.0"
              hint="%"
            />
            <label className="flex items-center gap-3 p-3 rounded-lg border-2 border-luxe-cream-dark hover:border-luxe-gold cursor-pointer transition-colors">
              <input
                type="checkbox"
                defaultChecked
                className="w-5 h-5 text-luxe-gold rounded border-luxe-gray focus:ring-luxe-gold focus:ring-2"
              />
              <span className="text-sm font-medium text-luxe-navy">
                Steuern im Preis enthalten
              </span>
            </label>
          </div>
        </Card>
      </div>
    </div>
  );
}
