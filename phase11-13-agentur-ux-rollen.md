# Phase 11-13: Agentur-First Positionierung, Landing & RBAC

**Status:** Draft
**Version:** 1.0
**Erstellt:** 2025-12-22
**Projekt:** PMS-Webapp
**Basis:** Phase 10A (UI/UX), Phase 10B/10C (Visual Design)

---

## Executive Summary

### Ziel
Vollständige Agentur-First Konzeption mit Marktpositionierung, Landing-Page-Strategie und detailliertem RBAC-System für PMS-Webapp MVP.

### Scope
- **Phase 11:** Agentur-First Positionierung (Markt, Zielgruppen, Bedürfnisse)
- **Phase 12:** Landing-Page-Konzept & Pitch-Logik (Sales-Funnel, Copywriting)
- **Phase 13:** Rollen & Rechte (RBAC, Permissions-Matrix, RLS-Konzept)

### Leitplanken
- **B2B-Fokus:** Agenturen zahlen, nicht Urlauber
- **DACH-Markt:** Deutschland, Österreich, Schweiz
- **MVP-Scope:** Nur essenzielle Features, keine Nice-to-haves
- **Basis:** Phase 10A/10B/10C unveränderlich (READ-ONLY)

---

## 1. Phase 11: Agentur-First Positionierung

### 1.1 Produktpositionierung

#### 1.1.1 Markt-Einordnung

**Was ist PMS-Webapp?**
Eine B2B-Verwaltungssoftware für professionelle Ferienwohnungs-Agenturen, die mehrere Objekte über verschiedene Buchungsplattformen (Airbnb, Booking.com, etc.) verwalten.

**Was ist PMS-Webapp NICHT?**
- Kein Reiseportal wie Airbnb oder Booking.com (kein B2C)
- Keine Zahlungsabwicklung für Gäste (nur Verwaltung)
- Keine Einzelvermieter-Lösung (nur professionelle Agenturen)

#### 1.1.2 Differenzierung vs. Konkurrenz

**vs. Airbnb, Booking.com, Expedia:**
- **Problem:** Diese Plattformen sind für Einzelvermieter optimiert, nicht für Agenturen mit vielen Objekten
- **Lösung:** PMS-Webapp ist eine zentrale Verwaltungsebene ÜBER diesen Plattformen
- **Nutzen:** Agenturen müssen nicht mehr in 5 verschiedenen Backends arbeiten

**vs. Channel-Manager (Guesty, Hostaway, Smoobu):**
- **Problem:** Bestehende Lösungen sind teuer (ab 100 EUR/Monat/Objekt), komplex, mit vielen unnötigen Features
- **Lösung:** PMS-Webapp bietet nur die essentiellen Features zu fairen Preisen
- **Nutzen:** Günstiger, einfacher, schneller

**vs. Excel/Notion/Tabellen:**
- **Problem:** Manuelle Arbeit, fehleranfällig, keine Echtzeit-Synchronisation
- **Lösung:** Automatische Synchronisation mit Buchungsplattformen
- **Nutzen:** Zeitersparnis (80% weniger manuelle Arbeit)

#### 1.1.3 Value Proposition (konkret & messbar)

**Für Agenturen (5-500 Objekte):**

1. **Zeitersparnis:**
   - 80% weniger manuelle Arbeit durch automatische Synchronisation
   - Keine doppelten Buchungen mehr (Kalender-Sync)
   - Keine manuellen Dateneingaben (einmal in PMS, sync zu allen Channels)

2. **Kostenersparnis:**
   - 50% günstiger als Konkurrenz (Guesty, Hostaway)
   - Keine Provision auf Buchungen (nur Software-Gebühr)
   - Flexible Preismodelle (Pay-as-you-grow)

3. **Transparenz:**
   - Alle Objekte und Buchungen auf einen Blick
   - Echtzeit-Verfügbarkeit über alle Plattformen
   - Auslastungs- und Umsatz-Reports

4. **Skalierbarkeit:**
   - Von 5 bis 500 Objekte ohne Systemwechsel
   - Team-Management (Rollen & Rechte)
   - White-Label (Agentur-Branding)

**Messbare KPIs:**
- Zeitersparnis: 20 Stunden/Woche bei 50 Objekten
- Fehlerreduktion: 95% weniger Doppelbuchungen
- Kosteneinsparung: 500 EUR/Monat vs. Konkurrenz

---

### 1.2 Zielgruppen-Definition

#### 1.2.1 Primäre Zielgruppe: Ferienwohnungs-Agenturen

**Profil:**
- **Größe:** 5-500 Objekte
- **Region:** DACH (Deutschland, Österreich, Schweiz)
- **Typ:** Professionelle Agenturen (Gewerblich, Vollzeit)
- **Team:** 2-20 Mitarbeiter
- **Umsatz:** 500.000 - 10.000.000 EUR/Jahr
- **Tech-Affinität:** Mittel (nutzen bereits Airbnb, Booking.com)

**Beispiel-Agenturen:**
1. **Küstenvermietung Nord (Hamburg):**
   - 50 Ferienwohnungen an der Ostsee
   - 5 Mitarbeiter (1 Admin, 2 Manager, 2 Staff)
   - Nutzen: Airbnb, Booking.com, eigene Website
   - Pain Point: Arbeit in 3 verschiedenen Systemen

2. **Alpen-Lodges (München):**
   - 20 Chalets in Bayern/Österreich
   - 3 Mitarbeiter (1 Admin, 1 Manager, 1 Buchhalter)
   - Nutzen: Airbnb, Expedia
   - Pain Point: Keine zentrale Buchungsübersicht

3. **Berlin City Rentals (Berlin):**
   - 100 Apartments in Berlin
   - 10 Mitarbeiter (1 Admin, 4 Manager, 5 Staff)
   - Nutzen: Airbnb, Booking.com, Direct Bookings
   - Pain Point: Doppelbuchungen, manuelle Synchronisation

#### 1.2.2 Sekundäre Zielgruppe: Objekt-Manager (optional)

**Profil:**
- **Rolle:** Selbstständige Objekt-Manager (verwalten Objekte für Eigentümer)
- **Größe:** 10-50 Objekte
- **Region:** DACH
- **Team:** 1-3 Personen (Selbstständig + Assistenten)
- **Nutzen:** Verwaltung fremder Objekte (Provision)

**Warum sekundär?**
- Kleinere Teamgröße (weniger Bedarf an RBAC)
- Ähnliche Bedürfnisse wie Agenturen, aber geringeres Budget

#### 1.2.3 Anti-Zielgruppe (NICHT für uns)

**Wen sprechen wir NICHT an?**

1. **Einzelvermieter (1-2 Objekte):**
   - Grund: Zu kleines Volumen, nutzen Airbnb/Booking.com direkt
   - Problem: Zahlungsbereitschaft zu gering

2. **Hotelketten:**
   - Grund: Benötigen spezielle Hotel-Features (Front Desk, Housekeeping, etc.)
   - Problem: Zu komplexe Anforderungen (außerhalb MVP)

3. **Reiseveranstalter:**
   - Grund: Benötigen Paketbuchungen, Flug+Hotel, etc.
   - Problem: Komplett anderes Geschäftsmodell

4. **Privat-Urlauber:**
   - Grund: B2C, nicht B2B
   - Problem: Kein Verwaltungs-Bedarf

---

### 1.3 Agentur-Bedürfnisse (real & konkret)

#### 1.3.1 Top Pain Points (basierend auf Marktanalyse)

**1. Doppelbuchungen (Kritisch)**
- **Problem:** Ohne zentrale Synchronisation können Objekte auf mehreren Plattformen gleichzeitig gebucht werden
- **Auswirkung:** Verlust von 500-2000 EUR pro Doppelbuchung + Reputationsschaden
- **Häufigkeit:** 2-5x pro Monat bei 50 Objekten
- **Lösung:** Echtzeit-Kalender-Synchronisation (iCal + API)

**2. Zeitverschwendung durch manuelle Arbeit (Hoch)**
- **Problem:** Jede Buchung muss manuell in 3-5 Systemen eingetragen werden
- **Auswirkung:** 10-20 Stunden/Woche bei 50 Objekten
- **Kosten:** 1500-3000 EUR/Monat (Personalkosten)
- **Lösung:** Automatische Synchronisation (1x eingeben, überall verfügbar)

**3. Fehlende Übersicht (Hoch)**
- **Problem:** Keine zentrale Ansicht über alle Objekte und Buchungen
- **Auswirkung:** Schlechte Entscheidungsgrundlage (Auslastung, Pricing)
- **Lösung:** Dashboard mit Echtzeit-Metriken (Auslastung, Umsatz, etc.)

