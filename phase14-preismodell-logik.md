# Phase 14: Preismodell-Logik & Billing-Strategie

**Status:** Draft
**Version:** 1.0
**Erstellt:** 2025-12-22
**Projekt:** PMS-Webapp
**Basis:** Phase 10A (UI/UX), Phase 10B/10C (Visual Design), Phase 11-13 (Agentur-UX & Rollen)

---

## Executive Summary

### Ziel
Vollständiges Preismodell-Konzept mit Marktanalyse, Pricing-Strategie, 3 Pricing-Tiers, Billing-System (Stripe) und Pricing-Page-Design für PMS-Webapp MVP.

### Scope
- **Pricing-Strategie:** Monatlich/Jährlich, Trial, Competitor Analysis
- **Pricing-Tiers:** Starter (€49), Professional (€149), Enterprise (Custom)
- **Feature-Matrix:** Tier × Feature (3×15 Features)
- **Trial & Onboarding:** 14 Tage kostenlos, Conversion-Optimierung
- **Billing-System:** Stripe Subscriptions, Invoicing, Dunning Management
- **Pricing-Page-Konzept:** Wireframe, Copywriting (Deutsch)
- **Klarstellung:** Agentur zahlt, Gäste NICHT

### Leitplanken
- **B2B-Fokus:** Nur Agenturen zahlen, keine Gäste-Zahlungen
- **DACH-Markt:** Deutschland, Österreich, Schweiz
- **Transparent:** Keine versteckten Kosten, jederzeit kündbar
- **Fair:** Flat-Rate Subscription, KEINE Provision auf Buchungen
- **Basis:** Phase 10A/10B/10C, Phase 11-13 unveränderlich (READ-ONLY)

---

## 1. Pricing-Strategie

### 1.1 Geschäftsmodell

**SaaS-Subscription (B2B):**
- Agenturen zahlen monatliche oder jährliche Software-Gebühr
- KEINE Provision auf Buchungen (Unterschied zu Airbnb/Booking.com)
- KEINE Gäste-Zahlungen durch unser System
- Flat-Rate pro Agentur (nicht pro Objekt wie bei Konkurrenz)

**Warum kein Pay-per-Object?**
- Einfachere Preisstruktur (Agenturen wissen genau, was sie zahlen)
- Keine Bestrafung bei Wachstum (Konkurrenz wird teurer pro Objekt)
- Planbare Kosten für Agenturen (kein Risiko bei vielen Objekten)

**Warum keine Provision?**
- B2B-Kunden bevorzugen feste Kosten (bessere Budgetplanung)
- Keine Abhängigkeit vom Umsatz (Agentur behält volle Kontrolle)
- Differenzierung zu Airbnb/Booking.com (die 15-20% Provision nehmen)

### 1.2 Monatlich vs. Jährlich

**Monatlich:**
- Voller Preis (z.B. €49/Monat)
- Monatlich kündbar
- Ideal für: Neue Kunden, kleine Agenturen, Trial-to-Paid

**Jährlich:**
- 20% Rabatt (z.B. €39/Monat statt €49/Monat)
- Jährlich im Voraus bezahlt (€468 statt €588)
- 12 Monate Mindestlaufzeit
- Ideal für: Etablierte Agenturen, Kosteneinsparung

**Empfehlung:**
- Beide Optionen anbieten
- Jährlich prominenter bewerben (höhere Customer Lifetime Value)
- CTA: "2 Monate gratis bei Jahreszahlung"

### 1.3 Free Trial

**14 Tage kostenlos:**
- Voller Zugriff auf **Professional** Tier (nicht Starter, nicht Enterprise)
- KEINE Kreditkarte erforderlich (frictionless signup)
- Nach 14 Tagen: Manuelle Upgrade-Entscheidung (keine automatische Abbuchung)

**Warum Professional Tier für Trial?**
- Zeigt volle Funktionalität (alle Channels, Advanced Reports)
- Höhere Conversion-Rate (User sieht Mehrwert)
- Downgrade auf Starter möglich (wenn Budget limitiert)

**Warum KEINE Kreditkarte?**
- Höhere Signup-Rate (keine Hemmschwelle)
- Kein Risiko für User (keine versehentliche Abbuchung)
- Bessere UX (weniger Friction im Signup-Flow)

**Conversion-Flow:**
- Tag 1: Willkommens-E-Mail + Setup-Guide
- Tag 7: Check-in-E-Mail ("Wie läuft's?")
- Tag 12: Reminder-E-Mail ("Noch 2 Tage kostenlos")
- Tag 14: Conversion-E-Mail ("Jetzt upgraden und weitermachen")

---

## 2. Competitor Analysis

### 2.1 Guesty

**Preismodell:**
- **Guesty Lite:** Ab $9/Monat + 1% Fee pro Buchung (für 1-3 Objekte)
- **Guesty Pro:** Custom Pricing (für 4-199 Objekte)
- **Guesty Enterprise:** Custom Pricing (für 200+ Objekte)

**Features:**
- Alle Channels (Airbnb, Vrbo, Booking.com, Expedia, etc.)
- Automatisierte Messaging
- Dynamic Pricing (PriceOptimizer)
- Team-Management
- Reporting & Analytics

**Kosten (geschätzt für 50 Objekte):**
- **Pro Tier:** $100-300/Monat/Objekt = $5.000-15.000/Monat
- **Zusätzliche Fees:** 3-5% pro Buchung + Cancellation Fees

**User-Feedback:**
- Positiv: Umfangreiche Features, gute Automatisierung, stabile Plattform
- Negativ: SEHR teuer, versteckte Fees, komplizierte Preisstruktur, langsamer Support

