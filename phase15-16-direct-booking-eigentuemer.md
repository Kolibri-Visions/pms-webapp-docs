# Phase 15-16: Direct Booking Flow & Eigentümer-Portal

**Version:** 1.0
**Erstellt:** 2025-12-22
**Projekt:** PMS-Webapp
**Basis:** Phase 10A (UI/UX), Phase 10B/10C (Visual Design), Phase 11-13 (Agentur-UX & Rollen), Phase 14 (Preismodell)

---

## Executive Summary

### Ziel

**Phase 15:** Gäste können direkt über die Agentur-Website buchen, OHNE dass PMS-Webapp die Zahlung abwickelt. Die Agentur nutzt externe Payment-Provider (Stripe, PayPal, Überweisung).

**Phase 16:** Externe Eigentümer (die ihre Objekte von der Agentur verwalten lassen) erhalten READ-ONLY Zugriff auf ihre Daten über ein reduziertes Portal.

### Scope

**Phase 15:**
- Booking Widget für Agentur-Website
- Schritt-für-Schritt Booking Flow (Datum → Gästedaten → Zusammenfassung → Bestätigung)
- Payment-Integration-Konzept (KEINE Zahlungsabwicklung durch PMS-Webapp)
- Buchungsbestätigung & E-Mail-Templates
- Kalender-Synchronisation (Direct Booking → Airbnb/Booking.com)

**Phase 16:**
- Eigentümer-Rolle (READ-ONLY)
- Eigentümer-Dashboard (nur eigene Objekte)
- Berichte für Eigentümer (Umsatz, Auslastung)
- RLS-Konzept (Row-Level Security)

### Leitplanken

- **B2B-Fokus:** Agenturen zahlen für Software, NICHT Gäste
- **KEINE Zahlungsabwicklung:** PMS-Webapp wickelt KEINE Gäste-Zahlungen ab
- **Sprache:** DEUTSCH (alle UI-Texte, E-Mails, Labels)
- **White-Label:** Token-basierte Farben, kein Produktname
- **UX-Prinzip:** "Less is more" - Menüpunkte verschwinden (nicht disabled)
- **Rollen:** Eigentümer = READ-ONLY, nur eigene Objekte
- **Konsistenz:** 100% konsistent mit Frozen Phases (10A-14)

---

## Phase 15: Direct Booking Flow (ohne Zahlungsabwicklung)

### 1. Booking Widget (für Agentur-Website)

#### 1.1 Konzept

**Ziel:**
Gäste können direkt über die Agentur-Website Ferienwohnungen buchen (zusätzlich zu Airbnb/Booking.com).

**Vorteile für Agentur:**
- 0% Provision (vs. 15-20% bei Airbnb/Booking.com)
- Direkter Kundenkontakt
- Kontrolle über Gästedaten
- Höhere Marge

**Integration:**
- Widget wird auf Agentur-Website eingebettet (iframe oder React Component)
- Widget ist White-Label (Agentur-Branding)
- Widget synchronisiert mit PMS-Webapp Kalender

#### 1.2 Komponenten

**Verfügbarkeitskalender:**
- Datum-Picker (Check-in / Check-out)
- Verfügbarkeit-Anzeige (grün = verfügbar, rot = gebucht)
- Mindestaufenthalt (z.B. 3 Nächte)
- Echtzeit-Synchronisation mit Airbnb/Booking.com

**Gästedaten-Formular:**
- Vorname, Nachname
- E-Mail
- Telefon (optional)
- Anzahl Gäste (Erwachsene / Kinder)
- Besondere Wünsche (Textarea, optional)

**Preis-Berechnung:**
- Nächte × Preis pro Nacht
- Zusätzliche Gebühren (Reinigungsgebühr, Kaution)
- Steuern (z.B. Kurtaxe)
- Gesamt-Preis (inkl. MwSt.)

**Buchungsbestätigung:**
- Zusammenfassung (Datum, Gäste, Preis)
- CTA: "Jetzt buchen" (ohne Zahlung)
- Hinweis: "Nach der Buchung erhalten Sie eine E-Mail mit Zahlungsanweisungen"

#### 1.3 Wireframe: Booking Widget (Desktop)

```
┌─────────────────────────────────────────────────────────────┐
│ [Agentur-Logo]                         [Ihre Buchung] 🛈     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────┐  ┌──────────────────┐   │
│  │ Objekt: Villa Meerblick        │  │ [Foto Objekt]    │   │
│  │ 🏠 4 Zimmer, 8 Gäste, 120m²   │  │                  │   │
│  │ 📍 Sylt, Deutschland           │  │                  │   │
│  └────────────────────────────────┘  └──────────────────┘   │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Schritt 1: Datum & Gäste auswählen                   │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │ Check-in               Check-out                      │   │
│  │ [📅 15.07.2025 ▼]     [📅 22.07.2025 ▼]             │   │
│  │                                                        │   │
│  │ Anzahl Gäste                                          │   │
│  │ Erwachsene: [2 ▼]   Kinder: [1 ▼]                   │   │
│  │                                                        │   │
│  │ ──────────────────────────────────────────────        │   │
│  │                                                        │   │
│  │ Preis-Übersicht:                                      │   │
│  │ 7 Nächte × €120/Nacht              €840,00          │   │
│  │ Reinigungsgebühr                    €80,00           │   │
│  │ ──────────────────────────────────────────────        │   │
│  │ Gesamt (inkl. MwSt.)                €920,00          │   │
│  │                                                        │   │
│  │              [Weiter zum nächsten Schritt]            │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  💳 Zahlung erfolgt NACH der Buchung über sicheren Link     │
│  ✅ Kostenlose Stornierung bis 14 Tage vor Check-in          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 1.4 Wireframe: Booking Widget (Mobile)

```
┌───────────────────────────────┐
│ [☰]  Ihre Buchung       [🛈]  │
├───────────────────────────────┤
│                               │
│ [Foto: Villa Meerblick]       │
│                               │
│ Villa Meerblick               │
│ 🏠 4 Zi., 8 Gäste, 120m²     │
│ 📍 Sylt                       │
│                               │
│ ┌───────────────────────────┐ │
│ │ Datum & Gäste             │ │
│ ├───────────────────────────┤ │
│ │                           │ │
│ │ Check-in                  │ │
│ │ [📅 15.07.2025 ▼]        │ │
│ │                           │ │
│ │ Check-out                 │ │
│ │ [📅 22.07.2025 ▼]        │ │
│ │                           │ │
│ │ Gäste                     │ │
│ │ Erwachsene [2▼] Kinder[1▼]│ │
│ │                           │ │
│ │ ───────────────────────   │ │
│ │                           │ │
│ │ 7 Nächte × €120   €840    │ │
│ │ Reinigung          €80    │ │
│ │ ───────────────────────   │ │
│ │ Gesamt            €920    │ │
│ │                           │ │
│ │ [Weiter]                  │ │
│ │                           │ │
│ └───────────────────────────┘ │
│                               │
│ 💳 Zahlung nach Buchung       │
│ ✅ Kostenlos stornierbar      │
│                               │
└───────────────────────────────┘
```

---

### 2. Booking Flow (Schritt-für-Schritt)

#### 2.1 Übersicht

**4-Schritte-Prozess:**
1. Datum & Gäste auswählen
2. Gästedaten eingeben
3. Zusammenfassung & Bestätigung
4. Buchung erstellt (Status: "Pending Payment")

**Wichtig:**
- KEINE Zahlungsabwicklung in Schritt 4
- E-Mail mit Zahlungsanweisungen wird nach Buchung verschickt
- Agentur markiert manuell als "Paid" nach Zahlungseingang

#### 2.2 Schritt 1: Datum & Gäste auswählen

**Wireframe (Desktop):**

```
┌─────────────────────────────────────────────────────────────┐
│ Schritt 1 von 4: Datum & Gäste                              │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ [●───────○─────○─────○] Fortschritt                         │
│                                                               │
│ Wann möchten Sie anreisen?                                   │
│                                                               │
│ Check-in                    Check-out                        │
│ [📅 Datum wählen ▼]        [📅 Datum wählen ▼]              │
│                                                               │
│ ┌─────────────────────────────────────────────────────┐     │
│ │        Juli 2025                 August 2025        │     │
│ │  Mo Di Mi Do Fr Sa So      Mo Di Mi Do Fr Sa So     │     │
│ │      1  2  3  4  5  6         1  2  3  4  5  6  7  │     │
│ │   7  8  9 10 11 12 13      8  9 10 11 12 13 14     │     │
│ │  14 [15 16 17 18 19 20]   15 16 17 18 19 20 21     │     │
│ │  21 [22] 23 24 25 26 27   [22] 23 24 25 26 27 28   │     │
│ │  28 29 30 31              29 30 31                  │     │
│ │                                                      │     │
│ │  ⬜ Verfügbar  ⬛ Gebucht  🟦 Ihre Auswahl          │     │
│ └─────────────────────────────────────────────────────┘     │
│                                                               │
│ Wie viele Gäste?                                             │
│                                                               │
│ Erwachsene  [➖  2  ➕]                                       │
│ Kinder      [➖  1  ➕]                                       │
│                                                               │
│ ──────────────────────────────────────────────────────       │
│                                                               │
│ Preis-Übersicht:                                             │
│ 7 Nächte × €120/Nacht              €840,00                  │
│ Reinigungsgebühr                    €80,00                   │
│ ──────────────────────────────────────────────────────       │
│ Gesamt (inkl. MwSt.)                €920,00                  │
│                                                               │
│                          [Abbrechen]  [Weiter]               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Validierung:**
- Check-out muss nach Check-in liegen
- Mindestaufenthalt beachten (z.B. 3 Nächte)
- Maximale Gästeanzahl prüfen (z.B. max. 8 Gäste)
- Verfügbarkeit prüfen (Datum nicht bereits gebucht)