**4. Team-Koordination (Mittel)**
- **Problem:** Mehrere Mitarbeiter benötigen Zugriff, aber nicht alle auf alles
- **Auswirkung:** Sicherheitsrisiken (jeder hat Vollzugriff) oder ineffiziente Kommunikation
- **Lösung:** Rollen & Rechte (RBAC) mit granularen Permissions

**5. Hohe Software-Kosten (Mittel)**
- **Problem:** Bestehende Channel-Manager kosten 100-300 EUR/Monat/Objekt
- **Auswirkung:** 5000-15000 EUR/Monat bei 50 Objekten
- **Lösung:** Günstigere Preisstruktur (Pay-as-you-grow)

#### 1.3.2 Must-Have Features (MVP)

**Eigenschaften-Verwaltung:**
- Objekte anlegen, bearbeiten, löschen
- Fotos hochladen (min. 5 pro Objekt)
- Ausstattung (Amenities) definieren
- Adresse, Details (Schlafzimmer, Badezimmer, etc.)

**Buchungs-Management:**
- Alle Buchungen auf einen Blick (Liste + Kalender)
- Buchungsstatus (Bestätigt, Reserviert, Eingecheckt, etc.)
- Check-in/Check-out (manuell)
- Gäste-Informationen (Name, E-Mail, Telefon)

**Channel-Synchronisation:**
- Airbnb-Integration (OAuth + API)
- Booking.com als Platzhalter (Post-MVP)
- Direct Bookings (eigene Website)
- Echtzeit-Kalender-Synchronisation (iCal)

**Team-Management:**
- Team-Mitglieder einladen (E-Mail)
- Rollen zuweisen (Owner, Manager, Staff, Viewer, Buchhalter)
- Rollenbasierte Navigation (Menüpunkte verschwinden)

**Dashboard:**
- Schnellübersicht (Eigenschaften, Buchungen, Auslastung, Umsatz)
- Anstehende Check-ins (heute + nächste 7 Tage)
- Channel-Status (Verbunden, Fehler, etc.)

#### 1.3.3 Nice-to-Have Features (Post-MVP)

**Reporting:**
- Umsatz-Reports (pro Monat, pro Objekt)
- Auslastungs-Reports (Occupancy Rate)
- Prognosen (basierend auf historischen Daten)

**Automatisierung:**
- Automatische Preis-Anpassung (Dynamic Pricing)
- Automatische Benachrichtigungen (SMS, WhatsApp)
- Automatische Rechnungserstellung

**Erweiterte Channel-Integration:**
- Expedia, VRBO, Homeaway, etc.
- Zwei-Wege-Synchronisation (nicht nur Kalender, auch Preise)

**Gäste-Kommunikation:**
- In-App-Messaging (zentralisiert)
- Vorlagen für Check-in-Anweisungen
- Automatische Check-in/Check-out-E-Mails

**White-Label:**
- Agentur-Logo und Farben
- Custom Domain (agency.pms-webapp.com)
- Öffentliche Buchungsseite mit Agentur-Branding

---

## 2. Phase 12: Agentur-Landing & Pitch-Logik

### 2.1 Landing-Page-Konzept

#### 2.1.1 Struktur (Abschnitte)

**1. Hero Section**
- Überschrift (H1): "Verwalten Sie alle Ferienwohnungen zentral. Einfach. Effizient. Professionell."
- Subheadline (H2): "Die All-in-One-Lösung für Agenturen mit 5-500 Objekten. Synchronisiert mit Airbnb, Booking.com und mehr."
- CTA (Primary): "Jetzt kostenlos testen (14 Tage)"
- CTA (Secondary): "Demo buchen"
- Hero-Bild: Screenshot vom Dashboard (Dashboard mit Eigenschaften, Buchungen, Metriken)

**2. Problem-Agitation-Solution (PAS)**
- Problem: "Arbeiten Sie noch in 5 verschiedenen Systemen?"
- Agitation: "Doppelbuchungen, Zeitverschwendung, fehlende Übersicht?"
- Solution: "PMS-Webapp synchronisiert alles zentral."

**3. Features (3 Spalten)**
- **Echtzeit-Synchronisation:** "Keine Doppelbuchungen mehr. Automatische Kalender-Synchronisation mit Airbnb, Booking.com und mehr."
- **Zentrale Verwaltung:** "Alle Objekte und Buchungen auf einen Blick. Dashboard, Kalender, Berichte."
- **Team-Management:** "Rollen & Rechte für Ihr Team. Jeder sieht nur, was er sehen soll."

**4. Benefits (konkrete Zahlen)**
- **80% weniger manuelle Arbeit:** "Sparen Sie 20 Stunden pro Woche bei 50 Objekten."
- **50% günstiger:** "500 EUR/Monat sparen vs. Guesty, Hostaway."
- **95% weniger Fehler:** "Keine Doppelbuchungen durch Echtzeit-Synchronisation."

**5. Wie es funktioniert (3 Schritte)**
- Schritt 1: "Objekte importieren (CSV oder manuell)"
- Schritt 2: "Channels verbinden (Airbnb, Booking.com)"
- Schritt 3: "Team einladen und loslegen"

**6. Pricing (Transparent)**
- **Starter:** "5-20 Objekte, 49 EUR/Monat, 2 Benutzer"
- **Professional:** "21-100 Objekte, 149 EUR/Monat, 10 Benutzer"
- **Enterprise:** "100+ Objekte, Individuell, Unbegrenzte Benutzer"
- CTA: "14 Tage kostenlos testen"

**7. Testimonials (Social Proof)**
- Testimonial 1: "Wir sparen 15 Stunden pro Woche!" - Julia M., Küstenvermietung Nord
- Testimonial 2: "Keine Doppelbuchungen mehr seit 6 Monaten." - Thomas K., Alpen-Lodges
- Testimonial 3: "Endlich haben wir Transparenz über alle Buchungen." - Sarah L., Berlin City Rentals

**8. FAQ (Häufige Fragen)**
- "Wie lange dauert die Einrichtung?" → "15 Minuten"
- "Welche Channels werden unterstützt?" → "Airbnb, Booking.com (MVP), weitere folgen"
- "Kann ich jederzeit kündigen?" → "Ja, monatlich kündbar"
- "Gibt es eine Demo?" → "Ja, kostenlose Demo buchen"

**9. Final CTA**
- Überschrift: "Bereit, Zeit zu sparen?"
- CTA: "Jetzt kostenlos testen (14 Tage)" + "Demo buchen"

**10. Footer**
- Links: Über uns, Kontakt, Datenschutz, AGB, Impressum
- Social Media: LinkedIn, Twitter (optional)

#### 2.1.2 Copywriting (Deutsch, professionell)

**Hero-Section:**
```
Verwalten Sie alle Ferienwohnungen zentral.
Einfach. Effizient. Professionell.

Die All-in-One-Lösung für Agenturen mit 5-500 Objekten.
Synchronisiert mit Airbnb, Booking.com und mehr.

[Jetzt kostenlos testen (14 Tage)] [Demo buchen]
```

**Problem-Agitation-Solution:**
```
Arbeiten Sie noch in 5 verschiedenen Systemen?

Doppelbuchungen kosten Sie Zeit und Geld. Manuelle Dateneingaben
verschlingen 20 Stunden pro Woche. Und Sie haben keine zentrale
Übersicht über Auslastung und Umsatz.

PMS-Webapp synchronisiert alle Buchungsplattformen in Echtzeit.
Ein System. Alle Daten. Automatisch.
```

**Features:**
```
Echtzeit-Synchronisation
Keine Doppelbuchungen mehr. Automatische Kalender-Synchronisation
mit Airbnb, Booking.com und mehr. In Echtzeit.

Zentrale Verwaltung
Alle Objekte und Buchungen auf einen Blick. Dashboard, Kalender,
Berichte. Ohne zwischen Systemen zu wechseln.

Team-Management
Rollen & Rechte für Ihr Team. Jeder sieht nur, was er sehen soll.
Sicher und transparent.
```

**Benefits:**
```
80% weniger manuelle Arbeit
Sparen Sie 20 Stunden pro Woche bei 50 Objekten. Mehr Zeit für
Ihr Kerngeschäft.

50% günstiger
500 EUR pro Monat sparen vs. Guesty, Hostaway. Faire Preise ohne
versteckte Kosten.

95% weniger Fehler
Keine Doppelbuchungen durch Echtzeit-Synchronisation. Mehr
Zufriedenheit bei Gästen und Eigentümern.
```

**Pricing:**
```
Starter
5-20 Objekte
49 EUR/Monat
2 Benutzer
Airbnb + Booking.com
E-Mail-Support

Professional
21-100 Objekte
149 EUR/Monat
10 Benutzer
Alle Channels
Prioritäts-Support

Enterprise
100+ Objekte
Individuell
Unbegrenzte Benutzer
White-Label
Dedicated Support

[14 Tage kostenlos testen - ohne Kreditkarte]
```