**Quelle:** [Guesty Pricing auf GetApp](https://www.getapp.com/hospitality-travel-software/a/guesty/pricing/)

---

### 2.2 Hostaway

**Preismodell:**
- Tailored Pricing (Custom Quotes)
- Setup Fees: $100-500
- Monatlich: Ab $20-40/Monat/Objekt
- Preis sinkt bei mehr Objekten (Staffelung)

**Features:**
- 300+ Integrationen
- AI-powered Automations
- PMS + Channel Manager (All-in-One)
- Direct Booking Websites
- 24/7 Support

**Kosten (geschätzt für 50 Objekte):**
- **Standard:** $20-40/Objekt/Monat = $1.000-2.000/Monat
- **Setup Fee:** $100-500 (einmalig)
- Keine versteckten Fees (laut Hersteller)

**User-Feedback:**
- Positiv: Viele Integrationen, gute AI-Features, transparentere Preisstruktur als Guesty
- Negativ: Immer noch teuer, kein Free Trial, Demo-Pflicht

**Quelle:** [Hostaway Pricing Guide](https://www.hostaway.com/pricing/)

---

### 2.3 Beds24

**Preismodell:**
- Pay-as-you-go (nutzungsbasiert)
- €0.55/Monat pro Link (1 Link = 1 Objekt zu 1 Channel)
- Keine Setup Fees
- Keine Verträge
- Keine Provisionen

**Features:**
- Channel Manager + PMS + Booking Engine
- Airbnb Preferred+ Partner
- Booking.com Premier Partner (10 Jahre)
- Basis-Features (weniger Automatisierung als Guesty/Hostaway)

**Kosten (geschätzt für 50 Objekte mit 3 Channels):**
- 50 Objekte × 3 Channels = 150 Links
- 150 Links × €0.55 = €82.50/Monat
- Start ab €15.50/Monat

**User-Feedback:**
- Positiv: SEHR günstig, transparente Preise, kein Vendor Lock-In, gutes Preis-Leistungs-Verhältnis (4.8/5)
- Negativ: Weniger moderne UI, weniger Automatisierung, weniger Features als Premium-Konkurrenz

**Quelle:** [Beds24 Pricing](https://beds24.com/pricing.html)

---

### 2.4 Markt-Positionierung (PMS-Webapp)

**Unsere Differenzierung:**

| Feature | Guesty | Hostaway | Beds24 | **PMS-Webapp** |
|---------|--------|----------|--------|----------------|
| **Preis (50 Objekte)** | $5.000-15.000/Mo | $1.000-2.000/Mo | €82.50/Mo | **€149/Monat** |
| **Preismodell** | Pay-per-Property | Pay-per-Property | Pay-per-Link | **Flat-Rate/Tier** |
| **Setup Fee** | Ja | $100-500 | Nein | **Nein** |
| **Free Trial** | 14 Tage | Nein | Nein | **14 Tage** |
| **Kreditkarte für Trial** | Ja | - | - | **Nein** |
| **Versteckte Fees** | Ja (3-5% + Cancellation) | Nein | Nein | **Nein** |
| **Provision** | Ja | Nein | Nein | **Nein** |
| **Feature-Umfang** | Sehr hoch (100+ Features) | Hoch (300+ Integrations) | Mittel | **Fokussiert (MVP)** |
| **Zielgruppe** | 50-500+ Objekte | 20-200 Objekte | 5-50 Objekte | **5-100 Objekte** |
| **Support-Sprache** | Englisch | Englisch | Englisch | **Deutsch** |
| **DSGVO-konform** | Ja | Ja | Ja | **Ja (Hosted in DE)** |

**Unsere Value Proposition:**

1. **50-90% günstiger als Guesty/Hostaway:**
   - Guesty (50 Objekte): $5.000-15.000/Monat → **Unsere Ersparnis: $4.851-14.851/Monat**
   - Hostaway (50 Objekte): $1.000-2.000/Monat → **Unsere Ersparnis: $851-1.851/Monat**

2. **Einfacher als Konkurrenz:**
   - Fokus auf essenziellen Features (keine Feature-Overload)
   - Setup in 15 Minuten (nicht Stunden)
   - Deutsche UI (keine Sprachbarriere)

3. **Transparenter als Konkurrenz:**
   - Keine versteckten Fees
   - Keine Provisionen
   - Klare Flat-Rate-Preise (€49, €149, Custom)

4. **Fairer als Konkurrenz:**
   - Kein Pay-per-Property (Wachstum wird nicht bestraft)
   - 14 Tage Trial ohne Kreditkarte
   - Monatlich kündbar (kein Vendor Lock-In)

**Positionierung:**
- **Teurer als:** Beds24 (aber modernere UI, bessere Features)
- **Günstiger als:** Guesty, Hostaway (aber gleiche Kernfunktionen)
- **Ideal für:** Mittelgroße Agenturen (5-100 Objekte) im DACH-Raum

---

## 3. Pricing-Tiers (3 Tiers)

### 3.1 Tier 1: Starter

**Zielgruppe:** Kleine Agenturen (5-20 Objekte)

**Preis:**
- **Monatlich:** €49/Monat
- **Jährlich:** €39/Monat (€468/Jahr statt €588/Jahr) - **20% Rabatt**

**Features:**

**Objektverwaltung:**
- Bis zu 20 Eigenschaften
- Unbegrenzte Buchungen
- Basis-Kalender (Verfügbarkeit)
- Fotos (bis zu 10 pro Objekt)

**Channel-Integration:**
- 1 Kanal (Airbnb ODER Booking.com)
- Echtzeit-Kalender-Synchronisation (iCal)
- Basis-Synchronisations-Logs

**Team & Rechte:**
- Bis zu 3 Team-Mitglieder
- Basis-Rollen (Owner, Manager, Staff)
- Keine Eigentümer-Portale

**Reporting:**
- Basis-Berichte (Occupancy, Revenue)
- Export (CSV)

**Support:**
- Email-Support (48h Response Time)
- Dokumentation & Tutorials

**Was NICHT enthalten:**
- ❌ Mehrere Kanäle gleichzeitig
- ❌ Advanced Reporting (Custom Reports)
- ❌ Priority Support
- ❌ Eigentümer-Portal (Read-Only)
- ❌ White-Label Branding
- ❌ API-Zugang

**Ideal für:**
- Neue Agenturen (5-10 Objekte)
- Budget-bewusste Agenturen
- Trial-to-Paid Conversion (von Professional → Downgrade)

---

### 3.2 Tier 2: Professional (BELIEBT)

**Zielgruppe:** Mittelgroße Agenturen (20-100 Objekte)

**Preis:**
- **Monatlich:** €149/Monat
- **Jährlich:** €119/Monat (€1.428/Jahr statt €1.788/Jahr) - **20% Rabatt**

**Features:**

**Objektverwaltung:**
- Bis zu 100 Eigenschaften
- Unbegrenzte Buchungen
- Advanced Kalender (Multi-Property-View)
- Fotos (unbegrenzt)

**Channel-Integration:**
- Alle Kanäle (Airbnb, Booking.com, Expedia, Direct Bookings)
- Echtzeit-Kalender-Synchronisation (iCal + API)
- Advanced Synchronisations-Logs (Fehler-Reports, Retry-Logs)

**Team & Rechte:**
- Bis zu 10 Team-Mitglieder
- Alle Rollen (Owner, Manager, Staff, Viewer, Buchhalter)
- Eigentümer-Portal (Read-Only für externe Eigentümer)

**Reporting:**
- Advanced Berichte (Custom Reports, Export)
- Revenue-Reports (pro Objekt, pro Kanal)
- Occupancy-Reports (Auslastung, Trends)
- Prognosen (basierend auf historischen Daten)

**Support:**
- Priority Email-Support (24h Response Time)
- Telefon-Support (bei Bedarf)
- Onboarding-Call (optional, 30 Minuten)

**Zusätzlich:**
- ✅ Eigentümer-Portal (Read-Only)
- ✅ Erweiterte Rollen & Rechte (RBAC)
- ✅ Custom Reports
- ✅ Priority Support

**Was NICHT enthalten:**
- ❌ White-Label Branding
- ❌ API-Zugang
- ❌ Dedicated Account Manager
- ❌ Custom Channel-Integrationen
- ❌ SLA (99.9% Uptime Garantie)

**Ideal für:**
- Etablierte Agenturen (20-100 Objekte)
- Agenturen mit mehreren Channels
- Agenturen mit externen Eigentümern
- **TRIAL-DEFAULT (14 Tage kostenlos)**

---

### 3.3 Tier 3: Enterprise (Custom Pricing)

**Zielgruppe:** Große Agenturen (100+ Objekte)

**Preis:**
- **Custom Pricing** (ab €499/Monat)
- Individuelles Angebot (basierend auf Anzahl Objekte, Features, Support)

**Features:**

**Objektverwaltung:**
- Unbegrenzte Eigenschaften
- Unbegrenzte Buchungen
- Custom Features (auf Anfrage)

**Channel-Integration:**
- Alle Kanäle + Custom Channel-Integration
- Dedicated Channel-Support (z.B. lokale Portale)
- Zwei-Wege-Synchronisation (Preise, Verfügbarkeit, Buchungen)

**Team & Rechte:**
- Unbegrenzte Team-Mitglieder
- Custom Rollen (auf Anfrage)
- White-Label Branding (Logo, Farben, Custom Domain)

**Reporting:**
- Custom Reports (auf Anfrage)
- API-Zugang (für externe Tools)
- Daten-Export (alle Formate)

**Support:**
- Dedicated Account Manager
- Phone & Priority Support (4h Response Time)
- Custom Onboarding & Training (vor Ort oder Remote)
- 24/7 Hotline (für kritische Issues)

**Zusätzlich:**
- ✅ White-Label Branding (Agentur-Logo, Farben)
- ✅ API-Zugang (REST API, Webhooks)
- ✅ Dedicated Account Manager
- ✅ SLA (99.9% Uptime Garantie)
- ✅ Custom Features (auf Anfrage)
- ✅ Custom Onboarding (vor Ort oder Remote)
- ✅ Custom Channel-Integrationen

**Ideal für:**
- Große Agenturen (100-500 Objekte)
- White-Label-Bedarf (eigenes Branding)
- API-Integration-Bedarf (externe Tools)
- Spezielle Anforderungen (Custom Features)

**CTA:** "Kontakt aufnehmen für individuelles Angebot"

---

## 4. Feature-Matrix (Tier × Feature)

### 4.1 Vollständige Tabelle

| Feature | Starter | Professional | Enterprise |
|---------|---------|--------------|------------|
| **PREIS** |
| Monatlich | €49/Monat | €149/Monat | Ab €499/Monat |
| Jährlich (20% Rabatt) | €39/Monat | €119/Monat | Custom |
| **EIGENSCHAFTEN** |
| Anzahl Eigenschaften | Bis 20 | Bis 100 | Unbegrenzt |
| Buchungen | Unbegrenzt | Unbegrenzt | Unbegrenzt |
| Fotos pro Objekt | Bis 10 | Unbegrenzt | Unbegrenzt |
| Kalender-Ansicht | Basis | Advanced (Multi-Property) | Custom |
| **CHANNELS** |
| Anzahl Kanäle | 1 Kanal | Alle Kanäle | Alle + Custom |
| Airbnb | ✅ (oder Booking.com) | ✅ | ✅ |
| Booking.com | ✅ (oder Airbnb) | ✅ | ✅ |
| Expedia, VRBO, etc. | ❌ | ✅ | ✅ |
| Direct Bookings (eigene Website) | ✅ | ✅ | ✅ |
| Custom Channel-Integration | ❌ | ❌ | ✅ |
| Synchronisation | iCal (Echtzeit) | iCal + API | iCal + API + Custom |
| Sync-Logs | Basis | Advanced (Fehler-Reports) | Custom (24/7 Monitoring) |
| **TEAM & RECHTE** |
| Team-Mitglieder | Bis 3 | Bis 10 | Unbegrenzt |
| Rollen | Owner, Manager, Staff | Alle Rollen + Viewer + Buchhalter | Custom Rollen |
| Eigentümer-Portal (Read-Only) | ❌ | ✅ | ✅ |
| Row-Level Security (RLS) | ✅ | ✅ | ✅ |
| **REPORTING** |
| Basis-Berichte | ✅ (Occupancy, Revenue) | ✅ | ✅ |
| Advanced Reports | ❌ | ✅ (Custom Reports) | ✅ (Custom Reports) |
| Export | CSV | CSV, PDF | Alle Formate |
| Revenue-Reports | ✅ | ✅ (pro Objekt, pro Kanal) | ✅ (Custom) |
| Prognosen | ❌ | ✅ | ✅ (Custom Algorithmen) |
| **SUPPORT** |
| Email-Support | ✅ (48h Response) | ✅ (24h Response, Priority) | ✅ (4h Response, Dedicated) |
| Telefon-Support | ❌ | ✅ (bei Bedarf) | ✅ (24/7 Hotline) |
| Onboarding-Call | ❌ | ✅ (30 Min, optional) | ✅ (Custom, vor Ort oder Remote) |
| Dokumentation & Tutorials | ✅ | ✅ | ✅ |
| Dedicated Account Manager | ❌ | ❌ | ✅ |
| **ZUSÄTZLICHE FEATURES** |
| White-Label Branding | ❌ | ❌ | ✅ (Logo, Farben, Domain) |
| API-Zugang | ❌ | ❌ | ✅ (REST API, Webhooks) |
| SLA (99.9% Uptime) | ❌ | ❌ | ✅ |
| Custom Features | ❌ | ❌ | ✅ (auf Anfrage) |
| **TRIAL & KÜNDIGUNG** |
| Free Trial | 14 Tage | 14 Tage | 14 Tage (auf Anfrage) |
| Kreditkarte für Trial | Nein | Nein | Nein |
| Kündigung | Monatlich | Monatlich | Custom (meist Jahresvertrag) |
| Vertragslaufzeit | Keine | Keine | 12 Monate (empfohlen) |

**Legende:**
- ✅ = Enthalten
- ❌ = Nicht enthalten
- Custom = Individuell verhandelbar

---

## 5. Trial & Onboarding (14 Tage kostenlos)

### 5.1 Trial-Setup

**Trial-Dauer:** 14 Tage

**Trial-Umfang:**
- Voller Zugriff auf **Professional** Tier (nicht Starter, nicht Enterprise)
- Alle Features (Alle Kanäle, Advanced Reports, 10 Team-Mitglieder)
- Kein Feature-Limit (volle Funktionalität)

**Warum Professional für Trial?**
- Zeigt volle Plattform-Funktionalität (alle Channels, Advanced Reports)
- Höhere Conversion-Rate (User sieht Mehrwert vs. Konkurrenz)
- Einfacher Downgrade auf Starter (wenn Budget limitiert)
- Einfacher Upgrade auf Enterprise (wenn Bedarf)

**Kreditkarte erforderlich:** NEIN

**Warum keine Kreditkarte?**
- Höhere Signup-Rate (keine Hemmschwelle, 30-50% höhere Conversion)
- Kein Risiko für User (keine versehentliche Abbuchung)
- Bessere UX (weniger Friction, kein "Dark Pattern")
- Vertrauen (wir sind so überzeugt, dass wir kein Geld im Voraus verlangen)

**Nach 14 Tagen:**
- Manuelle Upgrade-Entscheidung (keine automatische Abbuchung)
- User wählt Plan (Starter, Professional, Enterprise)
- Zahlungsmethode hinterlegen (Stripe)
- Erste Rechnung (nach Upgrade)

---

### 5.2 Trial-to-Paid Conversion-Optimierung

**Ziel:** 40% Trial-to-Paid Conversion Rate (10 Trials → 4 Paid Customers)

**Conversion-Flow (E-Mail-Kampagne):**

**Tag 1: Willkommens-E-Mail**
```
Betreff: Willkommen bei PMS-Webapp! Ihre 14 Tage Trial startet jetzt.

Hallo [Name],

Willkommen bei PMS-Webapp! Ihre 14-tägige kostenlose Testphase hat gerade begonnen.

Was Sie jetzt tun können:
1. Objekte importieren (CSV oder manuell)
2. Airbnb verbinden (3 Klicks, OAuth)
3. Team einladen (bis zu 10 Mitglieder)

Brauchen Sie Hilfe? Hier sind Ihre ersten Schritte:
[Link: Setup-Guide (PDF)]
[Link: Video-Tutorial (5 Minuten)]

Viel Erfolg!
Ihr PMS-Webapp Team

PS: Keine Kreditkarte erforderlich. Nach 14 Tagen entscheiden Sie selbst, ob Sie weitermachen möchten.
```

**Tag 3: Tutorial-Video**
```
Betreff: Erste Schritte mit PMS-Webapp (5 Minuten Tutorial)

Hallo [Name],

Sie sind jetzt seit 3 Tagen dabei. Hier ist ein kurzes Tutorial, um das Beste aus PMS-Webapp herauszuholen:

[Link: Video-Tutorial (5 Minuten)]
- Objekte anlegen (1 Minute)
- Airbnb verbinden (1 Minute)
- Buchungen verwalten (2 Minuten)
- Team einladen (1 Minute)

Haben Sie Fragen? Antworten Sie einfach auf diese E-Mail!

Viele Grüße,
[Support-Name]
```

**Tag 7: Check-in-E-Mail ("Wie läuft's?")**
```
Betreff: Wie läuft's mit PMS-Webapp?

Hallo [Name],

Sie sind jetzt seit 7 Tagen dabei. Wie läuft's?

Haben Sie schon:
✅ Objekte angelegt?
✅ Airbnb verbunden?
✅ Erste Buchungen synchronisiert?

Falls nicht, können wir helfen! Buchen Sie einen kostenlosen 30-Minuten-Call:
[Link: Calendly]

Oder antworten Sie einfach auf diese E-Mail mit Ihren Fragen.

Noch 7 Tage kostenlos!
[Support-Name]
```

**Tag 10: Feature-Highlight**
```
Betreff: Wussten Sie schon? Advanced Reports in PMS-Webapp

Hallo [Name],

Noch 4 Tage in Ihrer Testphase!

Haben Sie schon unsere Advanced Reports ausprobiert?
- Umsatz pro Objekt (Monat, Jahr)
- Auslastung pro Kanal (Airbnb vs. Booking.com)
- Prognosen (basierend auf historischen Daten)

[Link: Reports-Tutorial (3 Minuten)]

Fragen? Antworten Sie einfach auf diese E-Mail!

Viele Grüße,
[Support-Name]
```

**Tag 12: Reminder ("Noch 2 Tage")**
```
Betreff: Ihre Testphase endet in 2 Tagen

Hallo [Name],

Ihre 14-tägige Testphase endet in 2 Tagen (am [Datum]).

Möchten Sie weitermachen?
- Starter: €49/Monat (bis 20 Objekte)
- Professional: €149/Monat (bis 100 Objekte, alle Channels)
- Enterprise: Custom Pricing (100+ Objekte, White-Label)

[Link: Jetzt upgraden]

Noch Fragen? Buchen Sie einen kostenlosen Call:
[Link: Calendly]

Viele Grüße,
[Support-Name]
```

**Tag 14: Conversion-E-Mail ("Letzter Tag")**
```
Betreff: Heute endet Ihre Testphase - Jetzt upgraden und weitermachen

Hallo [Name],

Ihre 14-tägige Testphase endet heute um 23:59 Uhr.

Möchten Sie weitermachen?

[Link: Jetzt upgraden (Professional - €149/Monat)]
[Link: Downgrade auf Starter (€49/Monat)]
[Link: Enterprise-Angebot anfordern]

Was passiert, wenn Sie nicht upgraden?
- Ihre Daten bleiben 30 Tage gespeichert
- Sie können jederzeit zurückkommen
- Keine automatische Abbuchung

Haben Sie noch Fragen? Antworten Sie einfach auf diese E-Mail!

Viele Grüße,
[Support-Name]

PS: Jährliche Zahlung? Sparen Sie 20% (2 Monate gratis)!
```

**Tag 15: Post-Trial-E-Mail (wenn KEIN Upgrade)**
```
Betreff: Schade, dass Sie nicht weitermachen

Hallo [Name],

Schade, dass Sie nicht bei uns weitermachen.

Dürfen wir fragen, warum?
[Link: Feedback-Formular (2 Minuten)]

Ihre Daten bleiben 30 Tage gespeichert. Möchten Sie doch weitermachen?
[Link: Jetzt upgraden]

Viele Grüße,
[Support-Name]
```

---

### 5.3 Onboarding-Flow (während Trial)

**Ziel:** User zum Erfolg führen (aktivieren, Features zeigen, Mehrwert demonstrieren)

**Onboarding-Schritte:**

**1. Signup (Tag 0):**
- E-Mail + Passwort eingeben
- E-Mail bestätigen
- Agentur-Name eingeben
- Fertig (voller Zugriff)

**2. Setup-Wizard (Tag 0):**

**Schritt 1: Erste Eigenschaft anlegen**
```
┌─────────────────────────────────────────┐
│ Willkommen bei PMS-Webapp!              │
│                                         │
│ Schritt 1 von 3: Erste Eigenschaft     │
│                                         │
│ [Input: Eigenschaftsname]               │
│ [Input: Adresse]                        │
│ [Input: Schlafzimmer, Badezimmer]       │
│                                         │
│ [Weiter →]                              │
│ [Überspringen]                          │
└─────────────────────────────────────────┘
```

**Schritt 2: Airbnb verbinden**
```
┌─────────────────────────────────────────┐
│ Fast fertig!                            │
│                                         │
│ Schritt 2 von 3: Airbnb verbinden       │
│                                         │
│ Verbinden Sie Airbnb, um Buchungen      │
│ automatisch zu synchronisieren.         │
│                                         │
│ [Mit Airbnb verbinden (OAuth)]          │
│ [Später verbinden]                      │
└─────────────────────────────────────────┘
```

**Schritt 3: Team einladen (optional)**
```
┌─────────────────────────────────────────┐
│ Letzter Schritt!                        │
│                                         │
│ Schritt 3 von 3: Team einladen          │
│                                         │
│ Laden Sie Ihr Team ein (optional).      │
│                                         │
│ [Input: E-Mail-Adresse]                 │
│ [Dropdown: Rolle (Manager, Staff)]      │
│                                         │
│ [Einladen]                              │
│ [Überspringen]                          │
└─────────────────────────────────────────┘
```

**4. Dashboard (Tag 0):**
- Erste Eigenschaft sichtbar
- Airbnb-Status (Verbunden oder "Jetzt verbinden")
- "Nächste Schritte" Widget:
  - ✅ Erste Eigenschaft angelegt
  - ⚠️ Airbnb noch nicht verbunden → [Jetzt verbinden]
  - ⚠️ Team noch nicht eingeladen → [Jetzt einladen]

**5. Demo-Daten (optional):**
- "Möchten Sie mit Demo-Daten starten?" (Prompt beim ersten Login)
- 3 Demo-Eigenschaften
- 5 Demo-Buchungen
- Ideal zum Ausprobieren (ohne eigene Daten)

---

### 5.4 Conversion-Optimierung (A/B-Tests, Post-MVP)

**Hypothesen für höhere Conversion:**

**1. Onboarding-Call (Tag 7):**
- Hypothese: Persönlicher Kontakt erhöht Conversion
- Test: 50% bekommen Call-Angebot, 50% nicht
- Messung: Trial-to-Paid Conversion Rate

**2. Discount (Tag 13):**
- Hypothese: 10% Rabatt erhöht Conversion
- Test: "10% Rabatt bei Upgrade heute"
- Messung: Conversion Rate + Revenue Impact

**3. Feature-Highlight (während Trial):**
- Hypothese: User nutzen Features nicht → zeigen Features aktiv
- Test: In-App-Prompts ("Haben Sie schon Advanced Reports ausprobiert?")
- Messung: Feature Usage + Conversion Rate

**4. Social Proof (Pricing Page):**
- Hypothese: Testimonials erhöhen Vertrauen
- Test: Testimonials prominenter platzieren (oben statt unten)
- Messung: Pricing Page → Trial Conversion

---

## 6. Billing-System (Stripe)

### 6.1 Stripe Subscriptions

**Setup:**
- Stripe Checkout (Hosted Payment Page)
- Stripe Subscriptions (Recurring Billing)
- Stripe Customer Portal (Self-Service: Rechnungen, Zahlungsmethode, Abo kündigen)

**Preismodell in Stripe:**
- 3 Produkte (Starter, Professional, Enterprise)
- 2 Preise pro Produkt (Monatlich, Jährlich)
- Metadaten: Tier-Limits (z.B. max_properties: 20 für Starter)

**Stripe-Produkte (Konfiguration):**

**Starter:**
- Produkt: "PMS-Webapp Starter"
- Preis (Monatlich): €49/Monat (recurring)
- Preis (Jährlich): €468/Jahr (recurring, jährlich) = €39/Monat
- Metadaten: `{ "tier": "starter", "max_properties": 20, "max_team_members": 3 }`

**Professional:**
- Produkt: "PMS-Webapp Professional"
- Preis (Monatlich): €149/Monat (recurring)
- Preis (Jährlich): €1.428/Jahr (recurring, jährlich) = €119/Monat
- Metadaten: `{ "tier": "professional", "max_properties": 100, "max_team_members": 10 }`

**Enterprise:**
- Produkt: "PMS-Webapp Enterprise"
- Preis (Monatlich): Custom (erstellt per API)
- Preis (Jährlich): Custom (erstellt per API)
- Metadaten: `{ "tier": "enterprise", "max_properties": null, "max_team_members": null }`

---

### 6.2 Payment Methods

**Kreditkarte:**
- Visa, Mastercard, American Express
- 3D Secure 2.0 (SCA-konform, EU-Regulierung)
- Automatische Retry bei fehlgeschlagener Zahlung

**SEPA-Lastschrift (EU):**
- SEPA Direct Debit
- Ideal für: Deutsche Agenturen (bevorzugte Zahlungsmethode)
- Automatische Abbuchung (nach Mandat-Bestätigung)

**Rechnung (nur Enterprise, auf Anfrage):**
- Manuelle Rechnungserstellung
- Zahlungsziel: 14 Tage
- Nur für: Enterprise-Kunden mit Jahresvertrag

**NICHT unterstützt (MVP):**
- PayPal (zu hohe Fees, komplexe Subscription-Integration)
- Bitcoin/Crypto (zu volatil, rechtlich unklar)
- Überweisung (kein automatisches Billing)

---

### 6.3 Invoicing (Rechnungserstellung)

**Automatische Rechnungen:**
- Stripe erstellt automatisch Rechnung (PDF)
- E-Mail-Versand am Anfang des Monats (oder bei Jahres-Abbrechnung)
- Rechnungsadresse anpassbar (in Stripe Customer Portal)

**Rechnungs-Format (Deutsch, DSGVO-konform):**
```
┌────────────────────────────────────────┐
│ RECHNUNG                               │
│                                        │
│ Rechnungsnummer: #INV-2025-001         │
│ Datum: 01.01.2025                      │
│ Zahlungsziel: 14.01.2025               │
│                                        │
│ Von:                                   │
│ PMS-Webapp GmbH                        │
│ Musterstraße 123                       │
│ 10115 Berlin, Deutschland              │
│ USt-IdNr.: DE123456789                 │
│                                        │
│ An:                                    │
│ [Agentur-Name]                         │
│ [Adresse]                              │
│ [USt-IdNr. falls vorhanden]            │
│                                        │
│ ───────────────────────────────────    │
│                                        │
│ Position        Menge   Preis   Summe  │
│ ────────────────────────────────────   │
│ PMS-Webapp      1       €149    €149   │
│ Professional                           │
│ (01.01.-31.01.2025)                    │
│                                        │
│ ───────────────────────────────────    │
│ Netto:                           €149  │
│ MwSt. (19%):                     €28   │
│ ───────────────────────────────────    │
│ Gesamt:                          €177  │
│                                        │
│ Zahlungsmethode: Kreditkarte           │
│ Status: Bezahlt                        │
│                                        │
│ Vielen Dank für Ihr Vertrauen!         │
│ PMS-Webapp Team                        │
└────────────────────────────────────────┘
```

**Rechnungs-Zugriff:**
- Stripe Customer Portal (Self-Service)
- Download als PDF
- Historie aller Rechnungen

**MwSt.-Handling:**
- Deutschland (19% MwSt.): Automatisch berechnet
- EU (mit USt-IdNr.): Reverse Charge (0% MwSt., Kunde zahlt in eigenem Land)
- EU (ohne USt-IdNr.): 19% deutsche MwSt. (oder lokale MwSt.)
- Außerhalb EU: 0% MwSt.

---

### 6.4 Dunning Management (Zahlungsausfall)

**Ziel:** Zahlungsausfälle minimieren, Kunden behalten (nicht sofort kündigen)

**Prozess bei fehlgeschlagener Zahlung:**

**Tag 1: Automatischer Retry (Stripe)**
- Stripe versucht automatisch erneut (nach 24h)
- Kein Eingriff nötig
- User erhält E-Mail: "Zahlung fehlgeschlagen, bitte Zahlungsmethode prüfen"

**Tag 3: Erste Reminder-E-Mail (freundlich)**
```
Betreff: Zahlung fehlgeschlagen - Bitte aktualisieren Sie Ihre Zahlungsmethode

Hallo [Name],

Ihre Zahlung für PMS-Webapp (€149/Monat) ist leider fehlgeschlagen.

Bitte aktualisieren Sie Ihre Zahlungsmethode:
[Link: Stripe Customer Portal]

Was passiert, wenn Sie nicht zahlen?
- Tag 7: Zweite Erinnerung
- Tag 14: Account pausiert (nicht gelöscht)
- Tag 30: Account deaktiviert (Daten bleiben 90 Tage)

Haben Sie Fragen? Antworten Sie einfach auf diese E-Mail!

Viele Grüße,
PMS-Webapp Team
```

**Tag 7: Zweite Reminder-E-Mail (dringend)**
```
Betreff: Dringend: Zahlung fehlgeschlagen - Account wird in 7 Tagen pausiert

Hallo [Name],

Ihre Zahlung für PMS-Webapp ist noch ausstehend.

Bitte aktualisieren Sie Ihre Zahlungsmethode bis [Datum]:
[Link: Stripe Customer Portal]

Was passiert in 7 Tagen?
- Ihr Account wird pausiert (kein Zugriff mehr)
- Ihre Daten bleiben gespeichert
- Sie können jederzeit reaktivieren

Brauchen Sie Hilfe? Antworten Sie einfach auf diese E-Mail!

Viele Grüße,
PMS-Webapp Team
```

**Tag 14: Account pausiert**
- Login möglich, aber Features deaktiviert
- Dashboard zeigt: "Zahlung ausstehend - Bitte aktualisieren Sie Ihre Zahlungsmethode"
- CTA: "Jetzt zahlen und reaktivieren"
- E-Mail: "Account pausiert - Reaktivieren Sie jetzt"

**Tag 30: Account deaktiviert (Daten bleiben 90 Tage)**
- Login NICHT möglich
- E-Mail: "Account deaktiviert - Daten werden in 60 Tagen gelöscht"
- CTA: "Jetzt reaktivieren"

**Tag 90: Daten gelöscht (nach Warnung)**
- E-Mail (Tag 80): "Letzte Warnung: Daten werden in 10 Tagen gelöscht"
- Tag 90: Daten unwiederbringlich gelöscht

**Stripe Dunning Settings:**
- Smart Retries (Stripe optimiert Retry-Zeitpunkte)
- E-Mail-Benachrichtigungen (automatisch)
- Customer Portal (Self-Service Zahlungsmethode-Update)

---

### 6.5 Upgrade & Downgrade

**Upgrade (z.B. Starter → Professional):**

**Prozess:**
1. User klickt "Upgrade auf Professional"
2. Stripe berechnet anteilige Kosten (Prorated Billing)
3. Sofortige Freischaltung aller Professional-Features
4. Nächste Rechnung: Professional-Preis (€149/Monat)

**Berechnung (Beispiel):**
- User zahlt aktuell: Starter (€49/Monat)
- Upgrade am 15. des Monats (Halbzeit)
- Anteilige Berechnung:
  - Starter (restliche 15 Tage): -€24.50 (Gutschrift)
  - Professional (restliche 15 Tage): +€74.50
  - Sofort fällig: €50 (Differenz)
- Nächster Monat: €149 (voller Professional-Preis)

**Downgrade (z.B. Professional → Starter):**

**Prozess:**
1. User klickt "Downgrade auf Starter"
2. Downgrade erfolgt am Ende der aktuellen Abrechnungsperiode (nicht sofort)
3. User behält Professional-Features bis zum Monatsende
4. Nächste Rechnung: Starter-Preis (€49/Monat)
5. Anteilige Gutschrift (nächster Monat)

**Berechnung (Beispiel):**
- User zahlt aktuell: Professional (€149/Monat)
- Downgrade am 15. des Monats
- Downgrade erfolgt am 1. des nächsten Monats
- User behält Professional bis 31.12.
- Ab 01.01.: Starter (€49/Monat)
- Keine sofortige Gutschrift (User hat Professional bereits bezahlt)

**Refund-Policy:**
- Upgrade: Keine Refunds (nur Prorated Billing)
- Downgrade: Keine Refunds (User behält Features bis Monatsende)
- Kündigung: Keine Refunds (User behält Zugriff bis Monatsende)
- Ausnahmen: Auf Anfrage (bei technischen Problemen, Unzufriedenheit in ersten 7 Tagen)

---

## 7. Pricing-Page-Konzept

### 7.1 Wireframe (ASCII-Mockup)

```
┌────────────────────────────────────────────────────────────────┐
│  [Logo]  Preise              [Jetzt kostenlos testen]          │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│         Transparente Preise. Jederzeit kündbar.               │
│             Wählen Sie den Plan, der zu Ihrer Agentur passt.  │
│                                                                │
│  Toggle: [Monatlich] [Jährlich (20% sparen)]                  │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Starter    │  │ Professional │  │  Enterprise  │         │
│  │              │  │   BELIEBT    │  │              │         │
│  │   €49/M      │  │   €149/M     │  │   Custom     │         │
│  │   (€39/M*)   │  │   (€119/M*)  │  │              │         │
│  │              │  │              │  │              │         │
│  │ • 20 Objekte │  │ • 100 Objekte│  │ • ∞ Objekte  │         │
│  │ • 1 Kanal    │  │ • Alle Kanäle│  │ • Custom     │         │
│  │ • 3 Team     │  │ • 10 Team    │  │ • ∞ Team     │         │
│  │ • Basic Rep. │  │ • Advanced   │  │ • Custom     │         │
│  │ • Email (48h)│  │ • Priority   │  │ • Dedicated  │         │
│  │              │  │              │  │              │         │
│  │ [Testen]     │  │ [Testen]     │  │ [Kontakt]    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                │
│  * Bei jährlicher Zahlung (20% Rabatt)                        │
│                                                                │
│  ✅ 14 Tage kostenlos testen                                   │
│  ✅ Keine Kreditkarte erforderlich                             │
│  ✅ Jederzeit kündbar                                          │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ Alle Features im Vergleich                           │     │
│  │                                                       │     │
│  │ [Tabelle: Feature × Tier]                            │     │
│  │ (siehe Feature-Matrix oben)                          │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ FAQ: Häufig gestellte Fragen                         │     │
│  │                                                       │     │
│  │ [?] Was passiert nach dem Trial?                     │     │
│  │     → Sie entscheiden selbst, ob Sie weitermachen.   │     │
│  │       Keine automatische Abbuchung.                  │     │
│  │                                                       │     │
│  │ [?] Kann ich jederzeit kündigen?                     │     │
│  │     → Ja, monatlich kündbar. Keine Mindestlaufzeit.  │     │
│  │                                                       │     │
│  │ [?] Welche Zahlungsmethoden akzeptieren Sie?         │     │
│  │     → Kreditkarte, SEPA-Lastschrift, Rechnung        │     │
│  │       (Enterprise).                                  │     │
│  │                                                       │     │
│  │ [?] Sind meine Daten sicher?                         │     │
│  │     → Ja. DSGVO-konform, hosted in Deutschland,      │     │
│  │       SSL-verschlüsselt.                             │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐     │
│  │            Bereit, Zeit zu sparen?                    │     │
│  │                                                       │     │
│  │  Starten Sie heute Ihre 14-tägige kostenlose Testph. │     │
│  │  Keine Kreditkarte erforderlich. Jederzeit kündbar.  │     │
│  │                                                       │     │
│  │       [Jetzt kostenlos testen (14 Tage)]             │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                │
│  Footer:                                                       │
│  Über uns | Kontakt | Datenschutz | AGB | Impressum           │
│  © 2025 PMS-Webapp. Alle Rechte vorbehalten.                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

### 7.2 Copywriting (Deutsch, professionell)

**Headline:**
```
Transparente Preise. Jederzeit kündbar.
```

**Subheadline:**
```
Wählen Sie den Plan, der zu Ihrer Agentur passt. Alle Pläne inkl. 14 Tage kostenlosem Test.
```

**Pricing-Cards:**

**Starter:**
```
Starter
€49/Monat
€39/Monat (bei jährlicher Zahlung)

Perfekt für kleine Agenturen

✅ Bis zu 20 Eigenschaften
✅ Unbegrenzte Buchungen
✅ 1 Kanal (Airbnb oder Booking.com)
✅ 3 Team-Mitglieder
✅ Basis-Berichte (Occupancy, Revenue)
✅ Email-Support (48h Response)

[Jetzt kostenlos testen]
```

**Professional (BELIEBT):**
```
Professional ★ BELIEBT
€149/Monat
€119/Monat (bei jährlicher Zahlung)

Ideal für mittelgroße Agenturen

✅ Bis zu 100 Eigenschaften
✅ Unbegrenzte Buchungen
✅ Alle Kanäle (Airbnb, Booking.com, Expedia, Direct)
✅ 10 Team-Mitglieder
✅ Advanced Reports (Custom, Export)
✅ Priority Support (24h Response)
✅ Eigentümer-Portal (Read-Only)

[Jetzt kostenlos testen]
```

**Enterprise:**
```
Enterprise
Custom Pricing
Ab €499/Monat

Für große Agenturen mit speziellen Anforderungen

✅ Unbegrenzte Eigenschaften
✅ Unbegrenzte Buchungen
✅ Alle Kanäle + Custom Integrationen
✅ Unbegrenzte Team-Mitglieder
✅ White-Label Branding
✅ API-Zugang
✅ Dedicated Account Manager
✅ Phone & Priority Support (4h Response)

[Kontakt aufnehmen]
```

**Trust-Elemente:**
```
✅ 14 Tage kostenlos testen
✅ Keine Kreditkarte erforderlich
✅ Jederzeit kündbar. Keine Vertragsbindung.
✅ DSGVO-konform. Daten in Deutschland.
```

**FAQ:**

**Was passiert nach dem Trial?**
```
Nach 14 Tagen entscheiden Sie selbst, ob Sie weitermachen möchten. Es gibt keine
automatische Abbuchung. Sie wählen einen Plan und hinterlegen Ihre Zahlungsmethode.
```

**Kann ich jederzeit kündigen?**
```
Ja. Bei monatlicher Zahlung können Sie jederzeit kündigen. Bei jährlicher Zahlung
gilt eine 12-monatige Mindestlaufzeit (mit 20% Rabatt).
```

**Welche Zahlungsmethoden akzeptieren Sie?**
```
Kreditkarte (Visa, Mastercard, Amex), SEPA-Lastschrift (EU), Rechnung (nur Enterprise).
```

**Sind meine Daten sicher?**
```
Ja. DSGVO-konform, hosted in Deutschland (Supabase EU), SSL-verschlüsselt.
```

**Was ist mit Gäste-Zahlungen?**
```
PMS-Webapp wickelt KEINE Gäste-Zahlungen ab. Sie nutzen externe Payment-Provider
(Stripe, PayPal) für Direct Bookings. Airbnb/Booking.com-Zahlungen laufen über
diese Plattformen.
```

**Final CTA:**
```
Bereit, Zeit zu sparen?

Starten Sie heute Ihre 14-tägige kostenlose Testphase.
Keine Kreditkarte erforderlich. Jederzeit kündbar.

[Jetzt kostenlos testen (14 Tage)]
```

---

## 8. Klarstellung: Agentur zahlt, Gäste NICHT

### 8.1 Zahlungsflüsse (Klarstellung)

**PMS-Webapp (unsere Software):**
- **WER ZAHLT:** Agentur (monatlich oder jährlich)
- **FÜR WAS:** Software-Nutzung (Subscription)
- **WIE VIEL:** €49-499/Monat (je nach Tier)
- **PAYMENT METHOD:** Kreditkarte, SEPA-Lastschrift, Rechnung (Enterprise)

**Gäste-Buchungen (NICHT unsere Software):**
- **WER ZAHLT:** Gast (bucht Ferienwohnung)
- **FÜR WAS:** Unterkunft
- **AN WEN:** Agentur (über Airbnb, Booking.com, oder Direct)
- **DURCH WAS:** Airbnb-Payment, Booking.com-Payment, Stripe (Direct Bookings)

**Wichtig:**
- ❌ PMS-Webapp wickelt KEINE Gäste-Zahlungen ab
- ❌ PMS-Webapp nimmt KEINE Provision auf Buchungen
- ✅ PMS-Webapp ist nur eine Verwaltungs-Software (B2B)
- ✅ Agenturen zahlen feste Software-Gebühr (Flat-Rate)

---

### 8.2 Unterschied zu Airbnb/Booking.com

**Airbnb/Booking.com:**
- **Geschäftsmodell:** Provision auf jede Buchung (15-20%)
- **Payment:** Gast zahlt über Airbnb → Airbnb zahlt Agentur (minus Provision)
- **Kosten:** 15-20% des Buchungsumsatzes

**PMS-Webapp:**
- **Geschäftsmodell:** Software-Subscription (Flat-Rate)
- **Payment:** Agentur zahlt Software-Gebühr (€49-499/Monat)
- **Kosten:** Fixe monatliche Kosten (unabhängig von Umsatz)

**Vorteil für Agentur:**
- Planbare Kosten (kein % auf Umsatz)
- Keine Provision (100% des Umsatzes bleibt bei Agentur)
- Fair Pricing (Wachstum wird nicht bestraft)

**Beispiel-Rechnung (50 Objekte, 100 Buchungen/Monat, €150/Buchung):**

**Ohne PMS-Webapp (nur Airbnb/Booking.com):**
- Umsatz: 100 × €150 = €15.000/Monat
- Airbnb-Provision (15%): €2.250/Monat
- Netto-Umsatz: €12.750/Monat

**Mit PMS-Webapp (Airbnb + Direct Bookings):**
- Umsatz: 100 × €150 = €15.000/Monat
- Airbnb-Provision (15% auf 50 Buchungen): €1.125/Monat
- Direct Bookings (50 Buchungen, 0% Provision): €7.500/Monat
- PMS-Webapp-Gebühr: €149/Monat
- Netto-Umsatz: €13.726/Monat
- **Ersparnis: €976/Monat** (vs. nur Airbnb)

---

## 9. Zusammenfassung & Nächste Schritte

### 9.1 Wichtigste Entscheidungen

**Pricing-Strategie:**
- Flat-Rate Subscription (KEINE Provision)
- 3 Tiers (Starter €49, Professional €149, Enterprise Custom)
- Monatlich oder Jährlich (20% Rabatt)
- 14 Tage Trial (ohne Kreditkarte)

**Competitor Analysis:**
- 50-90% günstiger als Guesty/Hostaway
- Teurer als Beds24 (aber modernere Features)
- Transparenter als Konkurrenz (keine versteckten Fees)

**Trial & Onboarding:**
- 14 Tage Trial (Professional Tier)
- Conversion-Flow (5 E-Mails über 14 Tage)
- Ziel: 40% Trial-to-Paid Conversion

**Billing-System:**
- Stripe Subscriptions
- Automatische Rechnungen (Deutsch, DSGVO-konform)
- Dunning Management (Tag 1-90)
- Upgrade/Downgrade (Prorated Billing)

**Pricing-Page:**
- 3 Pricing-Cards (Starter, Professional, Enterprise)
- Feature-Matrix (Tier × Feature)
- FAQ (5 Fragen)
- Trust-Elemente (14 Tage Trial, DSGVO)

---

### 9.2 Nächste Schritte (Implementierung)

**Phase 15: Stripe-Integration (Backend)**
1. Stripe Account Setup (Test + Live Mode)
2. Produkte & Preise konfigurieren (Starter, Professional, Enterprise)
3. Stripe Checkout implementieren (Hosted Payment Page)
4. Stripe Subscriptions (Create, Update, Cancel)
5. Webhooks (Payment Success, Payment Failed, Subscription Updated)
6. Invoicing (Automatische Rechnungen, E-Mail-Versand)

**Phase 16: Pricing-Page (Frontend)**
1. Pricing-Page-Design (basierend auf Wireframe)
2. Pricing-Cards (3 Tiers)
3. Feature-Matrix (Responsive Table)
4. FAQ (Accordion)
5. Trust-Elemente (Badges, Testimonials)
6. CTA (Jetzt testen, Kontakt)

**Phase 17: Trial & Onboarding (Frontend + Backend)**
1. Trial-Signup-Flow (E-Mail, Passwort, Agentur-Name)
2. Setup-Wizard (3 Schritte: Eigenschaft, Airbnb, Team)
3. E-Mail-Kampagne (5 E-Mails über 14 Tage)
4. Trial-to-Paid Conversion (Upgrade-Flow)
5. Onboarding-Call-Booking (Calendly-Integration)

**Phase 18: Billing-Dashboard (Frontend)**
1. Rechnungs-Historie (Liste aller Rechnungen)
2. Aktuelle Subscription (Tier, Preis, Kündigungsdatum)
3. Upgrade/Downgrade-Flow (Tier wechseln)
4. Zahlungsmethode verwalten (Stripe Customer Portal)
5. Kündigung (Self-Service)

---

## Anhang: Pricing-Kalkulation (Intern)

### A.1 Kosten-Struktur (PMS-Webapp)

**Fixe Kosten (pro Monat):**
- Hosting (Vercel): €20/Monat (MVP)
- Datenbank (Supabase): €25/Monat (MVP)
- Stripe Fees: 1.4% + €0.25 pro Transaktion (EU)
- Support-Tools (Intercom, Zendesk): €50/Monat
- E-Mail (SendGrid): €15/Monat
- **Gesamt:** €110/Monat (ohne Personal)

**Variable Kosten (pro Customer):**
- Stripe Fee (€149 Subscription): €2.36 pro Monat
- Datenbank (pro Customer): ~€0.50 pro Monat
- **Gesamt:** €2.86 pro Customer/Monat

**Break-Even (ohne Personal):**
- Fixe Kosten: €110/Monat
- Variable Kosten: €2.86/Customer
- Professional Tier: €149/Monat
- Netto pro Customer: €149 - €2.86 = €146.14
- Break-Even: €110 / €146.14 = **0.75 Customers** (1 Customer genügt)

**Mit Personal (1 Entwickler + 1 Support, Teilzeit):**
- Personal: €5.000/Monat
- Fixe Kosten: €110/Monat
- Gesamt: €5.110/Monat
- Break-Even: €5.110 / €146.14 = **35 Customers (Professional Tier)**

**Revenue-Ziele:**
- Jahr 1: 50 Customers → €7.450/Monat → €89.400/Jahr
- Jahr 2: 200 Customers → €29.800/Monat → €357.600/Jahr
- Jahr 3: 500 Customers → €74.500/Monat → €894.000/Jahr

---

### A.2 Pricing-Sensitivität (A/B-Tests)

**Hypothesen für Pricing-Optimierung:**

**1. Starter-Preis:**
- Aktuell: €49/Monat
- Test: €39/Monat vs. €59/Monat
- Hypothese: €39 erhöht Conversion, €59 senkt Conversion (aber höherer Revenue)

**2. Professional-Preis:**
- Aktuell: €149/Monat
- Test: €129/Monat vs. €169/Monat
- Hypothese: €129 erhöht Conversion von Trial → Paid

**3. Jährlicher Rabatt:**
- Aktuell: 20% Rabatt
- Test: 15% vs. 25% Rabatt
- Hypothese: 25% erhöht jährliche Subscriptions (höhere Customer Lifetime Value)

**4. Trial-Dauer:**
- Aktuell: 14 Tage
- Test: 7 Tage vs. 30 Tage
- Hypothese: 30 Tage erhöht Conversion (User hat mehr Zeit zum Testen)

---

## Quellen

**Competitor Analysis:**
- [Guesty Pricing auf GetApp](https://www.getapp.com/hospitality-travel-software/a/guesty/pricing/)
- [Hostaway Pricing Guide](https://www.hostaway.com/pricing/)
- [Beds24 Pricing](https://beds24.com/pricing.html)

**Basis-Dokumente (READ-ONLY):**
- Phase 10A: UI/UX & Design System (Konzeption)
- Phase 10B/10C: Visuelles Design-System & White-Label-UX
- Phase 11-13: Agentur-First Positionierung, Landing & RBAC

---

**Ende des Dokuments.**