**Fehler-States:**
```
┌────────────────────────────────────────────────┐
│ ⚠️ Fehler: Dieses Datum ist nicht verfügbar   │
│                                                │
│ Das ausgewählte Check-in-Datum ist bereits    │
│ gebucht. Bitte wählen Sie ein anderes Datum.  │
│                                                │
│                    [Datum ändern]              │
└────────────────────────────────────────────────┘
```

#### 2.3 Schritt 2: Gästedaten eingeben

**Wireframe (Desktop):**

```
┌─────────────────────────────────────────────────────────────┐
│ Schritt 2 von 4: Ihre Daten                                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ [○───●─────○─────○] Fortschritt                             │
│                                                               │
│ Bitte geben Sie Ihre Kontaktdaten ein:                       │
│                                                               │
│ Vorname *                                                    │
│ [_____________________________]                              │
│                                                               │
│ Nachname *                                                   │
│ [_____________________________]                              │
│                                                               │
│ E-Mail-Adresse *                                             │
│ [_____________________________]                              │
│ ℹ️ Hierhin senden wir die Buchungsbestätigung               │
│                                                               │
│ Telefon (optional)                                           │
│ [_____________________________]                              │
│                                                               │
│ Anzahl Gäste                                                 │
│ 2 Erwachsene, 1 Kind                                         │
│                                                               │
│ Besondere Wünsche (optional)                                 │
│ [_____________________________]                              │
│ [_____________________________]                              │
│ [_____________________________]                              │
│                                                               │
│ ☐ Ich akzeptiere die AGB und Datenschutzerklärung *         │
│                                                               │
│                          [Zurück]  [Weiter]                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Validierung:**
- Alle Pflichtfelder (*) müssen ausgefüllt sein
- E-Mail-Format prüfen (name@domain.de)
- Telefon optional, aber empfohlen
- AGB-Checkbox muss aktiviert sein

**Fehler-States:**
```
┌────────────────────────────────────────────────┐
│ ⚠️ Bitte füllen Sie alle Pflichtfelder aus    │
│                                                │
│ Folgende Felder fehlen noch:                  │
│ • E-Mail-Adresse                              │
│ • AGB-Zustimmung                              │
│                                                │
│                    [OK]                        │
└────────────────────────────────────────────────┘
```

#### 2.4 Schritt 3: Zusammenfassung & Bestätigung

**Wireframe (Desktop):**

```
┌─────────────────────────────────────────────────────────────┐
│ Schritt 3 von 4: Zusammenfassung                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ [○───○───●─────○] Fortschritt                               │
│                                                               │
│ Bitte prüfen Sie Ihre Buchung:                               │
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Objekt                                                 │   │
│ │ Villa Meerblick, Sylt                                 │   │
│ │ 4 Zimmer, 8 Gäste, 120m²                              │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Reisedaten                                             │   │
│ │ Check-in:  15.07.2025 (ab 15:00 Uhr)                  │   │
│ │ Check-out: 22.07.2025 (bis 10:00 Uhr)                 │   │
│ │ Aufenthalt: 7 Nächte                                   │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Gästedaten                                             │   │
│ │ Max Mustermann                                         │   │
│ │ max.mustermann@example.com                            │   │
│ │ +49 170 1234567                                        │   │
│ │ 2 Erwachsene, 1 Kind                                   │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ Preis-Details                                          │   │
│ │ 7 Nächte × €120/Nacht              €840,00           │   │
│ │ Reinigungsgebühr                    €80,00            │   │
│ │ ───────────────────────────────────────────            │   │
│ │ Gesamt (inkl. MwSt.)                €920,00           │   │
│ └───────────────────────────────────────────────────────┘   │
│                                                               │
│ 💳 Zahlung nach Buchung                                      │
│ Nach der Buchung erhalten Sie eine E-Mail mit                │
│ Zahlungsanweisungen. Die Buchung wird erst nach             │
│ Zahlungseingang bestätigt.                                   │
│                                                               │
│ ✅ Kostenlose Stornierung bis 14 Tage vor Check-in           │
│                                                               │
│                          [Zurück]  [Jetzt buchen]            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 2.5 Schritt 4: Buchung erstellt

**Wireframe (Desktop):**

```
┌─────────────────────────────────────────────────────────────┐
│ Buchung erfolgreich erstellt! ✅                             │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ [○───○───○───●] Fortschritt                                 │
│                                                               │
│        ┌─────────────────────────────────────┐               │
│        │           ✅ BUCHUNG ERSTELLT       │               │
│        │                                     │               │
│        │  Vielen Dank für Ihre Buchung!     │               │
│        │                                     │               │
│        │  Buchungsnummer: #DB-2025-00123    │               │
│        └─────────────────────────────────────┘               │
│                                                               │
│ Was passiert jetzt?                                          │
│                                                               │
│ 1️⃣ Sie erhalten eine Bestätigungs-E-Mail                   │
│    an: max.mustermann@example.com                           │
│                                                               │
│ 2️⃣ Die E-Mail enthält einen Zahlungslink                   │
│    (Stripe / PayPal / Banküberweisung)                      │
│                                                               │
│ 3️⃣ Nach Zahlungseingang erhalten Sie:                      │
│    • Buchungsbestätigung                                     │
│    • Check-in-Anweisungen                                    │
│    • Kontaktdaten des Gastgebers                             │
│                                                               │
│ ───────────────────────────────────────────────────          │
│                                                               │
│ 💡 Tipp: Prüfen Sie Ihren SPAM-Ordner, falls die E-Mail     │
│    nicht innerhalb von 5 Minuten ankommt.                    │
│                                                               │
│                  [Zurück zur Startseite]                     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**Backend-Aktion:**
1. Buchung in Datenbank erstellen (Status: "Pending Payment")
2. Kalender blockieren (für andere Gäste)
3. E-Mail an Gast senden (Buchungsbestätigung + Zahlungslink)
4. E-Mail an Agentur senden (Neue Buchung-Benachrichtigung)

---

### 3. Payment-Integration (Konzept)

#### 3.1 WICHTIG: Keine Zahlungsabwicklung durch PMS-Webapp

**Klarstellung:**
- ❌ PMS-Webapp wickelt KEINE Gäste-Zahlungen ab
- ❌ PMS-Webapp speichert KEINE Kreditkarten-Daten
- ❌ PMS-Webapp nimmt KEINE Provision auf Buchungen
- ✅ Agentur nutzt externe Payment-Provider
- ✅ PMS-Webapp verwaltet nur Buchungen (NICHT Zahlungen)

**Zahlungsfluss:**
```
Gast bucht → PMS-Webapp → E-Mail mit Zahlungslink
                              ↓
                        Payment-Provider
                        (Stripe/PayPal)
                              ↓
                        Agentur-Konto
                              ↓
                        Agentur markiert als "Paid"
                              ↓
                        PMS-Webapp (Status-Update)
```

#### 3.2 Option A: Stripe Payment Link

**Konzept:**
- Agentur hat eigenen Stripe-Account
- PMS-Webapp erstellt Stripe Payment Link (via API)
- Link wird per E-Mail an Gast geschickt
- Gast zahlt direkt an Agentur (nicht an PMS-Webapp)
- Stripe sendet Webhook an PMS-Webapp (Payment Success)
- PMS-Webapp aktualisiert Buchung (Status: "Paid")

**Vorteile:**
- Automatisiert (kein manueller Aufwand)
- Sicher (Stripe-PCI-Konformität)
- Schnell (sofortige Zahlung)

**Nachteile:**
- Stripe-Gebühren (1,4% + €0,25 pro Transaktion)
- Erfordert Stripe-Integration

**Implementation:**

```javascript
// Backend: Stripe Payment Link erstellen
async function createStripePaymentLink(booking) {
  const stripe = require('stripe')(process.env.AGENCY_STRIPE_SECRET_KEY);

  const paymentLink = await stripe.paymentLinks.create({
    line_items: [
      {
        price_data: {
          currency: 'eur',
          product_data: {
            name: `Buchung: ${booking.property_name}`,
            description: `Check-in: ${booking.check_in}, Check-out: ${booking.check_out}`,
          },
          unit_amount: booking.total_price * 100, // Cent
        },
        quantity: 1,
      },
    ],
    metadata: {
      booking_id: booking.id,
      agency_id: booking.agency_id,
    },
    after_completion: {
      type: 'redirect',
      redirect: {
        url: `https://agency-website.com/booking-confirmed?id=${booking.id}`,
      },
    },
  });

  return paymentLink.url; // https://buy.stripe.com/xxx
}