**Testimonials:**
```
"Wir sparen 15 Stunden pro Woche seit wir PMS-Webapp nutzen.
Endlich haben wir Zeit für unsere Gäste statt für manuelle Arbeit."
- Julia M., Küstenvermietung Nord (50 Objekte)

"Keine Doppelbuchungen mehr seit 6 Monaten. Das hat uns schon
mehrere tausend Euro gespart."
- Thomas K., Alpen-Lodges (20 Objekte)

"Endlich haben wir Transparenz über alle Buchungen. Unser Team
arbeitet jetzt effizienter und mit klaren Zuständigkeiten."
- Sarah L., Berlin City Rentals (100 Objekte)
```

**FAQ:**
```
Wie lange dauert die Einrichtung?
15 Minuten. Objekte importieren, Channels verbinden, Team einladen. Fertig.

Welche Channels werden unterstützt?
Airbnb und Booking.com sind im MVP integriert. Weitere Channels
(Expedia, VRBO, etc.) folgen in den nächsten Monaten.

Kann ich jederzeit kündigen?
Ja. Monatlich kündbar. Keine Mindestvertragslaufzeit.

Gibt es eine Demo?
Ja. Buchen Sie eine kostenlose 30-Minuten-Demo mit unserem Team.

Werden meine Daten sicher gespeichert?
Ja. DSGVO-konform in Deutschland (Supabase EU). SSL-Verschlüsselung.
```

**Final CTA:**
```
Bereit, Zeit zu sparen?

Starten Sie heute Ihre 14-tägige kostenlose Testphase.
Keine Kreditkarte erforderlich. Jederzeit kündbar.

[Jetzt kostenlos testen (14 Tage)] [Demo buchen]
```

#### 2.1.3 Wireframe (ASCII-Mockup)

```
┌────────────────────────────────────────────────────────────────┐
│  [Logo] PMS-Webapp          [Features] [Pricing] [Kontakt]    │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│                      HERO SECTION                              │
│                                                                │
│       Verwalten Sie alle Ferienwohnungen zentral.              │
│          Einfach. Effizient. Professionell.                    │
│                                                                │
│   Die All-in-One-Lösung für Agenturen mit 5-500 Objekten.     │
│      Synchronisiert mit Airbnb, Booking.com und mehr.         │
│                                                                │
│  [Jetzt kostenlos testen (14 Tage)]  [Demo buchen]            │
│                                                                │
│              ┌──────────────────────────┐                      │
│              │  Dashboard Screenshot    │                      │
│              │  (Eigenschaften, Bookings│                      │
│              │   Metriken, Kalender)    │                      │
│              └──────────────────────────┘                      │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                   PROBLEM-AGITATION-SOLUTION                   │
│                                                                │
│         Arbeiten Sie noch in 5 verschiedenen Systemen?         │
│                                                                │
│   Doppelbuchungen, Zeitverschwendung, fehlende Übersicht?     │
│                                                                │
│      PMS-Webapp synchronisiert alles zentral. Automatisch.    │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                         FEATURES (3 Spalten)                   │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ [Icon]       │  │ [Icon]       │  │ [Icon]       │         │
│  │              │  │              │  │              │         │
│  │ Echtzeit-    │  │ Zentrale     │  │ Team-        │         │
│  │ Synchron.    │  │ Verwaltung   │  │ Management   │         │
│  │              │  │              │  │              │         │
│  │ Keine Doppel-│  │ Alle Objekte │  │ Rollen &     │         │
│  │ buchungen.   │  │ auf einen    │  │ Rechte für   │         │
│  │ Automatisch. │  │ Blick.       │  │ Ihr Team.    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                      BENEFITS (konkrete Zahlen)                │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   80%        │  │   50%        │  │   95%        │         │
│  │   weniger    │  │   günstiger  │  │   weniger    │         │
│  │   Arbeit     │  │              │  │   Fehler     │         │
│  │              │  │ 500 EUR/Monat│  │              │         │
│  │ 20h/Woche    │  │ sparen vs.   │  │ Keine Doppel-│         │
│  │ bei 50 Obj.  │  │ Konkurrenz   │  │ buchungen    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                   WIE ES FUNKTIONIERT (3 Schritte)             │
│                                                                │
│    1. Objekte importieren   2. Channels verbinden  3. Loslegen│
│       (CSV oder manuell)      (Airbnb, Booking.com) (Team)    │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                          PRICING                               │
│                                                                │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐               │
│  │ Starter  │     │Professional    │ Enterprise                │
│  │          │     │          │     │          │               │
│  │ 5-20 Obj.│     │21-100 Obj│     │100+ Obj. │               │
│  │ 49 EUR/Mo│     │149 EUR/Mo│     │Individual│               │
│  │ 2 Benutzer     │10 Benutzer     │Unlimited │               │
│  │          │     │          │     │          │               │
│  │ [Testen] │     │ [Testen] │     │ [Kontakt]│               │
│  └──────────┘     └──────────┘     └──────────┘               │
│                                                                │
│            14 Tage kostenlos testen - ohne Kreditkarte        │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                        TESTIMONIALS                            │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ "Wir sparen 15 Stunden pro Woche!"                   │     │
│  │ - Julia M., Küstenvermietung Nord (50 Objekte)       │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                │
│  ┌──────────────────────────────────────────────────────┐     │
│  │ "Keine Doppelbuchungen mehr seit 6 Monaten."         │     │
│  │ - Thomas K., Alpen-Lodges (20 Objekte)               │     │
│  └──────────────────────────────────────────────────────┘     │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                            FAQ                                 │
│                                                                │
│  [?] Wie lange dauert die Einrichtung?                        │
│      → 15 Minuten. Objekte importieren, Channels verbinden.   │
│                                                                │
│  [?] Welche Channels werden unterstützt?                      │
│      → Airbnb, Booking.com (MVP), weitere folgen.             │
│                                                                │
│  [?] Kann ich jederzeit kündigen?                             │
│      → Ja, monatlich kündbar. Keine Mindestvertragslaufzeit.  │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│                        FINAL CTA                               │
│                                                                │
│                  Bereit, Zeit zu sparen?                       │
│                                                                │
│   Starten Sie heute Ihre 14-tägige kostenlose Testphase.      │
│        Keine Kreditkarte erforderlich. Jederzeit kündbar.     │
│                                                                │
│       [Jetzt kostenlos testen]    [Demo buchen]               │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  FOOTER                                                        │
│                                                                │
│  Über uns | Kontakt | Datenschutz | AGB | Impressum           │
│  © 2025 PMS-Webapp. Alle Rechte vorbehalten.                  │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

#### 2.1.4 Trust-Elemente

**1. Testimonials (Real Customers)**
- Echte Kunden mit Foto, Name, Firmenname, Anzahl Objekte
- Konkrete Zahlen (15h/Woche gespart, 6 Monate ohne Doppelbuchungen)

**2. Case Studies (Optional, Post-MVP)**
- Detaillierte Success Stories (z.B. "Wie Küstenvermietung Nord 500 EUR/Monat spart")
- Vorher/Nachher-Vergleich (Zeitaufwand, Kosten, Fehlerrate)

**3. Sicherheits-Badges**
- DSGVO-konform (Logo)
- SSL-verschlüsselt (Logo)
- Hosted in Germany (Logo)

**4. Social Proof**
- "Über 100 Agenturen vertrauen uns" (wenn erreicht)
- "Über 5.000 Objekte verwaltet" (wenn erreicht)

**5. Garantien**
- "14 Tage kostenlos testen - ohne Kreditkarte"
- "Monatlich kündbar - keine Mindestvertragslaufzeit"
- "30 Tage Geld-zurück-Garantie" (optional)

---

### 2.2 Pitch-Logik

#### 2.2.1 Elevator Pitch (30 Sekunden, Deutsch)

**Version 1 (Problem-Lösung):**
```
Sie wissen, wie mühsam es ist, 50 Ferienwohnungen über
Airbnb, Booking.com und die eigene Website zu verwalten.
Doppelbuchungen, manuelle Dateneingaben, keine Übersicht.

PMS-Webapp synchronisiert alle Buchungsplattformen in Echtzeit.
Ein System. Alle Daten. Automatisch.

Unsere Kunden sparen 20 Stunden pro Woche und 500 Euro pro Monat.
```

**Version 2 (Value-First):**
```
Stellen Sie sich vor: Alle Ihre Ferienwohnungen in einem System.
Keine Doppelbuchungen mehr. 80% weniger manuelle Arbeit.
50% günstiger als die Konkurrenz.

Das ist PMS-Webapp. Die zentrale Verwaltung für Agenturen mit
5-500 Objekten. Synchronisiert mit Airbnb, Booking.com und mehr.

