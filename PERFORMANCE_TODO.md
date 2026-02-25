# Performance Optimierung - TODO

**Erstellt:** 2026-02-25
**Basierend auf:** Umfassende Code-Analyse (Frontend, Backend, Datenbank)

---

## Phase 1: Quick Wins - useMemo Optimierung

- [x] **Phase 1 abgeschlossen**

### Frontend - Filter-Optimierung
- [x] 1.1 `useMemo` für Filter in `/app/amenities/page.tsx`
- [x] 1.2 `/app/bookings/page.tsx` - bereits serverseitige Filter (kein useMemo nötig)
- [x] 1.3 `/app/properties/page.tsx` - bereits serverseitige Filter (kein useMemo nötig)

**Ergebnis:** Amenities-Seite filtert jetzt ohne Re-render-Trigger. Bookings/Properties nutzten bereits effiziente serverseitige Filterung.

---

## Phase 2: State Management & Caching

- [ ] **Phase 2 abgeschlossen**

### Frontend - State Aggregation
- [ ] 2.1 `useModal` Hook konsistent in amenities, bookings nutzen
- [ ] 2.2 `useListState` Hook konsistent nutzen
- [ ] 2.3 `React.memo` für `BookingCard` Component
- [ ] 2.4 `React.memo` für `PropertyCard` Component
- [ ] 2.5 `<img>` → `<Image>` mit lazy loading (Public-Seiten)

### Backend - Response Caching
- [ ] 2.6 Redis-Cache für GET `/api/v1/properties` (60s TTL)
- [ ] 2.7 Redis-Cache für GET `/api/v1/amenities` (300s TTL)
- [ ] 2.8 COUNT ohne JOINs für Pagination optimieren

---

## Phase 3: Dynamic Imports & Bundle Optimization

- [ ] **Phase 3 abgeschlossen**

### Frontend
- [ ] 3.1 Dynamic Import für `RichTextEditor`
- [ ] 3.2 Dynamic Import für Calendar-Komponenten
- [ ] 3.3 Dynamic Import für schwere Modals
- [ ] 3.4 Bundle-Analyzer (@next/bundle-analyzer) einrichten
- [ ] 3.5 Web Vitals Monitoring implementieren

### Backend
- [ ] 3.6 Schlanke Response-DTOs für Listen-Endpoints (BookingListItem)
- [ ] 3.7 Cursor-based Pagination für große Listen

---

## Phase 4: Datenbank-Optimierung (Optional)

- [ ] **Phase 4 abgeschlossen**

### Indexes
- [ ] 4.1 GIN Index für `bookings.channel_data` (JSONB)
- [ ] 4.2 GIN Index für `audit_log.metadata` (JSONB)
- [ ] 4.3 Index auf `bookings.created_by_user_id`
- [ ] 4.4 Connection Pool max_size auf 30 erhöhen

---

## Erwartete Verbesserungen

| Metrik | Vorher | Nach Phase 1 | Nach Phase 2 | Nach Phase 3 |
|--------|--------|--------------|--------------|--------------|
| Re-renders (Amenities) | 10+ | 2-3 | 2-3 | 2-3 |
| API Latenz | ~200ms | ~200ms | ~100ms | ~100ms |
| Bundle Size (JS) | ~500KB | ~500KB | ~450KB | ~400KB |
| Bandwidth (Listen) | ~12KB | ~12KB | ~8KB | ~5KB |

---

## Commit-Historie

| Phase | Commit | Datum | Status |
|-------|--------|-------|--------|
| Phase 1 | TBD | 2026-02-25 | ✅ Fertig |
| Phase 2 | - | - | Ausstehend |
| Phase 3 | - | - | Ausstehend |
| Phase 4 | - | - | Optional |