// Webhook: Payment Success
app.post('/webhooks/stripe', async (req, res) => {
  const event = req.body;

  if (event.type === 'payment_intent.succeeded') {
    const bookingId = event.data.object.metadata.booking_id;

    // Buchung als "Paid" markieren
    await updateBookingStatus(bookingId, 'paid');

    // Bestätigungs-E-Mail senden
    await sendBookingConfirmationEmail(bookingId);
  }

  res.status(200).send('OK');
});
```

#### 3.3 Option B: PayPal Payment Request

**Konzept:**
- Agentur hat eigenen PayPal-Account
- PMS-Webapp erstellt PayPal Invoice (via API)
- Link wird per E-Mail an Gast geschickt
- Gast zahlt über PayPal
- PayPal sendet Webhook an PMS-Webapp (Payment Success)
- PMS-Webapp aktualisiert Buchung (Status: "Paid")

**Vorteile:**
- Weit verbreitet (viele Nutzer haben PayPal)
- Käuferschutz
- Mehrere Zahlungsmethoden (Kreditkarte, Lastschrift, PayPal-Balance)

**Nachteile:**
- PayPal-Gebühren (1,9% + €0,35 pro Transaktion)
- Weniger modern als Stripe

#### 3.4 Option C: Manuelle Überweisung

**Konzept:**
- Agentur sendet Bankdaten per E-Mail
- Gast überweist manuell
- Agentur markiert Buchung manuell als "Paid" (nach Zahlungseingang)
- PMS-Webapp aktualisiert Status

**Vorteile:**
- Keine Payment-Provider-Gebühren
- Volle Kontrolle
- Ideal für große Buchungen

**Nachteile:**
- Langsam (1-3 Werktage)
- Manueller Aufwand (Agentur muss prüfen)
- Risiko: Gast bucht, zahlt aber nicht

**E-Mail-Template (siehe 4.1):**
```
Zahlungsanweisungen:

Bitte überweisen Sie €920,00 auf folgendes Konto:

Kontoinhaber: [Agentur-Name]
IBAN: DE89 3704 0044 0532 0130 00
BIC: COBADEFFXXX
Verwendungszweck: Buchung #DB-2025-00123

Zahlungsziel: 7 Tage (bis 29.12.2025)
```

#### 3.5 Status-Update-Flow

**Status-Modell:**
```
Pending Payment → Paid → Confirmed → Completed
                   ↓
                Cancelled
```

**Status-Beschreibung:**
- **Pending Payment:** Buchung erstellt, Zahlung ausstehend
- **Paid:** Zahlung eingegangen
- **Confirmed:** Buchung bestätigt (nach manueller Prüfung)
- **Completed:** Check-out abgeschlossen
- **Cancelled:** Storniert (vor oder nach Zahlung)

**Manuelles Status-Update (Agentur-Admin):**

```
┌─────────────────────────────────────────────┐
│ Buchung #DB-2025-00123                      │
├─────────────────────────────────────────────┤
│                                             │
│ Status: Pending Payment ⏳                  │
│                                             │
│ [Als "Paid" markieren]                      │
│                                             │
│ ℹ️ Markieren Sie die Buchung als "Paid",   │
│   sobald die Zahlung auf Ihrem Konto       │
│   eingegangen ist.                          │
│                                             │
└─────────────────────────────────────────────┘
```

---

### 4. Buchungsbestätigung & E-Mails

#### 4.1 Template: Gast-Bestätigung (nach Buchung)

**Betreff:** Ihre Buchung bei [Agentur-Name] - Buchungsnummer #DB-2025-00123

```
Hallo Max Mustermann,

vielen Dank für Ihre Buchung!

──────────────────────────────────────────────────

BUCHUNGSNUMMER: #DB-2025-00123
STATUS: Zahlung ausstehend ⏳

──────────────────────────────────────────────────

IHRE UNTERKUNFT:
Villa Meerblick
4 Zimmer, 8 Gäste, 120m²
Strandweg 12, 25980 Sylt

REISEDATEN:
Check-in:  15.07.2025 (ab 15:00 Uhr)
Check-out: 22.07.2025 (bis 10:00 Uhr)
Aufenthalt: 7 Nächte

GÄSTE:
2 Erwachsene, 1 Kind

──────────────────────────────────────────────────

PREIS-DETAILS:
7 Nächte × €120/Nacht              €840,00
Reinigungsgebühr                    €80,00
───────────────────────────────────────────────
Gesamt (inkl. MwSt.)                €920,00

──────────────────────────────────────────────────

ZAHLUNG:

Bitte wählen Sie eine Zahlungsmethode:

Option 1: Online bezahlen (Stripe)
[Jetzt mit Kreditkarte bezahlen]
→ https://buy.stripe.com/xxx

Option 2: PayPal
[Mit PayPal bezahlen]
→ https://paypal.me/xxx

Option 3: Banküberweisung
Kontoinhaber: [Agentur-Name]
IBAN: DE89 3704 0044 0532 0130 00
BIC: COBADEFFXXX
Verwendungszweck: Buchung #DB-2025-00123

Zahlungsziel: 7 Tage (bis 29.12.2025)

──────────────────────────────────────────────────

WAS PASSIERT NACH DER ZAHLUNG?

1. Sie erhalten eine Zahlungsbestätigung
2. Wir senden Ihnen die Check-in-Anweisungen
3. Sie erhalten die Kontaktdaten des Gastgebers

──────────────────────────────────────────────────

STORNIERUNG:
Kostenlose Stornierung bis 14 Tage vor Check-in.
Bei späterer Stornierung behalten wir 50% ein.

──────────────────────────────────────────────────

FRAGEN?
Kontaktieren Sie uns:
E-Mail: info@agentur-name.de
Telefon: +49 4651 1234567

──────────────────────────────────────────────────

Wir freuen uns auf Ihren Besuch!

Ihr Team von [Agentur-Name]

──────────────────────────────────────────────────

[Logo: Agentur-Name]
```

#### 4.2 Template: Agentur-Benachrichtigung (neue Buchung)

**Betreff:** Neue Direct Booking: Villa Meerblick (15.07.2025 - 22.07.2025)

```
Neue Direct Booking eingegangen! 🎉

──────────────────────────────────────────────────

BUCHUNGSNUMMER: #DB-2025-00123
STATUS: Pending Payment ⏳
ERSTELLT: 22.12.2025, 14:32 Uhr

──────────────────────────────────────────────────

OBJEKT:
Villa Meerblick, Sylt

REISEDATEN:
Check-in:  15.07.2025
Check-out: 22.07.2025
Aufenthalt: 7 Nächte

GAST:
Max Mustermann
max.mustermann@example.com
+49 170 1234567
2 Erwachsene, 1 Kind

──────────────────────────────────────────────────

PREIS:
Gesamt: €920,00 (inkl. MwSt.)

──────────────────────────────────────────────────

NÄCHSTE SCHRITTE:

1. Warten Sie auf Zahlungseingang
2. Markieren Sie die Buchung als "Paid"
3. Senden Sie Check-in-Anweisungen

[Buchung im PMS-Webapp öffnen]
→ https://pms-webapp.com/bookings/DB-2025-00123

──────────────────────────────────────────────────

Diese E-Mail wurde automatisch von PMS-Webapp generiert.
```

#### 4.3 Template: Zahlungs-Reminder (nach 3 Tagen)

**Betreff:** Erinnerung: Zahlung ausstehend - Buchung #DB-2025-00123

```
Hallo Max Mustermann,

Ihre Buchung wartet noch auf die Zahlung.

──────────────────────────────────────────────────

BUCHUNGSNUMMER: #DB-2025-00123
ZAHLUNGSZIEL: 29.12.2025 (noch 4 Tage)

──────────────────────────────────────────────────

Bitte bezahlen Sie €920,00, um Ihre Buchung zu bestätigen.

ZAHLUNGSMETHODEN:

Option 1: Online bezahlen (Stripe)
[Jetzt mit Kreditkarte bezahlen]
→ https://buy.stripe.com/xxx

Option 2: PayPal
[Mit PayPal bezahlen]
→ https://paypal.me/xxx

Option 3: Banküberweisung
IBAN: DE89 3704 0044 0532 0130 00
Verwendungszweck: Buchung #DB-2025-00123

──────────────────────────────────────────────────

⚠️ WICHTIG:
Wenn die Zahlung nicht bis zum 29.12.2025 eingeht,
wird Ihre Buchung automatisch storniert.