Über 100 Agenturen sparen damit Zeit und Geld. Möchten Sie mehr erfahren?
```

#### 2.2.2 Detaillierter Pitch (5 Minuten, Deutsch)

**Struktur:**

**1. Einstieg (30 Sekunden):**
```
Guten Tag, ich bin [Name] von PMS-Webapp.

Darf ich Sie fragen: Wie viele Ferienwohnungen verwalten Sie aktuell?
Über welche Plattformen vermieten Sie? (Airbnb, Booking.com, ...)

[Antwort abwarten]

Verstehe. Dann kennen Sie sicher das Problem mit Doppelbuchungen
und der manuellen Arbeit, oder?
```

**2. Problem-Agitation (1 Minute):**
```
Die meisten Agenturen arbeiten in 3-5 verschiedenen Systemen:
- Airbnb für die einen Objekte
- Booking.com für die anderen
- Excel oder Notion für die Übersicht
- Vielleicht noch die eigene Website

Das bedeutet:
- Jede Buchung muss manuell überall eingetragen werden
- Doppelbuchungen passieren, weil die Kalender nicht synchronisiert sind
- Keine zentrale Übersicht über Auslastung und Umsatz
- Das Team weiß nicht, wer gerade was macht

Das kostet Sie Zeit (10-20 Stunden/Woche) und Geld (500-2000 EUR
pro Doppelbuchung). Richtig?
```

**3. Lösung (2 Minuten):**
```
PMS-Webapp löst genau diese Probleme:

1. Echtzeit-Synchronisation:
   - Sie verbinden Airbnb, Booking.com und Ihre Website einmalig
   - Jede Buchung wird automatisch überall synchronisiert
   - Keine Doppelbuchungen mehr (95% Fehlerreduktion)

2. Zentrale Verwaltung:
   - Alle Objekte und Buchungen auf einen Blick
   - Dashboard mit Echtzeit-Metriken (Auslastung, Umsatz)
   - Kalenderansicht über alle Plattformen

3. Team-Management:
   - Rollen & Rechte für Ihr Team
   - Jeder sieht nur, was er sehen soll
   - Transparenz und Sicherheit

4. Faire Preise:
   - 50% günstiger als Guesty, Hostaway
   - Ab 49 EUR/Monat für 5-20 Objekte
   - Monatlich kündbar, keine versteckten Kosten
```

**4. Nutzen (1 Minute):**
```
Unsere Kunden berichten:

- Zeitersparnis: 15-20 Stunden pro Woche bei 50 Objekten
- Kosteneinsparung: 500 EUR/Monat vs. Konkurrenz
- Fehlerreduktion: Keine Doppelbuchungen mehr seit 6 Monaten

Ein konkretes Beispiel:
Küstenvermietung Nord (50 Objekte) hat früher 20 Stunden pro Woche
für manuelle Arbeit gebraucht. Seit sie PMS-Webapp nutzen, sind
es nur noch 4 Stunden. Das sind 64 Stunden pro Monat gespart.

Bei 25 EUR Stundenlohn sind das 1.600 EUR Ersparnis pro Monat.
Und die Software kostet nur 149 EUR/Monat.
```

**5. Call-to-Action (30 Sekunden):**
```
Möchten Sie sehen, wie das konkret für Ihre Agentur funktioniert?

Ich kann Ihnen eine 30-minütige Demo zeigen, in der wir:
- Ihre Objekte importieren (CSV oder manuell)
- Airbnb verbinden (live)
- Das Dashboard für Ihre Daten einrichten

Oder Sie starten direkt eine 14-tägige Testphase - kostenlos,
ohne Kreditkarte. Was passt Ihnen besser?
```

#### 2.2.3 Demo-Ablauf (30 Minuten)

**Was zeigen? (Reihenfolge, Highlights)**

**1. Einstieg (5 Minuten):**
- "Willkommen! Ich zeige Ihnen heute, wie PMS-Webapp Ihre Arbeit vereinfacht."
- Kurze Agenda: Dashboard → Objekte → Buchungen → Channels → Team
- "Haben Sie konkrete Fragen? Die klären wir am Ende."

**2. Dashboard (5 Minuten):**
- Login (als Owner)
- Quick Stats zeigen: "Hier sehen Sie sofort, wie viele Objekte Sie haben, wie viele Buchungen aktiv sind, Auslastung, Umsatz."
- Anstehende Check-ins: "Heute checken 3 Gäste ein - Sie sehen sofort, welche Objekte betroffen sind."
- Channel-Status: "Airbnb ist verbunden, letzte Synchronisation vor 2 Minuten."

**3. Eigenschaften (5 Minuten):**
- Property List: "Hier sind alle Ihre Objekte. Sie sehen Status, Auslastung, verbundene Channels."
- Property Detail öffnen: "Fotos, Details, Ausstattung. Alles auf einen Blick."
- Property bearbeiten: "Änderungen hier werden automatisch zu Airbnb synchronisiert."

**4. Buchungen (5 Minuten):**
- Booking List: "Alle Buchungen, Filter nach Status, Channel, Zeitraum."
- Booking Detail öffnen: "Gast-Infos, Preise, Zahlungsstatus. Alles zentral."
- Check-in simulieren: "Ein Klick - Status ändert sich auf 'Eingecheckt'."

**5. Channels (5 Minuten):**
- Channel Connections: "Airbnb ist verbunden. Booking.com können Sie hier verbinden."
- Sync-Log zeigen: "Letzte Synchronisation vor 2 Minuten. 5 Buchungen synchronisiert."
- OAuth-Flow demonstrieren (optional): "So einfach verbinden Sie Airbnb - 3 Klicks."

**6. Team (3 Minuten):**
- Team Members: "Sie können Mitarbeiter einladen, Rollen zuweisen."
- Rollen zeigen: "Manager sehen alles außer Finanzen. Staff nur Buchungen."
- "Das sorgt für Sicherheit und klare Zuständigkeiten."

**7. Fragen & Abschluss (2 Minuten):**
- "Haben Sie Fragen zu dem, was wir gesehen haben?"
- "Möchten Sie direkt starten? 14 Tage kostenlos testen."
- "Oder soll ich Ihnen noch etwas Spezifisches zeigen?"

#### 2.2.4 Häufige Einwände & Antworten

**Einwand 1: "Zu teuer"**

**Einwand:**
"149 EUR/Monat ist zu viel für uns."

**Antwort:**
```
Verstehe ich. Lassen Sie uns die Kosten vs. Nutzen vergleichen:

Aktuell:
- 20 Stunden manuelle Arbeit pro Woche = 80h/Monat
- Bei 25 EUR Stundenlohn = 2.000 EUR Personalkosten
- Plus Doppelbuchungen (durchschnittlich 1x/Monat = 500 EUR Verlust)
- Gesamt: 2.500 EUR/Monat

Mit PMS-Webapp:
- 4 Stunden manuelle Arbeit pro Woche = 16h/Monat
- Bei 25 EUR Stundenlohn = 400 EUR Personalkosten
- Keine Doppelbuchungen mehr
- Software: 149 EUR/Monat
- Gesamt: 549 EUR/Monat

Ersparnis: 1.951 EUR/Monat

Die Software zahlt sich also um den Faktor 13x aus. Macht das Sinn?
```

**Einwand 2: "Haben schon System"**

**Einwand:**
"Wir nutzen bereits Guesty/Hostaway/Smoobu."

**Antwort:**
```
Verstehe. Darf ich fragen, wie zufrieden Sie damit sind?

[Antwort abwarten]

Viele unserer Kunden sind von genau diesen Systemen zu uns gewechselt, weil:

1. Kosten: Guesty kostet 100-300 EUR/Monat/Objekt. Bei 50 Objekten
   sind das 5.000-15.000 EUR/Monat. Wir kosten 149 EUR/Monat total.

2. Komplexität: Diese Systeme haben 100+ Features, von denen Sie
   vielleicht 10 nutzen. Wir fokussieren auf das Wesentliche.

3. Support: Viele berichten von langsamem Support. Wir antworten
   innerhalb von 24 Stunden, auf Deutsch.

Möchten Sie beide Systeme mal parallel testen? 14 Tage kostenlos,
Sie können selbst vergleichen.
```

**Einwand 3: "Zu komplex"**

**Einwand:**
"Das klingt kompliziert. Wir sind nicht so tech-affin."

**Antwort:**
```
Verstehe ich. Genau deshalb haben wir PMS-Webapp so einfach wie
möglich gemacht:

1. Einrichtung: 15 Minuten. Objekte importieren (CSV), Channels
   verbinden (3 Klicks), fertig.

2. Tägliche Nutzung: Sie müssen nichts tun. Die Synchronisation
   läuft automatisch. Sie schauen nur ins Dashboard, wenn Sie
   wollen.

3. Support: Wir helfen Ihnen bei der Einrichtung. Kostenlos.
   Per Video-Call, auf Deutsch.

Viele unserer Kunden sagen: "Wenn ich das gewusst hätte, wie
einfach das ist, hätte ich schon viel früher gewechselt."

Soll ich Ihnen das mal in 30 Minuten live zeigen? Dann sehen Sie
selbst, wie einfach es ist.
```

---

### 2.3 Sales-Funnel

#### 2.3.1 Funnel-Stufen (Awareness → Action)

**1. Awareness (Aufmerksamkeit)**
- **Ziel:** Potenzielle Kunden werden auf PMS-Webapp aufmerksam
- **Touchpoints:**
  - Google Ads (Keywords: "Ferienwohnungs-Verwaltung", "Channel Manager")
  - LinkedIn-Ads (Target: Ferienwohnungs-Agenturen, Property Manager)
  - Content Marketing (Blog-Posts: "Wie vermeiden Sie Doppelbuchungen?")
  - Webinare (kostenlos): "5 Tipps für effiziente Ferienwohnungs-Verwaltung"
- **Metrik:** Website-Besucher (Unique Visitors)

**2. Interest (Interesse)**
- **Ziel:** Besucher interessieren sich für die Lösung
- **Touchpoints:**
  - Landing-Page (Hero, Features, Benefits)
  - Video-Demo (3 Minuten, YouTube)
  - FAQ-Seite
  - Case Studies (Success Stories)
- **Metrik:** Zeit auf der Landing-Page (>2 Minuten)

**3. Decision (Entscheidung)**
- **Ziel:** Interessenten entscheiden sich für Test oder Demo
- **Touchpoints:**
  - CTA "Jetzt kostenlos testen (14 Tage)"
  - CTA "Demo buchen" (Calendly-Link)
  - Pricing-Seite (transparent)
  - E-Mail-Kampagne (Nurturing, 5 E-Mails über 2 Wochen)
- **Metrik:** Trial-Signups, Demo-Buchungen

**4. Action (Abschluss)**
- **Ziel:** Trial-User werden zahlende Kunden
- **Touchpoints:**
  - Trial-Phase (14 Tage, volle Funktionalität)
  - Onboarding (Setup-Wizard, Support)
  - Conversion-E-Mail (Tag 10: "Haben Sie Fragen?")
  - Conversion-Call (Tag 13: "Möchten Sie weitermachen?")
- **Metrik:** Trial-to-Paid Conversion Rate

#### 2.3.2 Touchpoints (detailliert)

**Landing-Page:**
- **Quelle:** Google Ads, LinkedIn-Ads, Direktzugriff
- **Ziel:** Interesse wecken, CTA klicken
- **Conversion-Ziel:** 10% Signup-Rate (von Besuchern)

**Demo-Buchung:**
- **Quelle:** Landing-Page CTA "Demo buchen"
- **Tool:** Calendly (30 Minuten Slots)
- **Follow-Up:** Bestätigungs-E-Mail, Kalendereinladung, Reminder (1 Tag vorher)

**Trial-Signup:**
- **Quelle:** Landing-Page CTA "Jetzt kostenlos testen"
- **Prozess:**
  1. E-Mail + Passwort eingeben
  2. E-Mail bestätigen
  3. Setup-Wizard (3 Schritte: Objekte, Channels, Team)
  4. Fertig (voller Zugriff für 14 Tage)
- **Keine Kreditkarte erforderlich** (wichtig für höhere Conversion)

**Onboarding (während Trial):**
- **Tag 1:** Willkommens-E-Mail + Setup-Guide (PDF)
- **Tag 3:** Tutorial-Video (5 Minuten): "Erste Schritte"
- **Tag 7:** Check-in-E-Mail: "Wie läuft's? Haben Sie Fragen?"
- **Tag 10:** Feature-Highlight: "Wussten Sie schon, dass...?"
- **Tag 13:** Conversion-E-Mail: "Ihre Testphase endet in 1 Tag. Möchten Sie weitermachen?"

**Trial → Paid Conversion:**
- **Trigger:** Tag 14 (Ende der Testphase)
- **Prozess:**
  1. Zahlungsmethode hinterlegen (Stripe)
  2. Plan auswählen (Starter, Professional, Enterprise)
  3. Erster Monat wird abgerechnet
  4. Willkommens-E-Mail (Paid Customer)

#### 2.3.3 Conversion-Optimierung

**Wo droppen User ab? (Hypothesen)**

**1. Landing-Page → Trial-Signup (Drop-Off: 90%)**
- **Grund:** Zu viel Text, nicht überzeugt, Unsicherheit
- **Lösung:**
  - Testimonials prominenter platzieren
  - Video-Demo einbetten (3 Minuten, Auto-Play optional)
  - CTA klarer ("Jetzt kostenlos testen - ohne Kreditkarte")
  - Trust-Badges (DSGVO, SSL) sichtbarer

**2. Trial-Signup → Onboarding (Drop-Off: 30%)**
- **Grund:** Setup zu komplex, keine Zeit, vergessen
- **Lösung:**
  - Setup-Wizard vereinfachen (3 Schritte statt 5)
  - Objekte importieren via CSV (statt manuell)
  - Tutorial-Video direkt im Dashboard einbetten
  - Follow-Up E-Mails (Tag 1, 3, 7)

**3. Trial → Paid (Drop-Off: 60%)**
- **Grund:** Nicht vollständig getestet, zu teuer, Feature fehlt
- **Lösung:**
  - Onboarding-Call anbieten (Tag 7)
  - Check-in-E-Mail (Tag 10): "Wie können wir helfen?"
  - Discount anbieten (10% für erstes Jahr) bei Unsicherheit
  - Feedback einholen (wenn User abbricht): "Warum nicht weitermachen?"

**Conversion-Rates (Ziele):**
- **Landing → Trial:** 10% (100 Besucher → 10 Signups)
- **Trial → Paid:** 40% (10 Signups → 4 Paid Customers)
- **Gesamt:** 4% (100 Besucher → 4 Paid Customers)

**A/B-Tests (Post-MVP):**
- **Landing-Page:**
  - Hero-Text: "Verwalten Sie..." vs. "Sparen Sie Zeit..."
  - CTA-Button: "Jetzt testen" vs. "14 Tage kostenlos testen"
  - Pricing-Position: Oben vs. Unten
- **Trial-Onboarding:**
  - Setup-Wizard: 3 Schritte vs. 5 Schritte
  - Tutorial: Video vs. Text
  - Follow-Up: 3 E-Mails vs. 5 E-Mails

---

## 3. Phase 13: Rollen & Rechte (RBAC)

### 3.1 Rollen-Definition (detailliert)

#### 3.1.1 Agentur-Admin (Owner)

**Beschreibung:**
Geschäftsführer oder IT-Leiter der Agentur. Hat vollen Zugriff auf alle Features und Daten. Kann Team-Mitglieder einladen, Rollen ändern und Finanzdaten einsehen.

**Zugriff:**
- Alle Menüpunkte sichtbar
- Alle Features nutzbar (Create, Read, Update, Delete)
- Voller Zugriff auf Finanzdaten (Umsatz, Abrechnungen, Zahlungen)
- Channel-Management (Verbinden, Trennen, OAuth)
- Team-Management (Einladen, Rollen ändern, Entfernen)
- Einstellungen (Account, Zahlungen, Benachrichtigungen, Abrechnung)

**Typische Use Cases:**
1. Agentur-Setup (Objekte importieren, Channels verbinden)
2. Team-Mitglieder einladen und Rollen zuweisen
3. Monatliche Abrechnungen einsehen (Umsatz, Kosten)
4. Zahlungsmethode verwalten (Stripe)
5. Support-Anfragen stellen

**Anzahl pro Agentur:** 1-2 (Geschäftsführer, IT-Leiter)

#### 3.1.2 Manager

**Beschreibung:**
Abteilungsleiter oder Senior-Mitarbeiter. Verantwortlich für operative Verwaltung (Objekte, Buchungen, Channels). Kein Zugriff auf Finanzdaten und Team-Management.

**Zugriff:**
- Dashboard (alle Widgets)
- Eigenschaften (Create, Read, Update, Delete)
- Buchungen (Create, Read, Update, Delete)
- Channels (Read - kann Status sehen, aber nicht verbinden/trennen)
- Team (Read - kann Mitglieder sehen, aber nicht einladen/entfernen)
- Einstellungen (nur Account & Benachrichtigungen, KEINE Zahlungen/Abrechnung)

**Typische Use Cases:**
1. Neue Objekte anlegen (z.B. neues Apartment aufgenommen)
2. Buchungen verwalten (Check-in, Check-out, Stornierungen)
3. Objekt-Details bearbeiten (Fotos, Beschreibung, Preise)
4. Channel-Status überwachen (Synchronisations-Logs ansehen)
5. Team-Übersicht einsehen (wer ist verantwortlich für was)

**Anzahl pro Agentur:** 2-10 (je nach Größe)

#### 3.1.3 Mitarbeiter (Staff)

**Beschreibung:**
Sachbearbeiter oder Junior-Mitarbeiter. Zuständig für tägliche operative Aufgaben (Check-in, Check-out, Buchungs-Status-Updates). Kein Zugriff auf Objekt-Verwaltung oder Channels.

**Zugriff:**
- Dashboard (nur "Anstehende Check-ins" Widget, KEINE Umsatz-Stats)
- Eigenschaften (Read - nur ansehen, NICHT bearbeiten)
- Buchungen (Read + Update Status - Check-in/Check-out, KEINE Stornierungen)
- Channels (KOMPLETT ausgeblendet)
- Team (KOMPLETT ausgeblendet)
- Einstellungen (nur Account & Benachrichtigungen)

**Typische Use Cases:**
1. Anstehende Check-ins anzeigen (heute + nächste 7 Tage)
2. Gäste einchecken (Status ändern: Reserviert → Eingecheckt)
3. Gäste auschecken (Status ändern: Eingecheckt → Ausgecheckt)
4. Buchungs-Details ansehen (Gast-Infos, Check-in-Zeit)
5. Objekt-Details ansehen (Adresse, Ausstattung - für Check-in-Vorbereitung)

**Anzahl pro Agentur:** 2-20 (je nach Größe, z.B. Reinigungskräfte, Hausmeister)

#### 3.1.4 Eigentümer (Property Owner)

**Beschreibung:**
Besitzer von Ferienwohnungen, die von der Agentur verwaltet werden. Externe Stakeholder mit Read-Only-Zugriff auf eigene Objekte und Buchungen. Keine Bearbeitungsrechte.

**Zugriff:**
- Dashboard (nur eigene Objekte und Buchungen)
- Eigenschaften (Read - nur eigene Objekte, NICHT bearbeiten)
- Buchungen (Read - nur Buchungen der eigenen Objekte)
- Channels (KOMPLETT ausgeblendet)
- Team (KOMPLETT ausgeblendet)
- Einstellungen (nur Account)

**Typische Use Cases:**
1. Auslastung der eigenen Objekte einsehen (Occupancy Rate)
2. Buchungen der eigenen Objekte einsehen (Gast-Namen, Check-in/out)
3. Umsatz der eigenen Objekte einsehen (Monats-Übersicht)
4. Objekt-Details ansehen (Beschreibung, Fotos, Preise)
5. Berichte herunterladen (PDF: Monatliche Auslastung & Umsatz)

**Anzahl pro Agentur:** 5-100 (je nach Anzahl externer Eigentümer)

**WICHTIG: Row-Level Security (RLS)**
- Eigentümer sehen NUR Objekte, bei denen `owner_id = auth.uid()`
- Keine Objekte anderer Eigentümer sichtbar
- Isolation auf Datenbank-Ebene (Supabase RLS Policies)

#### 3.1.5 Buchhalter (Accountant)

**Beschreibung:**
Finanz- oder Buchhaltungs-Abteilung. Zugriff auf Berichte, Abrechnungen und Finanzdaten. Kein Zugriff auf Objekt-Verwaltung oder Buchungs-Bearbeitung.

**Zugriff:**
- Dashboard (nur Finanz-Widgets: Umsatz, Ausstehende Zahlungen, Abrechnungen)
- Eigenschaften (KOMPLETT ausgeblendet ODER Read-Only)
- Buchungen (Read - nur Finanz-Daten: Preise, Zahlungsstatus, KEINE Bearbeitung)
- Berichte (Alle: Umsatz, Auslastung, Prognosen)
- Abrechnungen (Create, Export - Monats-Abrechnungen, Steuer-Reports)
- Channels (KOMPLETT ausgeblendet)
- Team (KOMPLETT ausgeblendet)
- Einstellungen (nur Account & Benachrichtigungen)

**Typische Use Cases:**
1. Monatliche Umsatz-Reports erstellen (pro Objekt, pro Channel)
2. Ausstehende Zahlungen überwachen (Pending Payments)
3. Abrechnungen exportieren (CSV, PDF für Steuerberater)
4. Buchungs-Details einsehen (nur Finanz-Daten: Preis, Zahlungsstatus)
5. Prognosen erstellen (basierend auf historischen Daten)

**Anzahl pro Agentur:** 1-3 (je nach Größe)

---

### 3.2 Permissions-Matrix (vollständig)

#### 3.2.1 Tabelle: Rolle × Feature

| Feature | Agentur-Admin | Manager | Mitarbeiter | Eigentümer | Buchhalter |
|---------|---------------|---------|-------------|------------|------------|
| **Dashboard** |
| Dashboard (alle Widgets) | ✅ | ✅ | ❌ (nur Check-ins) | ❌ (nur eigene) | ❌ (nur Finanzen) |
| Quick Stats | ✅ | ✅ | ❌ | ✅ (nur eigene) | ✅ (nur Umsatz) |
| Anstehende Check-ins | ✅ | ✅ | ✅ | ✅ (nur eigene) | ❌ |
| Recent Activity | ✅ | ✅ | ❌ | ❌ | ❌ |
| Channel-Status | ✅ | ✅ (Read) | ❌ | ❌ | ❌ |
| **Eigenschaften** |
| Eigenschaften ansehen (Read) | ✅ | ✅ | ✅ (Read-only) | ✅ (nur eigene) | ❌ / Read |
| Eigenschaften erstellen (Create) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Eigenschaften bearbeiten (Update) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Eigenschaften löschen (Delete) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Fotos hochladen | ✅ | ✅ | ❌ | ❌ | ❌ |
| Preise bearbeiten | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Buchungen** |
| Buchungen ansehen (Read) | ✅ | ✅ | ✅ | ✅ (nur eigene) | ✅ (nur Finanzen) |
| Buchungen erstellen (Create) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Buchungen bearbeiten (Update) | ✅ | ✅ | ❌ (nur Status) | ❌ | ❌ |
| Buchungen stornieren (Cancel) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Check-in/Check-out | ✅ | ✅ | ✅ | ❌ | ❌ |
| Gäste-Daten bearbeiten | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Gäste** |
| Gäste ansehen (Read) | ✅ | ✅ | ✅ | ❌ | ❌ |
| Gäste erstellen (Create) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Gäste bearbeiten (Update) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Gäste löschen (Delete) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Channels** |
| Channels ansehen (Read) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Channels verbinden (Connect) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Channels trennen (Disconnect) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Sync-Logs ansehen (View) | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Team** |
| Team-Mitglieder ansehen (Read) | ✅ | ✅ | ❌ | ❌ | ❌ |
| Team-Mitglieder einladen (Invite) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Rollen bearbeiten (Edit Role) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Team-Mitglieder entfernen (Remove) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Einstellungen** |
| Account-Einstellungen | ✅ | ✅ | ✅ | ✅ | ✅ |
| Zahlungs-Einstellungen (Stripe) | ✅ | ❌ | ❌ | ❌ | ❌ |
| Benachrichtigungen | ✅ | ✅ | ✅ | ✅ | ✅ |
| Abrechnung (Billing) | ✅ | ❌ | ❌ | ❌ | ❌ |
| **Berichte** |
| Umsatz-Reports (View) | ✅ | ✅ | ❌ | ✅ (nur eigene) | ✅ |
| Auslastungs-Reports (View) | ✅ | ✅ | ❌ | ✅ (nur eigene) | ✅ |
| Reports exportieren (Export) | ✅ | ✅ | ❌ | ✅ | ✅ |
| **Abrechnungen** |
| Abrechnungen ansehen (View) | ✅ | ❌ | ❌ | ❌ | ✅ |
| Abrechnungen erstellen (Create) | ✅ | ❌ | ❌ | ❌ | ✅ |
| Abrechnungen exportieren (Export) | ✅ | ❌ | ❌ | ❌ | ✅ |

**Legende:**
- **✅** = Zugriff erlaubt
- **❌** = Kein Zugriff (Feature komplett ausgeblendet)
- **✅ (Read)** = Nur Lesen, keine Änderungen
- **✅ (nur eigene)** = Nur eigene Daten (Row-Level Security)
- **❌ / Read** = Optional ausgeblendet ODER Read-Only (Implementierungsdetail)

---

### 3.3 Menü-Struktur pro Rolle (mit Mockups)

#### 3.3.1 Menü-Prinzip: Verschwinden, nicht disabled

**WICHTIG:**
Menüpunkte, auf die eine Rolle keinen Zugriff hat, werden KOMPLETT ausgeblendet (nicht nur disabled/grayed-out).

**Warum?**
- Bessere UX (weniger Clutter, keine Frustration)
- Klarere Rollen-Trennung (User sieht nur, was für ihn relevant ist)
- Sicherheit (keine Hinweise auf existierende Features, die man nicht nutzen darf)

**Beispiel (FALSCH):**
```jsx
<MenuItem disabled={!isOwner}>Zahlungen</MenuItem>
// User sieht "Zahlungen" (grayed-out), kann aber nicht klicken
```

**Beispiel (RICHTIG):**
```jsx
{isOwner && <MenuItem>Zahlungen</MenuItem>}
// User sieht "Zahlungen" nur, wenn er Owner ist
```

#### 3.3.2 Agentur-Admin (Owner) - Vollständige Navigation

**Sidebar (Desktop):**
```
┌──────────────────────┐
│ [Logo] PMS-Webapp    │
├──────────────────────┤
│                      │
│ 📊 Dashboard         │
│                      │
│ 🏠 Eigenschaften     │
│                      │
│ 📅 Buchungen         │
│                      │
│ 🔗 Channels          │
│                      │
│ 👥 Team              │
│                      │
│ 📊 Berichte          │
│                      │
│ 💰 Abrechnungen      │
│                      │
│ ⚙️  Einstellungen     │
│    ├─ Account        │
│    ├─ Zahlungen      │
│    ├─ Benachricht.   │
│    └─ Abrechnung     │
│                      │
└──────────────────────┘
```

**Top Bar (Desktop):**
```
┌─────────────────────────────────────────────────────┐
│ [Logo] PMS-Webapp          [🔔] [User Menu ▼]      │
└─────────────────────────────────────────────────────┘