──────────────────────────────────────────────────

FRAGEN?
Kontaktieren Sie uns:
E-Mail: info@agentur-name.de
Telefon: +49 4651 1234567

──────────────────────────────────────────────────

Ihr Team von [Agentur-Name]
```

#### 4.4 Template: Zahlungsbestätigung (nach Zahlung)

**Betreff:** Zahlung bestätigt - Ihre Buchung ist reserviert! ✅

```
Hallo Max Mustermann,

Ihre Zahlung ist eingegangen! 🎉

──────────────────────────────────────────────────

BUCHUNGSNUMMER: #DB-2025-00123
STATUS: Bezahlt ✅

──────────────────────────────────────────────────

IHRE UNTERKUNFT:
Villa Meerblick, Sylt

REISEDATEN:
Check-in:  15.07.2025 (ab 15:00 Uhr)
Check-out: 22.07.2025 (bis 10:00 Uhr)

──────────────────────────────────────────────────

CHECK-IN-ANWEISUNGEN:

Adresse:
Strandweg 12
25980 Sylt

Anreise:
Ab 15:00 Uhr

Schlüsselübergabe:
Der Schlüssel befindet sich in einem Schlüsselsafe
neben der Eingangstür. Code: 1234

Kontakt vor Ort:
Frau Schmidt
+49 4651 9876543

──────────────────────────────────────────────────

WAS SIE MITBRINGEN SOLLTEN:
• Personalausweis / Reisepass
• Diese Buchungsbestätigung
• Gute Laune! 😊

──────────────────────────────────────────────────

HAUSREGELN:
• Keine Haustiere
• Nichtraucher-Unterkunft
• Nachtruhe ab 22:00 Uhr

──────────────────────────────────────────────────

Wir freuen uns auf Ihren Besuch!

Ihr Team von [Agentur-Name]

──────────────────────────────────────────────────

[Rechnung als PDF anhängen]
```

---

### 5. Kalender-Synchronisation

#### 5.1 Konzept

**Ziel:**
- Direct Bookings blockieren Kalender automatisch
- Airbnb/Booking.com sieht blockierte Daten (keine Doppelbuchungen)
- Airbnb/Booking.com-Buchungen blockieren Direct Booking-Kalender

**Synchronisations-Richtung:**
```
Direct Booking → PMS-Webapp Kalender → Airbnb/Booking.com (iCal Export)
Airbnb/Booking.com → PMS-Webapp Kalender (iCal Import)
```

#### 5.2 Direct Booking → Kalender blockieren

**Ablauf:**
1. Gast bucht direkt über Widget
2. Buchung wird in Datenbank erstellt (Status: "Pending Payment")
3. Kalender wird sofort blockiert (für andere Gäste)
4. iCal-Feed wird aktualisiert (für Airbnb/Booking.com)

**WICHTIG:**
- Kalender wird SOFORT blockiert (nicht erst nach Zahlung)
- Verhindert Doppelbuchungen
- Wenn Zahlung nicht eingeht → Buchung wird storniert → Kalender freigegeben

**Code-Beispiel:**

```javascript
// Buchung erstellen
async function createDirectBooking(bookingData) {
  // 1. Verfügbarkeit prüfen
  const isAvailable = await checkAvailability(
    bookingData.property_id,
    bookingData.check_in,
    bookingData.check_out
  );

  if (!isAvailable) {
    throw new Error('Datum nicht verfügbar');
  }

  // 2. Buchung in Datenbank erstellen
  const booking = await db.bookings.create({
    property_id: bookingData.property_id,
    check_in: bookingData.check_in,
    check_out: bookingData.check_out,
    guest_name: bookingData.guest_name,
    guest_email: bookingData.guest_email,
    status: 'pending_payment',
    source: 'direct',
    total_price: bookingData.total_price,
  });

  // 3. Kalender blockieren
  await blockCalendar(
    bookingData.property_id,
    bookingData.check_in,
    bookingData.check_out,
    booking.id
  );

  // 4. iCal-Feed aktualisieren
  await updateICalFeed(bookingData.property_id);

  // 5. E-Mail senden
  await sendBookingConfirmationEmail(booking);

  return booking;
}
```

#### 5.3 Synchronisation mit Airbnb/Booking.com (iCal)

**iCal Export (PMS-Webapp → Airbnb/Booking.com):**

```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//PMS-Webapp//Direct Bookings//EN
CALNAME:Villa Meerblick - Direct Bookings

BEGIN:VEVENT
UID:DB-2025-00123@pms-webapp.com
DTSTART:20250715
DTEND:20250722
SUMMARY:Direct Booking (Max Mustermann)
DESCRIPTION:Buchung #DB-2025-00123, Status: Pending Payment
STATUS:CONFIRMED
END:VEVENT

END:VCALENDAR
```

**Airbnb/Booking.com importiert iCal:**
- Airbnb/Booking.com importiert iCal-URL alle 15-30 Minuten
- Blockierte Daten werden automatisch ausgeblendet
- Verhindert Doppelbuchungen

**iCal Import (Airbnb/Booking.com → PMS-Webapp):**
- PMS-Webapp importiert iCal-URL von Airbnb/Booking.com alle 15 Minuten
- Airbnb/Booking.com-Buchungen blockieren Direct Booking-Kalender
- Konflikt-Erkennung (siehe 5.4)

#### 5.4 Konflikt-Erkennung & Handling

**Szenario: Gast bucht direkt, aber Datum ist bereits auf Airbnb gebucht**

**Problem:**
- Gast bucht direkt um 14:00 Uhr
- Airbnb-Buchung kommt um 14:05 Uhr rein
- iCal-Import-Intervall: 15 Minuten
- → Doppelbuchung!

**Lösung:**

```javascript
// Konflikt-Prüfung vor jeder Buchung
async function checkAvailability(propertyId, checkIn, checkOut) {
  // 1. Prüfen: Direct Bookings in Datenbank
  const existingBookings = await db.bookings.findMany({
    where: {
      property_id: propertyId,
      OR: [
        { check_in: { gte: checkIn, lt: checkOut } },
        { check_out: { gt: checkIn, lte: checkOut } },
        { check_in: { lte: checkIn }, check_out: { gte: checkOut } },
      ],
      status: { in: ['pending_payment', 'paid', 'confirmed'] },
    },
  });

  if (existingBookings.length > 0) {
    return false; // Nicht verfügbar
  }

  // 2. Prüfen: Airbnb/Booking.com iCal (gecached in DB)
  const externalBookings = await db.external_bookings.findMany({
    where: {
      property_id: propertyId,
      OR: [
        { check_in: { gte: checkIn, lt: checkOut } },
        { check_out: { gt: checkIn, lte: checkOut } },
        { check_in: { lte: checkIn }, check_out: { gte: checkOut } },
      ],
    },
  });

  if (externalBookings.length > 0) {
    return false; // Nicht verfügbar
  }

  return true; // Verfügbar
}
```

**Konflikt-Benachrichtigung (Agentur):**

```
⚠️ WARNUNG: Mögliche Doppelbuchung erkannt!

Objekt: Villa Meerblick
Datum: 15.07.2025 - 22.07.2025

Buchung 1: #DB-2025-00123 (Direct Booking, Pending Payment)
Buchung 2: Airbnb-Import (HM1234567890)

Bitte prüfen Sie die Buchungen manuell und stornieren Sie
eine der beiden Buchungen.

[Buchungen vergleichen]
```

#### 5.5 Synchronisations-Intervall

**iCal Import (Airbnb/Booking.com → PMS-Webapp):**
- Intervall: 15 Minuten
- Cron Job: `*/15 * * * *`
- Verhindert API-Rate-Limits

**iCal Export (PMS-Webapp → Airbnb/Booking.com):**
- Intervall: Sofort nach Direct Booking
- Airbnb/Booking.com importiert alle 15-30 Minuten
- Verzögerung: Bis zu 30 Minuten (akzeptabel)

**WICHTIG:**
- Echtzeit-Synchronisation NICHT möglich (Airbnb/Booking.com unterstützen nur iCal, kein Webhook)
- Konflikt-Risiko: 15-30 Minuten Fenster
- Lösung: Verfügbarkeits-Prüfung vor jeder Buchung (inkl. gecachte iCal-Daten)

---

### 6. Backend-Logik (Konzept)

#### 6.1 API Endpoints

**POST /api/direct-bookings/check-availability**
- Prüft Verfügbarkeit für Datum
- Input: `property_id`, `check_in`, `check_out`
- Output: `{ available: true/false, reason: "..." }`

**POST /api/direct-bookings/create**
- Erstellt neue Direct Booking
- Input: `property_id`, `check_in`, `check_out`, `guest_data`, `total_price`
- Output: `{ booking_id, status, payment_link }`

**GET /api/direct-bookings/:id**
- Ruft Buchungs-Details ab
- Output: `{ booking_id, property, guest, status, total_price, ... }`

**PATCH /api/direct-bookings/:id/status**
- Aktualisiert Buchungs-Status (nur Agentur-Admin)
- Input: `{ status: "paid" | "confirmed" | "cancelled" }`
- Output: `{ booking_id, status }`

**POST /api/direct-bookings/:id/send-reminder**
- Sendet Zahlungs-Reminder an Gast (manuell oder automatisch)
- Output: `{ email_sent: true }`

**GET /api/properties/:id/availability**
- Ruft Kalender-Daten ab (für Widget)
- Output: `{ available_dates: [...], booked_dates: [...] }`

#### 6.2 Datenbank-Schema

**Tabelle: direct_bookings**

```sql
CREATE TABLE direct_bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID NOT NULL REFERENCES agencies(id),
  property_id UUID NOT NULL REFERENCES properties(id),

  -- Gästedaten
  guest_name VARCHAR(255) NOT NULL,
  guest_email VARCHAR(255) NOT NULL,
  guest_phone VARCHAR(50),
  guest_count_adults INT NOT NULL DEFAULT 1,
  guest_count_children INT NOT NULL DEFAULT 0,
  special_requests TEXT,

  -- Reisedaten
  check_in DATE NOT NULL,
  check_out DATE NOT NULL,
  nights INT GENERATED ALWAYS AS (check_out - check_in) STORED,

  -- Preis
  price_per_night DECIMAL(10, 2) NOT NULL,
  cleaning_fee DECIMAL(10, 2) DEFAULT 0,
  total_price DECIMAL(10, 2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'EUR',

  -- Status
  status VARCHAR(50) NOT NULL DEFAULT 'pending_payment',
    -- pending_payment, paid, confirmed, completed, cancelled
  payment_method VARCHAR(50), -- stripe, paypal, bank_transfer
  payment_link TEXT, -- Stripe/PayPal Link
  paid_at TIMESTAMP,

  -- Metadaten
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  -- Constraints
  CONSTRAINT check_dates CHECK (check_out > check_in),
  CONSTRAINT check_guests CHECK (guest_count_adults > 0)
);

-- Indizes
CREATE INDEX idx_direct_bookings_property ON direct_bookings(property_id);
CREATE INDEX idx_direct_bookings_agency ON direct_bookings(agency_id);
CREATE INDEX idx_direct_bookings_status ON direct_bookings(status);
CREATE INDEX idx_direct_bookings_dates ON direct_bookings(check_in, check_out);
```

**Tabelle: external_bookings (iCal Import)**

```sql
CREATE TABLE external_bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID NOT NULL REFERENCES agencies(id),
  property_id UUID NOT NULL REFERENCES properties(id),

  -- iCal-Daten
  ical_uid VARCHAR(255) NOT NULL UNIQUE,
  source VARCHAR(50) NOT NULL, -- airbnb, booking_com, vrbo, etc.

  -- Reisedaten
  check_in DATE NOT NULL,
  check_out DATE NOT NULL,
  summary TEXT, -- z.B. "Airbnb Booking (John Doe)"

  -- Metadaten
  imported_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Indizes
CREATE INDEX idx_external_bookings_property ON external_bookings(property_id);
CREATE INDEX idx_external_bookings_dates ON external_bookings(check_in, check_out);
CREATE UNIQUE INDEX idx_external_bookings_ical_uid ON external_bookings(ical_uid);
```

#### 6.3 Validierung

**Verfügbarkeit:**
- Check-out > Check-in
- Mindestaufenthalt beachten (z.B. 3 Nächte)
- Maximale Gästeanzahl prüfen
- Keine Überschneidung mit existierenden Buchungen

**Gästedaten:**
- E-Mail-Format validieren
- Telefon optional, aber empfohlen
- Mindestens 1 Erwachsener

**Preis:**
- Preis-Berechnung serverseitig (nicht vom Frontend übernehmen)
- Verhindert Manipulation

```javascript
// Preis-Berechnung (Backend)
function calculatePrice(property, checkIn, checkOut, guests) {
  const nights = (new Date(checkOut) - new Date(checkIn)) / (1000 * 60 * 60 * 24);
  const pricePerNight = property.price_per_night;
  const cleaningFee = property.cleaning_fee || 0;

  const subtotal = nights * pricePerNight;
  const total = subtotal + cleaningFee;

  return {
    nights,
    price_per_night: pricePerNight,
    subtotal,
    cleaning_fee: cleaningFee,
    total,
  };
}
```

---

## Phase 16: Eigentümer-Portal (Read-Only)

### 1. Eigentümer-Rolle

#### 1.1 Beschreibung

**Wer ist ein Eigentümer?**
- Besitzer von Ferienwohnungen, die von der Agentur verwaltet werden
- Externe Stakeholder (NICHT Teil des Agentur-Teams)
- Möchten ihre Objekte und Buchungen einsehen

**Zugriff:**
- READ-ONLY (keine Bearbeitungs-Rechte)
- Nur eigene Objekte sichtbar (RLS auf Datenbank-Ebene)
- Keine Möglichkeit, andere Objekte zu sehen

**Permissions:**

| Feature | Eigentümer |
|---------|------------|
| **Dashboard** |
| Dashboard (nur eigene Daten) | ✅ READ |
| **Objekte** |
| Objekte ansehen | ✅ READ (nur eigene) |
| Objekte erstellen | ❌ |
| Objekte bearbeiten | ❌ |
| Objekte löschen | ❌ |
| **Buchungen** |
| Buchungen ansehen | ✅ READ (nur eigene) |
| Buchungen erstellen | ❌ |
| Buchungen bearbeiten | ❌ |
| Buchungen stornieren | ❌ |
| **Berichte** |
| Berichte ansehen | ✅ READ (nur eigene) |
| Berichte exportieren | ✅ (CSV, PDF) |
| **Team** |
| Team ansehen | ❌ |
| **Einstellungen** |
| Eigenes Profil bearbeiten | ✅ |
| Agentur-Einstellungen | ❌ |

#### 1.2 RLS-Konzept (Row-Level Security)

**Konzept:**
- Eigentümer sieht NUR Objekte, bei denen `owner_id = auth.uid()`
- Keine Objekte anderer Eigentümer sichtbar
- Isolation auf Datenbank-Ebene (Supabase RLS Policies)

**RLS Policy: Eigentümer-Isolation (properties)**

```sql
-- Policy: owner_read_own_properties
CREATE POLICY owner_read_own_properties
ON properties
FOR SELECT
USING (
  (auth.jwt() ->> 'role' = 'owner' AND owner_id = auth.uid())
  OR
  (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff')
   AND agency_id = (auth.jwt() ->> 'agency_id')::uuid)
);
```

**Erklärung:**
- Eigentümer sieht nur Objekte, bei denen `owner_id = auth.uid()`
- Admin/Manager/Staff sehen ALLE Objekte ihrer Agentur
- Keine Frontend-Logik nötig (Datenbank macht das automatisch)

**RLS Policy: Eigentümer-Isolation (bookings)**

```sql
-- Policy: owner_read_own_bookings
CREATE POLICY owner_read_own_bookings
ON bookings
FOR SELECT
USING (
  (auth.jwt() ->> 'role' = 'owner'
   AND property_id IN (
     SELECT id FROM properties WHERE owner_id = auth.uid()
   ))
  OR
  (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff', 'accountant')
   AND agency_id = (auth.jwt() ->> 'agency_id')::uuid)
);
```

**Erklärung:**
- Eigentümer sieht nur Buchungen von Objekten, bei denen `owner_id = auth.uid()`
- Admin/Manager/Staff/Buchhalter sehen ALLE Buchungen ihrer Agentur

---

### 2. Eigentümer-Dashboard

#### 2.1 Konzept

**Ziel:**
- Eigentümer sieht auf einen Blick:
  - Anzahl eigener Objekte
  - Aktuelle Buchungen (nächste 30 Tage)
  - Umsatz (Monat, Jahr)
  - Auslastung (Occupancy Rate)

**Beschränkung:**
- NUR eigene Daten (keine Agentur-Daten)
- KEINE Bearbeitungs-Funktionen
- KEINE Team-Daten
- KEINE Finanzdaten der Agentur

#### 2.2 Wireframe: Eigentümer-Dashboard (Desktop)

```
┌─────────────────────────────────────────────────────────────┐
│ [Logo]  Dashboard                      [Profil ▼] [Abmelden]│
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Willkommen, Herr Müller                                      │
│                                                               │
│ ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│ │ Meine        │  │ Aktuelle     │  │ Umsatz       │        │
│ │ Objekte      │  │ Buchungen    │  │ (Monat)      │        │
│ │              │  │              │  │              │        │
│ │    3         │  │    7         │  │  €4.200      │        │
│ │              │  │              │  │              │        │
│ │ [Details]    │  │ [Details]    │  │ [Details]    │        │
│ └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Anstehende Check-ins                                   │  │
│ ├────────────────────────────────────────────────────────┤  │
│ │                                                         │  │
│ │ 23.12.2025  Villa Meerblick      Familie Schmidt       │  │
│ │ 24.12.2025  Ferienwohnung Strand  Herr Meyer          │  │
│ │ 26.12.2025  Penthouse City        Frau Becker         │  │
│ │                                                         │  │
│ │                                   [Alle Buchungen]     │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Auslastung (Letzten 6 Monate)                          │  │
│ ├────────────────────────────────────────────────────────┤  │
│ │                                                         │  │
│ │     █                                                   │  │
│ │     █      █                                            │  │
│ │     █      █      █                                     │  │
│ │     █      █      █      █      █      █               │  │
│ │  ───┴──────┴──────┴──────┴──────┴──────┴───            │  │
│ │   Jul   Aug   Sep   Oct   Nov   Dec                    │  │
│ │                                                         │  │
│ │   Durchschnitt: 72%                                     │  │
│ │                                                         │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 2.3 Wireframe: Eigentümer-Dashboard (Mobile)