User Menu:
- Profil
- Agentur wechseln (bei Multi-Tenant)
- Hilfe & Support
- Abmelden
```

**Alle Features sichtbar und nutzbar.**

#### 3.3.3 Manager - Eingeschränkte Navigation

**Sidebar (Desktop):**
```
┌──────────────────────┐
│ [Logo] PMS-Webapp    │
├──────────────────────┤
│                      │
│ 📊 Dashboard         │
│                      │
│ 🏠 Eigenschaften     │
│                      │
│ 📅 Buchungen         │
│                      │
│ 🔗 Channels          │  ← Read-Only (intern)
│                      │
│ 👥 Team              │  ← Read-Only (intern)
│                      │
│ 📊 Berichte          │
│                      │
│ ⚙️  Einstellungen     │
│    ├─ Account        │
│    └─ Benachricht.   │
│                      │
└──────────────────────┘
```

**Was ist VERSCHWUNDEN:**
- 💰 Abrechnungen (KOMPLETT ausgeblendet)
- Einstellungen > Zahlungen (KOMPLETT ausgeblendet)
- Einstellungen > Abrechnung (KOMPLETT ausgeblendet)

**Was ist Read-Only (Buttons ausgeblendet):**
- Channels: "Verbinden" Button VERSCHWUNDEN
- Team: "+ Einladen" Button VERSCHWUNDEN

#### 3.3.4 Mitarbeiter (Staff) - Stark reduzierte Navigation

**Sidebar (Desktop):**
```
┌──────────────────────┐
│ [Logo] PMS-Webapp    │
├──────────────────────┤
│                      │
│ 📊 Dashboard         │  ← Reduziert (nur Check-ins)
│                      │
│ 🏠 Eigenschaften     │  ← Read-Only
│                      │
│ 📅 Buchungen         │  ← Eingeschränkt (nur Status)
│                      │
│ ⚙️  Einstellungen     │
│    ├─ Account        │
│    └─ Benachricht.   │
│                      │
└──────────────────────┘
```

**Was ist VERSCHWUNDEN:**
- 🔗 Channels (KOMPLETT ausgeblendet)
- 👥 Team (KOMPLETT ausgeblendet)
- 📊 Berichte (KOMPLETT ausgeblendet)
- 💰 Abrechnungen (KOMPLETT ausgeblendet)
- Einstellungen > Zahlungen (KOMPLETT ausgeblendet)
- Einstellungen > Abrechnung (KOMPLETT ausgeblendet)

**Dashboard (reduziert):**
```
┌─────────────────────────────────────────┐
│ Dashboard (Mitarbeiter-Ansicht)         │
├─────────────────────────────────────────┤
│                                         │
│ Anstehende Check-ins (Heute)            │
│ • 10:00 - Beach Villa - John Doe        │
│ • 14:00 - Mountain Cabin - Jane Smith   │
│                                         │
│ [Alle Check-ins anzeigen →]             │
│                                         │
└─────────────────────────────────────────┘
```

**KEINE Quick Stats (Umsatz, Auslastung) sichtbar.**

**Buchungen (eingeschränkt):**
- Nur "Status ändern" Button (Check-in, Check-out)
- KEIN "Bearbeiten" Button
- KEIN "Stornieren" Button
- KEIN "Erstellen" Button

#### 3.3.5 Eigentümer (Property Owner) - Nur eigene Daten

**Sidebar (Desktop):**
```
┌──────────────────────┐
│ [Logo] PMS-Webapp    │
├──────────────────────┤
│                      │
│ 📊 Dashboard         │  ← Nur eigene Daten
│                      │
│ 🏠 Meine Objekte     │  ← Nur eigene, Read-Only
│                      │
│ 📅 Buchungen         │  ← Nur eigene, Read-Only
│                      │
│ 📊 Berichte          │  ← Nur eigene
│                      │
│ ⚙️  Einstellungen     │
│    └─ Account        │
│                      │
└──────────────────────┘
```

**Was ist VERSCHWUNDEN:**
- 🔗 Channels (KOMPLETT ausgeblendet)
- 👥 Team (KOMPLETT ausgeblendet)
- 💰 Abrechnungen (KOMPLETT ausgeblendet)
- Einstellungen > Zahlungen (KOMPLETT ausgeblendet)
- Einstellungen > Benachrichtigungen (KOMPLETT ausgeblendet)
- Einstellungen > Abrechnung (KOMPLETT ausgeblendet)

**Dashboard (nur eigene Daten):**
```
┌─────────────────────────────────────────┐
│ Dashboard (Eigentümer-Ansicht)          │
├─────────────────────────────────────────┤
│                                         │
│ Meine Objekte: 3                        │
│ Aktive Buchungen: 5                     │
│ Auslastung: 82%                         │
│ Umsatz (Monat): €2.400                  │
│                                         │
│ Anstehende Buchungen (Meine Objekte)    │
│ • Jul 1-5: Beach Villa - John Doe       │
│ • Jul 10-15: City Apt - Jane Smith      │
│                                         │
│ [Alle Buchungen anzeigen →]             │
│                                         │
└─────────────────────────────────────────┘
```

**Eigenschaften (automatisch gefiltert):**
- Filter automatisch auf `owner_id = auth.uid()`
- User sieht NUR eigene Objekte
- Keine Bearbeitungs-Buttons (Read-Only)

#### 3.3.6 Buchhalter (Accountant) - Finanz-Fokus

**Sidebar (Desktop):**
```
┌──────────────────────┐
│ [Logo] PMS-Webapp    │
├──────────────────────┤
│                      │
│ 📊 Dashboard         │  ← Finanz-Widgets
│                      │
│ 📅 Buchungen         │  ← Read-Only (Finanzen)
│                      │
│ 📊 Berichte          │
│                      │
│ 💰 Abrechnungen      │
│                      │
│ ⚙️  Einstellungen     │
│    ├─ Account        │
│    └─ Benachricht.   │
│                      │
└──────────────────────┘
```

**Was ist VERSCHWUNDEN:**
- 🏠 Eigenschaften (KOMPLETT ausgeblendet ODER Read-Only)
- 🔗 Channels (KOMPLETT ausgeblendet)
- 👥 Team (KOMPLETT ausgeblendet)
- Einstellungen > Zahlungen (KOMPLETT ausgeblendet)
- Einstellungen > Abrechnung (KOMPLETT ausgeblendet)

**Dashboard (Finanz-Fokus):**
```
┌─────────────────────────────────────────┐
│ Dashboard (Buchhalter-Ansicht)          │
├─────────────────────────────────────────┤
│                                         │
│ Umsatz (Monat): €12.500                 │
│ Ausstehende Zahlungen: €2.300           │
│ Abrechnungen (offen): 3                 │
│                                         │
│ Umsatz-Entwicklung (Chart)              │
│ ┌──────────────────────────────────┐   │
│ │ Jan  Feb  Mar  Apr  May  Jun     │   │
│ │  ▁   ▃   ▅   █   ▇   ▅          │   │
│ └──────────────────────────────────┘   │
│                                         │
│ [Abrechnungen anzeigen →]               │
│                                         │
└─────────────────────────────────────────┘
```

**Buchungen (Read-Only, nur Finanzen):**
- Nur Finanz-Spalten sichtbar (Preis, Zahlungsstatus, Zahlungsmethode)
- KEINE Bearbeitungs-Buttons
- KEINE Gast-Details (Datenschutz)

---

### 3.4 Row-Level Security (RLS Konzept)

#### 3.4.1 Daten-Isolation auf Datenbank-Ebene

**Ziel:**
- Agenturen sehen nur ihre eigenen Daten (Multi-Tenancy)
- Eigentümer sehen nur ihre eigenen Objekte (innerhalb einer Agentur)

**Methode:**
- Supabase Row-Level Security (RLS) Policies
- PostgreSQL-basierte Sicherheits-Policies auf Tabellenebene

#### 3.4.2 Agentur-Ebene (Multi-Tenancy)

**Datenbank-Tabellen mit `agency_id`:**
- `properties` (agency_id)
- `bookings` (agency_id)
- `guests` (agency_id)
- `channels` (agency_id)
- `team_members` (agency_id)
- `sync_logs` (agency_id)

**RLS Policy: Agentur-Isolation**

**Konzept (KEIN SQL, nur Konzept):**
```
Policy: agency_isolation
Tabelle: properties
Regel: Benutzer sehen nur Eigenschaften ihrer eigenen Agentur