```
┌───────────────────────────────┐
│ [☰]  Dashboard      [Profil]  │
├───────────────────────────────┤
│                               │
│ Willkommen, Herr Müller       │
│                               │
│ ┌───────────────────────────┐ │
│ │ Meine Objekte             │ │
│ │          3                │ │
│ │      [Details]            │ │
│ └───────────────────────────┘ │
│                               │
│ ┌───────────────────────────┐ │
│ │ Aktuelle Buchungen        │ │
│ │          7                │ │
│ │      [Details]            │ │
│ └───────────────────────────┘ │
│                               │
│ ┌───────────────────────────┐ │
│ │ Umsatz (Monat)            │ │
│ │       €4.200              │ │
│ │      [Details]            │ │
│ └───────────────────────────┘ │
│                               │
│ ┌───────────────────────────┐ │
│ │ Anstehende Check-ins      │ │
│ ├───────────────────────────┤ │
│ │ 23.12  Villa Meerblick    │ │
│ │ 24.12  Ferienwohnung...   │ │
│ │ 26.12  Penthouse City     │ │
│ │                           │ │
│ │      [Alle Buchungen]     │ │
│ └───────────────────────────┘ │
│                               │
│ ┌───────────────────────────┐ │
│ │ Auslastung (6 Monate)     │ │
│ ├───────────────────────────┤ │
│ │     █                     │ │
│ │     █  █  █  █  █  █      │ │
│ │  ───┴──┴──┴──┴──┴──┴───   │ │
│ │   Jul Aug Sep Oct Nov Dec │ │
│ │                           │ │
│ │   Ø 72%                   │ │
│ └───────────────────────────┘ │
│                               │
└───────────────────────────────┘
```

---

### 3. Eigentümer-Menü-Struktur

#### 3.1 Menü-Items (Desktop)

**Sidebar:**
```
┌──────────────────────┐
│ [Logo]               │
│                      │
│ 📊 Dashboard         │
│ 🏠 Meine Objekte     │
│ 📅 Buchungen         │
│ 📈 Berichte          │
│ 👤 Profil            │
│                      │
│ ──────────────────   │
│                      │
│ [Abmelden]           │
└──────────────────────┘
```

**WICHTIG:**
- KEINE anderen Menüpunkte (Team, Einstellungen, Channels, etc.)
- "Less is more" - nur relevante Features zeigen
- Menüpunkte verschwinden (nicht disabled)

#### 3.2 Menü-Items (Mobile)

**Hamburger-Menü:**
```
┌───────────────────────────┐
│ [☰]                       │
├───────────────────────────┤
│                           │
│ 📊 Dashboard              │
│ 🏠 Meine Objekte          │
│ 📅 Buchungen              │
│ 📈 Berichte               │
│ 👤 Profil                 │
│                           │
│ ───────────────────       │
│                           │
│ [Abmelden]                │
│                           │
└───────────────────────────┘
```

#### 3.3 Menü-Prinzip: Verschwinden, nicht disabled

**RICHTIG (Eigentümer):**
```jsx
{role === 'owner' && (
  <>
    <MenuItem href="/dashboard">Dashboard</MenuItem>
    <MenuItem href="/properties">Meine Objekte</MenuItem>
    <MenuItem href="/bookings">Buchungen</MenuItem>
    <MenuItem href="/reports">Berichte</MenuItem>
    <MenuItem href="/profile">Profil</MenuItem>
  </>
)}
```

**FALSCH:**
```jsx
<MenuItem href="/team" disabled={role === 'owner'}>Team</MenuItem>
// User sieht "Team" (grayed-out), kann aber nicht klicken
```

---

### 4. Objekt-Liste (READ-ONLY)

#### 4.1 Wireframe: Objekt-Liste (Desktop)

```
┌─────────────────────────────────────────────────────────────┐
│ Meine Objekte (3)                                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ [Foto]  Villa Meerblick                        [▼]     │  │
│ │         4 Zimmer, 8 Gäste, 120m²                       │  │
│ │         📍 Strandweg 12, 25980 Sylt                    │  │
│ │                                                         │  │
│ │         Status: Aktiv 🟢                                │  │
│ │         Nächste Buchung: 23.12.2025                     │  │
│ │                                                         │  │
│ │         [Details ansehen]                               │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ [Foto]  Ferienwohnung Strand                   [▼]     │  │
│ │         2 Zimmer, 4 Gäste, 60m²                        │  │
│ │         📍 Dünenweg 5, 25980 Sylt                      │  │
│ │                                                         │  │
│ │         Status: Aktiv 🟢                                │  │
│ │         Nächste Buchung: 24.12.2025                     │  │
│ │                                                         │  │
│ │         [Details ansehen]                               │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ [Foto]  Penthouse City                         [▼]     │  │
│ │         3 Zimmer, 6 Gäste, 90m²                        │  │
│ │         📍 Hauptstraße 1, 20095 Hamburg                │  │
│ │                                                         │  │
│ │         Status: Aktiv 🟢                                │  │
│ │         Nächste Buchung: 26.12.2025                     │  │
│ │                                                         │  │
│ │         [Details ansehen]                               │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 4.2 Wireframe: Objekt-Details (READ-ONLY)

```
┌─────────────────────────────────────────────────────────────┐
│ [← Zurück]  Villa Meerblick                                 │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ [Foto 1]  [Foto 2]  [Foto 3]  [Foto 4]  [Foto 5]      │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ Villa Meerblick                                              │
│ 4 Zimmer, 8 Gäste, 120m²                                    │
│ 📍 Strandweg 12, 25980 Sylt                                 │
│                                                               │
│ Status: Aktiv 🟢                                             │
│ Nächste Buchung: 23.12.2025                                  │
│                                                               │
│ ──────────────────────────────────────────────────────       │
│                                                               │
│ Beschreibung:                                                │
│ Luxuriöse Villa mit Meerblick, direkt am Strand.            │
│ 4 Schlafzimmer, 2 Bäder, voll ausgestattete Küche.          │
│ Großer Garten mit Terrasse und Grill.                       │
│                                                               │
│ ──────────────────────────────────────────────────────       │
│                                                               │
│ Ausstattung:                                                 │
│ • WLAN                                                       │
│ • Küche (voll ausgestattet)                                  │
│ • Waschmaschine                                              │
│ • Parkplatz                                                  │
│ • Garten                                                     │
│ • Haustiere erlaubt                                          │
│                                                               │
│ ──────────────────────────────────────────────────────       │
│                                                               │
│ Preis:                                                       │
│ €120/Nacht                                                   │
│ Reinigungsgebühr: €80                                        │
│                                                               │
│ ──────────────────────────────────────────────────────       │
│                                                               │
│ ℹ️ Möchten Sie Details ändern? Kontaktieren Sie:            │
│   info@agentur-name.de oder +49 4651 1234567                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**WICHTIG:**
- KEIN "Bearbeiten" Button
- KEIN "Löschen" Button
- NUR READ-ONLY Ansicht
- Hinweis: "Kontaktieren Sie Agentur für Änderungen"

---

### 5. Buchungs-Liste (READ-ONLY)

#### 5.1 Wireframe: Buchungs-Liste (Desktop)

```
┌─────────────────────────────────────────────────────────────┐
│ Buchungen                                                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Filter: [Alle Objekte ▼] [Alle Status ▼] [Alle Daten ▼]    │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Check-in │ Check-out │ Objekt          │ Gast  │ Status│  │
│ ├────────────────────────────────────────────────────────┤  │
│ │ 23.12.25 │ 30.12.25  │ Villa Meerblick │ Schmidt│ ✅  │  │
│ │ 24.12.25 │ 27.12.25  │ Ferienwohnung.. │ Meyer  │ ✅  │  │
│ │ 26.12.25 │ 02.01.26  │ Penthouse City  │ Becker │ ✅  │  │
│ │ 01.01.26 │ 08.01.26  │ Villa Meerblick │ Müller │ ⏳  │  │
│ │ 10.01.26 │ 17.01.26  │ Ferienwohnung.. │ Wagner │ ⏳  │  │
│ │ 15.01.26 │ 22.01.26  │ Penthouse City  │ Schulz │ ⏳  │  │
│ │ 20.01.26 │ 27.01.26  │ Villa Meerblick │ Fischer│ ⏳  │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ Legende:                                                     │
│ ✅ Bestätigt   ⏳ Zahlung ausstehend   ❌ Storniert          │
│                                                               │
│                              [Seite 1 von 3]  [Weiter →]    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 5.2 Wireframe: Buchungs-Details (READ-ONLY)

```
┌─────────────────────────────────────────────────────────────┐
│ [← Zurück]  Buchung #DB-2025-00123                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Status: Bestätigt ✅                                         │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Objekt                                                  │  │
│ │ Villa Meerblick, Sylt                                  │  │
│ │ 4 Zimmer, 8 Gäste, 120m²                               │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Reisedaten                                              │  │
│ │ Check-in:  23.12.2025 (ab 15:00 Uhr)                   │  │
│ │ Check-out: 30.12.2025 (bis 10:00 Uhr)                  │  │
│ │ Aufenthalt: 7 Nächte                                    │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Gast                                                    │  │
│ │ Familie Schmidt                                         │  │
│ │ 2 Erwachsene, 1 Kind                                    │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Preis                                                   │  │
│ │ 7 Nächte × €120/Nacht              €840,00            │  │
│ │ Reinigungsgebühr                    €80,00             │  │
│ │ ───────────────────────────────────────────             │  │
│ │ Gesamt (inkl. MwSt.)                €920,00            │  │
│ │ Status: Bezahlt ✅                                      │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Quelle                                                  │  │
│ │ Airbnb                                                  │  │
│ │ Buchungsnummer: HM1234567890                           │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ℹ️ Fragen zur Buchung? Kontaktieren Sie:                    │
│   info@agentur-name.de oder +49 4651 1234567                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

**WICHTIG:**
- KEIN "Bearbeiten" Button
- KEIN "Stornieren" Button
- NUR READ-ONLY Ansicht
- Hinweis: "Kontaktieren Sie Agentur für Änderungen"

---

### 6. Berichte für Eigentümer

#### 6.1 Konzept

**Ziel:**
- Eigentümer kann Umsatz und Auslastung seiner Objekte einsehen
- Transparenz über Buchungen
- Export als CSV oder PDF

**Berichte:**
1. Umsatz pro Objekt (Monat, Jahr)
2. Auslastung (Occupancy Rate)
3. Buchungs-Historie (letzten 12 Monate)

#### 6.2 Wireframe: Berichte-Seite (Desktop)

```
┌─────────────────────────────────────────────────────────────┐
│ Berichte                                                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│ Filter: [Alle Objekte ▼] [Zeitraum: Letzten 12 Monate ▼]   │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Umsatz pro Objekt (Letzten 12 Monate)                  │  │
│ ├────────────────────────────────────────────────────────┤  │
│ │                                                         │  │
│ │ Villa Meerblick                          €28.800       │  │
│ │ Ferienwohnung Strand                     €14.400       │  │
│ │ Penthouse City                           €21.600       │  │
│ │ ───────────────────────────────────────────────         │  │
│ │ Gesamt                                   €64.800       │  │
│ │                                                         │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Auslastung pro Objekt (Letzten 12 Monate)              │  │
│ ├────────────────────────────────────────────────────────┤  │
│ │                                                         │  │
│ │     █                                                   │  │
│ │     █      █                                            │  │
│ │     █      █      █                                     │  │
│ │     █      █      █      █      █      █               │  │
│ │  ───┴──────┴──────┴──────┴──────┴──────┴───            │  │
│ │  Villa  Ferien  Pent.                                   │  │
│ │  Meer.  Strand  City                                    │  │
│ │                                                         │  │
│ │  Villa Meerblick: 80%                                   │  │
│ │  Ferienwohnung Strand: 60%                              │  │
│ │  Penthouse City: 72%                                    │  │
│ │                                                         │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ ┌────────────────────────────────────────────────────────┐  │
│ │ Buchungs-Historie (Letzten 12 Monate)                  │  │
│ ├────────────────────────────────────────────────────────┤  │
│ │                                                         │  │
│ │ Monat     │ Buchungen │ Nächte │ Umsatz                │  │
│ │ Dez 2025  │     12    │   48   │ €5.760                │  │
│ │ Nov 2025  │      8    │   32   │ €3.840                │  │
│ │ Okt 2025  │     10    │   40   │ €4.800                │  │
│ │ Sep 2025  │      9    │   36   │ €4.320                │  │
│ │ Aug 2025  │     15    │   60   │ €7.200                │  │
│ │ ...                                                     │  │
│ │                                                         │  │
│ └────────────────────────────────────────────────────────┘  │
│                                                               │
│ [Als CSV exportieren]  [Als PDF exportieren]                │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

#### 6.3 Export-Formate

**CSV-Export (Excel-kompatibel):**
```csv
Monat,Objekt,Buchungen,Nächte,Umsatz
Dez 2025,Villa Meerblick,5,20,€2400
Dez 2025,Ferienwohnung Strand,4,16,€1920
Dez 2025,Penthouse City,3,12,€1440
Nov 2025,Villa Meerblick,3,12,€1440
...
```

**PDF-Export:**
```
┌────────────────────────────────────────┐
│ Umsatz-Bericht                         │
│ Eigentümer: Herr Müller                │
│ Zeitraum: Letzten 12 Monate            │
│ Erstellt: 22.12.2025                   │
├────────────────────────────────────────┤
│                                        │
│ UMSATZ PRO OBJEKT:                     │
│ Villa Meerblick           €28.800      │
│ Ferienwohnung Strand      €14.400      │
│ Penthouse City            €21.600      │
│ ────────────────────────────           │
│ Gesamt                    €64.800      │
│                                        │
│ AUSLASTUNG:                            │
│ Villa Meerblick           80%          │
│ Ferienwohnung Strand      60%          │
│ Penthouse City            72%          │
│                                        │
│ [Chart: Umsatz pro Monat]              │
│                                        │
└────────────────────────────────────────┘
```

---

### 7. RLS-Konzept (Row-Level Security)

#### 7.1 Supabase PostgreSQL Policies

**Policy 1: Eigentümer-Isolation (properties)**

```sql
-- Eigentümer sieht nur eigene Objekte
CREATE POLICY owner_read_own_properties
ON properties
FOR SELECT
USING (
  (auth.jwt() ->> 'role' = 'owner' AND owner_id = auth.uid())
  OR
  (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff')
   AND agency_id = (auth.jwt() ->> 'agency_id')::uuid)
);

-- Eigentümer kann NICHTS bearbeiten
CREATE POLICY owner_no_update_properties
ON properties
FOR UPDATE
USING (
  auth.jwt() ->> 'role' IN ('admin', 'manager')
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
);

-- Eigentümer kann NICHTS erstellen
CREATE POLICY owner_no_insert_properties
ON properties
FOR INSERT
WITH CHECK (
  auth.jwt() ->> 'role' IN ('admin', 'manager')
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
);

-- Eigentümer kann NICHTS löschen
CREATE POLICY owner_no_delete_properties
ON properties
FOR DELETE
USING (
  auth.jwt() ->> 'role' = 'admin'
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
);
```

**Policy 2: Eigentümer-Isolation (bookings)**

```sql
-- Eigentümer sieht nur Buchungen seiner eigenen Objekte
CREATE POLICY owner_read_own_bookings
ON bookings
FOR SELECT
USING (
  (auth.jwt() ->> 'role' = 'owner'
   AND property_id IN (
     SELECT id FROM properties WHERE owner_id = auth.uid()
   ))
  OR
  (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff', 'accountant')
   AND agency_id = (auth.jwt() ->> 'agency_id')::uuid)
);

-- Eigentümer kann Buchungen NICHT bearbeiten
CREATE POLICY owner_no_update_bookings
ON bookings
FOR UPDATE
USING (
  auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff')
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
);

-- Eigentümer kann Buchungen NICHT erstellen
CREATE POLICY owner_no_insert_bookings
ON bookings
FOR INSERT
WITH CHECK (
  auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff')
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
);

-- Eigentümer kann Buchungen NICHT löschen
CREATE POLICY owner_no_delete_bookings
ON bookings
FOR DELETE
USING (
  auth.jwt() ->> 'role' IN ('admin', 'manager')
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
);
```

**Policy 3: Eigentümer-Isolation (direct_bookings)**

```sql
-- Eigentümer sieht nur Direct Bookings seiner eigenen Objekte
CREATE POLICY owner_read_own_direct_bookings
ON direct_bookings
FOR SELECT
USING (
  (auth.jwt() ->> 'role' = 'owner'
   AND property_id IN (
     SELECT id FROM properties WHERE owner_id = auth.uid()
   ))
  OR
  (auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff')
   AND agency_id = (auth.jwt() ->> 'agency_id')::uuid)
);