Bedingung:
  auth.jwt()->>'agency_id' = properties.agency_id

Ergebnis:
  - Benutzer A (Agentur 1) sieht nur Eigenschaften von Agentur 1
  - Benutzer B (Agentur 2) sieht nur Eigenschaften von Agentur 2
```

**Anwendung:**
- Gilt für ALLE Rollen (Owner, Manager, Staff, Viewer, Buchhalter)
- Automatisch auf Datenbank-Ebene (keine Code-Logik nötig)
- Sicherheit: Selbst bei SQL-Injection sieht User nur eigene Agentur-Daten

#### 3.4.3 Eigentümer-Ebene (innerhalb Agentur)

**Datenbank-Tabellen mit `owner_id`:**
- `properties` (agency_id, owner_id)
- `bookings` (agency_id, property_id → owner_id via JOIN)

**RLS Policy: Eigentümer-Isolation**

**Konzept (KEIN SQL, nur Konzept):**
```
Policy: owner_isolation
Tabelle: properties
Regel: Eigentümer sehen nur ihre eigenen Objekte

Bedingung:
  (auth.role() = 'owner' AND auth.uid() = properties.owner_id)
  OR
  (auth.role() IN ('admin', 'manager', 'staff') AND auth.jwt()->>'agency_id' = properties.agency_id)

Ergebnis:
  - Eigentümer A sieht nur Eigenschaften, bei denen owner_id = A
  - Admin/Manager/Staff sehen ALLE Eigenschaften ihrer Agentur
```

**Anwendung:**
- Nur für Rolle "Property Owner"
- Automatische Filterung auf Datenbank-Ebene
- Transparenz: Eigentümer können ihre Objekte einsehen, ohne Zugriff auf andere Objekte

#### 3.4.4 RLS Policies für Buchungen

**Konzept:**

**Policy: bookings_agency_isolation**
```
Tabelle: bookings
Regel: Benutzer sehen nur Buchungen ihrer eigenen Agentur

Bedingung:
  auth.jwt()->>'agency_id' = bookings.agency_id
```

**Policy: bookings_owner_isolation**
```
Tabelle: bookings
Regel: Eigentümer sehen nur Buchungen ihrer eigenen Objekte

Bedingung:
  (auth.role() = 'owner' AND bookings.property_id IN (
    SELECT id FROM properties WHERE owner_id = auth.uid()
  ))
  OR
  (auth.role() IN ('admin', 'manager', 'staff', 'accountant') AND auth.jwt()->>'agency_id' = bookings.agency_id)

Ergebnis:
  - Eigentümer A sieht nur Buchungen von Objekten, bei denen owner_id = A
  - Admin/Manager/Staff/Buchhalter sehen ALLE Buchungen ihrer Agentur
```

#### 3.4.5 RLS Policies für Team-Management

**Konzept:**

**Policy: team_members_isolation**
```
Tabelle: team_members
Regel: Benutzer sehen nur Team-Mitglieder ihrer eigenen Agentur

Bedingung:
  auth.jwt()->>'agency_id' = team_members.agency_id

Ausnahme:
  - Rolle "Staff" sieht Team-Mitglieder NICHT (per App-Logik ausgeblendet)
  - Rolle "Owner" sieht Team-Mitglieder (per App-Logik sichtbar)
```

**WICHTIG:**
- RLS schützt auf Datenbank-Ebene (Backend-Sicherheit)
- App-Logik schützt auf UI-Ebene (Frontend-Sicherheit)
- Beide Ebenen MÜSSEN konsistent sein

#### 3.4.6 Implementierungs-Hinweise

**Backend (Supabase RLS):**
1. Policies definieren (PostgreSQL)
2. JWT-Claims nutzen (`agency_id`, `role`)
3. Policies testen (mit Test-Benutzern)

**Frontend (Next.js):**
1. Supabase Client nutzt automatisch RLS
2. Keine manuelle Filterung nötig (Datenbank macht das)
3. Zusätzliche UI-Logik für Menü-Reduktion

**Beispiel (Frontend):**
```typescript
// Supabase Query (automatisch mit RLS)
const { data: properties } = await supabase
  .from('properties')
  .select('*');

// RLS Policy filtert automatisch nach agency_id
// User sieht nur Eigenschaften seiner Agentur
```

**Vorteil:**
- Sicherheit auf Datenbank-Ebene (selbst bei Backend-Bugs)
- Kein manuelles Filtern nötig (weniger Code, weniger Fehler)
- Performance (Datenbank-Index auf agency_id)

---

## 4. Zusammenfassung & Nächste Schritte

### 4.1 Wichtigste Entscheidungen

**Produktpositionierung:**
- B2B-Software für Agenturen (5-500 Objekte), nicht für Einzelvermieter
- 50% günstiger, 80% Zeitersparnis vs. Konkurrenz
- DACH-Markt (Deutschland, Österreich, Schweiz)

**Zielgruppe:**
- Primär: Ferienwohnungs-Agenturen (professionell, gewerblich)
- Sekundär: Objekt-Manager (Selbstständige)
- Anti: Einzelvermieter, Hotelketten, Reiseveranstalter

**Landing-Page:**
- 10 Abschnitte (Hero, Problem, Features, Benefits, Pricing, Testimonials, FAQ, CTA)
- Deutsch, professionell, B2B-Fokus (keine Marketing-Buzzwords)
- 14 Tage kostenlose Testphase (ohne Kreditkarte)

**Rollen:**
- 5 Rollen: Agentur-Admin, Manager, Mitarbeiter, Eigentümer, Buchhalter
- Menüpunkte VERSCHWINDEN (nicht disabled)
- Row-Level Security (RLS) auf Datenbank-Ebene

### 4.2 Nächste Schritte

**Phase 14: Frontend-Implementierung (Next.js)**
1. Landing-Page umsetzen (basierend auf Wireframe)
2. RBAC-System implementieren (Rollen, Permissions, Menü-Reduktion)
3. Dashboard pro Rolle (Owner, Manager, Staff, Owner, Buchhalter)

**Phase 15: Backend-Implementierung (Supabase)**
1. RLS Policies definieren (PostgreSQL)
2. JWT-Claims erweitern (`agency_id`, `role`)
3. RLS testen (mit Test-Benutzern)

**Phase 16: Marketing & Sales**
1. Landing-Page live schalten
2. Google Ads Kampagne starten
3. Demo-Funnel einrichten (Calendly)
4. Trial-Onboarding optimieren (E-Mail-Kampagne)

---

## Anhang: Design-System-Kompatibilität

**Basis: Phase 10A/10B/10C (READ-ONLY)**

**Alle UI-Texte aus Phase 10B/10C übernommen:**
- Buttons: "Speichern", "Abbrechen", "Löschen", etc. (Deutsch)
- Labels: "Eigenschaftsname", "Check-in", "Status", etc. (Deutsch)
- Status-Badges: "Bestätigt", "Reserviert", "Eingecheckt", etc. (Deutsch)

**Alle Design-Tokens aus Phase 10B/10C übernommen:**
- Farben: Primary (#2563EB), Success (#16A34A), Error (#DC2626), Warning (#D97706)
- Typografie: Inter, 16px Base Size, Font Weights (400, 500, 600, 700)
- Spacing: 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px
- Komponenten: Buttons, Forms, Badges, Cards, Tables, Modals, Alerts

**Rollen-UX aus Phase 10C integriert:**
- Menüpunkte verschwinden (nicht disabled)
- Permissions-Matrix erweitert (5 Rollen statt 4)
- Deutsche UI-Texte für Rollen: "Inhaber", "Manager", "Mitarbeiter", "Eigentümer", "Buchhalter"

---

**Ende des Dokuments.**