-- Eigentümer kann NICHTS bearbeiten
CREATE POLICY owner_no_update_direct_bookings
ON direct_bookings
FOR UPDATE
USING (
  auth.jwt() ->> 'role' IN ('admin', 'manager', 'staff')
  AND agency_id = (auth.jwt() ->> 'agency_id')::uuid
);
```

#### 7.2 Code-Beispiele (Frontend)

**Supabase Client (automatische RLS):**

```javascript
// Frontend: Objekte abrufen (für Eigentümer)
async function getOwnerProperties() {
  const { data, error } = await supabase
    .from('properties')
    .select('*')
    .order('created_at', { ascending: false });

  // RLS filtert automatisch:
  // - Eigentümer sieht nur owner_id = auth.uid()
  // - Admin/Manager sieht alle Objekte ihrer Agentur

  return data;
}

// Frontend: Buchungen abrufen (für Eigentümer)
async function getOwnerBookings() {
  const { data, error } = await supabase
    .from('bookings')
    .select(`
      *,
      property:properties(*)
    `)
    .order('check_in', { ascending: true });

  // RLS filtert automatisch:
  // - Eigentümer sieht nur Buchungen seiner eigenen Objekte

  return data;
}
```

**WICHTIG:**
- KEINE manuelle Filterung nötig (Datenbank macht das)
- Sicherheit auf Datenbank-Ebene (nicht nur Frontend)
- Selbst bei SQL-Injection sieht User nur eigene Daten

#### 7.3 Testen von RLS Policies

**Test 1: Eigentümer sieht nur eigene Objekte**

```sql
-- Als Eigentümer einloggen (JWT mit owner_id = uuid1)
SELECT * FROM properties;

-- Ergebnis: Nur Objekte mit owner_id = uuid1

-- Versuch, andere Objekte zu sehen (manuell)
SELECT * FROM properties WHERE owner_id = 'uuid2';

-- Ergebnis: Leer (RLS blockiert)
```

**Test 2: Eigentümer kann nichts bearbeiten**

```sql
-- Versuch, Objekt zu bearbeiten
UPDATE properties SET name = 'Neuer Name' WHERE id = 'uuid1';

-- Ergebnis: Fehler (RLS blockiert)
```

**Test 3: Eigentümer sieht nur eigene Buchungen**

```sql
-- Als Eigentümer einloggen
SELECT * FROM bookings;

-- Ergebnis: Nur Buchungen von Objekten mit owner_id = uuid1
```

---

## Anhang

### A1. Datenbank-Schema (vollständig)

**Tabelle: properties (erweitert um owner_id)**

```sql
ALTER TABLE properties
ADD COLUMN owner_id UUID REFERENCES auth.users(id);

CREATE INDEX idx_properties_owner ON properties(owner_id);
```

**Tabelle: direct_bookings (neu)**

```sql
CREATE TABLE direct_bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID NOT NULL REFERENCES agencies(id),
  property_id UUID NOT NULL REFERENCES properties(id),

  -- Gästedaten
  guest_name VARCHAR(255) NOT NULL,
  guest_email VARCHAR(255) NOT NULL,
  guest_phone VARCHAR(50),
  guest_count_adults INT NOT NULL DEFAULT 1,
  guest_count_children INT NOT NULL DEFAULT 0,
  special_requests TEXT,

  -- Reisedaten
  check_in DATE NOT NULL,
  check_out DATE NOT NULL,
  nights INT GENERATED ALWAYS AS (check_out - check_in) STORED,

  -- Preis
  price_per_night DECIMAL(10, 2) NOT NULL,
  cleaning_fee DECIMAL(10, 2) DEFAULT 0,
  total_price DECIMAL(10, 2) NOT NULL,
  currency VARCHAR(3) DEFAULT 'EUR',

  -- Status
  status VARCHAR(50) NOT NULL DEFAULT 'pending_payment',
  payment_method VARCHAR(50),
  payment_link TEXT,
  paid_at TIMESTAMP,

  -- Metadaten
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),

  CONSTRAINT check_dates CHECK (check_out > check_in),
  CONSTRAINT check_guests CHECK (guest_count_adults > 0)
);

CREATE INDEX idx_direct_bookings_property ON direct_bookings(property_id);
CREATE INDEX idx_direct_bookings_agency ON direct_bookings(agency_id);
CREATE INDEX idx_direct_bookings_status ON direct_bookings(status);
CREATE INDEX idx_direct_bookings_dates ON direct_bookings(check_in, check_out);
```

**Tabelle: external_bookings (neu)**

```sql
CREATE TABLE external_bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  agency_id UUID NOT NULL REFERENCES agencies(id),
  property_id UUID NOT NULL REFERENCES properties(id),

  ical_uid VARCHAR(255) NOT NULL UNIQUE,
  source VARCHAR(50) NOT NULL,

  check_in DATE NOT NULL,
  check_out DATE NOT NULL,
  summary TEXT,

  imported_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_external_bookings_property ON external_bookings(property_id);
CREATE INDEX idx_external_bookings_dates ON external_bookings(check_in, check_out);
CREATE UNIQUE INDEX idx_external_bookings_ical_uid ON external_bookings(ical_uid);
```

### A2. API Endpoints (REST)

**Direct Bookings:**
- `POST /api/direct-bookings/check-availability` - Verfügbarkeit prüfen
- `POST /api/direct-bookings/create` - Buchung erstellen
- `GET /api/direct-bookings/:id` - Buchung abrufen
- `PATCH /api/direct-bookings/:id/status` - Status aktualisieren
- `POST /api/direct-bookings/:id/send-reminder` - Zahlungs-Reminder senden
- `GET /api/properties/:id/availability` - Kalender-Daten abrufen

**Eigentümer-Portal:**
- `GET /api/owner/dashboard` - Dashboard-Daten
- `GET /api/owner/properties` - Eigene Objekte
- `GET /api/owner/properties/:id` - Objekt-Details
- `GET /api/owner/bookings` - Eigene Buchungen
- `GET /api/owner/bookings/:id` - Buchungs-Details
- `GET /api/owner/reports/revenue` - Umsatz-Bericht
- `GET /api/owner/reports/occupancy` - Auslastungs-Bericht
- `GET /api/owner/reports/export` - Export (CSV/PDF)

### A3. E-Mail-Templates (vollständig)

**Siehe Kapitel 4 (Buchungsbestätigung & E-Mails)**

- Template: Gast-Bestätigung (nach Buchung)
- Template: Agentur-Benachrichtigung (neue Buchung)
- Template: Zahlungs-Reminder (nach 3 Tagen)
- Template: Zahlungsbestätigung (nach Zahlung)

---

## Zusammenfassung

### Phase 15: Direct Booking Flow

**Umgesetzt:**
- ✅ Booking Widget (Desktop & Mobile)
- ✅ 4-Schritte Booking Flow (Datum → Gästedaten → Zusammenfassung → Bestätigung)
- ✅ Payment-Integration-Konzept (Stripe, PayPal, Überweisung)
- ✅ KEINE Zahlungsabwicklung durch PMS-Webapp
- ✅ Buchungsbestätigung & E-Mail-Templates (4 Templates)
- ✅ Kalender-Synchronisation (Direct Booking → Airbnb/Booking.com)
- ✅ Konflikt-Erkennung & Handling
- ✅ Backend-Logik (API Endpoints, Datenbank-Schema)

### Phase 16: Eigentümer-Portal

**Umgesetzt:**
- ✅ Eigentümer-Rolle (READ-ONLY, nur eigene Objekte)
- ✅ Eigentümer-Dashboard (Desktop & Mobile)
- ✅ Menü-Struktur (Dashboard, Objekte, Buchungen, Berichte, Profil)
- ✅ Objekt-Liste (READ-ONLY)
- ✅ Buchungs-Liste (READ-ONLY)
- ✅ Berichte (Umsatz, Auslastung, Export CSV/PDF)
- ✅ RLS-Konzept (Supabase PostgreSQL Policies)
- ✅ Code-Beispiele (Frontend & Backend)

### Konsistenz mit Frozen Phases

**Phase 10A/10B/10C:**
- ✅ Token-basierte Farben (White-Label)
- ✅ Deutsche UI-Texte
- ✅ "Less is more" (Menüpunkte verschwinden)

**Phase 11-13:**
- ✅ 5 Rollen (Agentur-Admin, Manager, Mitarbeiter, Eigentümer, Buchhalter)
- ✅ Eigentümer = READ-ONLY
- ✅ RLS auf Datenbank-Ebene

**Phase 14:**
- ✅ B2B-Fokus (Agenturen zahlen, nicht Gäste)
- ✅ KEINE Zahlungsabwicklung durch PMS-Webapp
- ✅ Externe Payment-Provider (Stripe, PayPal, Überweisung)

---

**ENDE Phase 15-16 Dokumentation**
