# Contributing zu PMS-Webapp

Vielen Dank für Ihr Interesse, zu diesem Projekt beizutragen!

## Inhaltsverzeichnis

- [Entwicklungsumgebung](#entwicklungsumgebung)
- [Branch-Strategie](#branch-strategie)
- [Commit-Convention](#commit-convention)
- [Pull Request Prozess](#pull-request-prozess)
- [Code-Standards](#code-standards)
- [Testing](#testing)

---

## Entwicklungsumgebung

### Voraussetzungen

- **Python:** 3.12+ (3.12.3 empfohlen)
- **Node.js:** 18+ (für Frontend, wenn vorhanden)
- **Docker:** Latest (für lokale Entwicklung)
- **Git:** Latest

### Setup

```bash
# Repository klonen
git clone https://github.com/YOUR_ORG/PMS-Webapp.git
cd PMS-Webapp

# Backend Setup
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Environment Setup
cp .env.example .env
# .env bearbeiten und Secrets eintragen

# Tests ausführen
./scripts/run_pytest.sh
```

---

## Branch-Strategie

Wir verwenden **Trunk-Based Development** mit kurzlebigen Feature Branches.

### Branch-Struktur

```
main (protected)
  ↓
  develop (integration branch)
    ↓
    feature/xyz (kurzlebig, < 3 Tage)
    fix/abc (kurzlebig, < 1 Tag)

release/vX.Y.Z (für Releases)
hotfix/critical-bug (für Production Hotfixes)
```

### Branch-Typen

| Branch | Zweck | Lebensdauer | Protected | Deploy To |
|--------|-------|-------------|-----------|-----------|
| `main` | Production-ready code | Permanent | ✅ Yes | Production |
| `develop` | Integration branch | Permanent | ✅ Yes | Staging |
| `feature/*` | Feature development | < 3 Tage | ❌ No | Dev (optional) |
| `fix/*` | Bug fixes | < 1 Tag | ❌ No | Dev (optional) |
| `release/*` | Release preparation | < 1 Woche | ✅ Yes | Staging → Production |
| `hotfix/*` | Critical production fixes | < 2 Stunden | ❌ No | Production (urgent) |

### Branch-Naming

```bash
# Features
feature/add-booking-com-adapter
feature/implement-revenue-analytics

# Fixes
fix/calendar-sync-duplicate-bookings
fix/stripe-webhook-timeout

# Releases
release/v1.0.0
release/v1.2.3

# Hotfixes
hotfix/critical-payment-bug
hotfix/security-vulnerability
```

### Workflow

1. **Feature entwickeln:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/my-feature
   # ... entwickeln, committen ...
   git push origin feature/my-feature
   # PR erstellen: feature/my-feature → develop
   ```

2. **Bug fixen:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b fix/my-bug
   # ... fixen, committen ...
   git push origin fix/my-bug
   # PR erstellen: fix/my-bug → develop
   ```

3. **Release vorbereiten:**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b release/v1.0.0
   # ... Version bumpen, CHANGELOG aktualisieren ...
   git push origin release/v1.0.0
   # PR erstellen: release/v1.0.0 → main
   # Nach Merge: Tag erstellen
   ```

---

## Commit-Convention

Wir verwenden **Conventional Commits** für klare, semantische Commit-Messages.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring (no feature/fix)
- `perf`: Performance improvement
- `test`: Add/update tests
- `build`: Build system or dependencies
- `ci`: CI/CD configuration
- `chore`: Maintenance tasks

### Scopes (PMS-Webapp specific)

- `backend`: Backend API (FastAPI)
- `frontend`: Frontend (Next.js)
- `channel-manager`: Channel Manager Adapters
- `sync-engine`: Sync Engine (Celery tasks)
- `database`: Database schema, migrations
- `auth`: Authentication/Authorization
- `payments`: Payment processing (Stripe)
- `webhooks`: Webhook handlers
- `monitoring`: Observability (Prometheus, Sentry)
- `docs`: Documentation

### Beispiele

```bash
# Feature
feat(channel-manager): add Booking.com adapter
feat(frontend): implement property search UI

# Fix
fix(sync-engine): prevent duplicate booking imports
fix(payments): handle Stripe webhook timeout

# Refactor
refactor(backend): extract availability logic to service
refactor(frontend): migrate to App Router

# Docs
docs(api): update OpenAPI spec for bookings endpoint

# Chore
chore(deps): upgrade FastAPI to 0.109.0
```

### Breaking Changes

Für Breaking Changes verwenden Sie `!` nach dem Type/Scope:

```bash
feat(backend)!: migrate to Supabase RLS

BREAKING CHANGE: All API endpoints now require tenant_id header.
Migration guide: docs/migration-v2.md
```

---

## Pull Request Prozess

### PR erstellen

1. **Branch von `develop` erstellen**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/my-feature
   ```

2. **Code entwickeln**
   - Folgen Sie den [Code-Standards](#code-standards)
   - Schreiben Sie Tests (Coverage > 80%)
   - Dokumentieren Sie Änderungen

3. **PR öffnen**
   - Verwenden Sie die [PR-Template](.github/pull_request_template.md)
   - Beschreiben Sie Änderungen klar
   - Verlinken Sie relevante Issues

4. **Review abwarten**
   - Für Solo-Dev: Self-review, dann mergen
   - Für Teams: Review von mind. 1 Team-Mitglied

5. **CI checks abwarten**
   - Alle Tests müssen grün sein
   - Linting muss ohne Fehler durchlaufen

6. **Merge**
   - `feature/*` → `develop`: **Squash & Merge**
   - `develop` → `main`: **Merge Commit**
   - `hotfix/*` → `main`: **Merge Commit**

### Merge-Strategien

- **Squash & Merge:** Für Feature-Branches (cleaner History)
- **Merge Commit:** Für `develop` → `main` (preserve History)
- **Rebase:** NICHT verwenden (zu riskant für Team)

---

## Code-Standards

### Python (Backend)

**Formatter:** `black`
```bash
cd backend
black .
```

**Linter:** `ruff`
```bash
cd backend
ruff check .
```

**Type Checking:** `mypy` (optional)
```bash
cd backend
mypy app/
```

**Docstrings:** Google Style
```python
def calculate_price(nights: int, rate: float) -> float:
    """Calculate total price for booking.

    Args:
        nights: Number of nights
        rate: Price per night

    Returns:
        Total price

    Raises:
        ValueError: If nights or rate is negative
    """
    if nights < 0 or rate < 0:
        raise ValueError("Nights and rate must be positive")
    return nights * rate
```

### JavaScript/TypeScript (Frontend)

**Formatter:** `prettier`
**Linter:** `eslint`
**Type Checking:** `tsc`

---

## Testing

### Test-Coverage

- **Minimum:** 80% Coverage
- **Ideal:** 90% Coverage

### Test-Typen

**Alle Tests ausführen:**
```bash
cd backend
./scripts/run_pytest.sh
```

**Unit Tests:**
```bash
cd backend
./scripts/run_pytest.sh tests/unit/
```

**Integration Tests:**
```bash
cd backend
./scripts/run_pytest.sh tests/integration/
```

**Smoke Tests:**
```bash
cd backend
./scripts/run_pytest.sh tests/smoke/
```

**Hinweis:** Das `run_pytest.sh` Script deaktiviert globale pytest-Plugins und stellt reproduzierbare Test-Runs sicher.

### Test-Konventionen

- **Naming:** `test_<function_name>_<scenario>`
- **Struktur:** Arrange, Act, Assert (AAA)
- **Mocking:** Verwenden Sie `pytest-mock` oder `unittest.mock`

**Beispiel:**
```python
def test_calculate_price_valid_input():
    # Arrange
    nights = 3
    rate = 100.0

    # Act
    result = calculate_price(nights, rate)

    # Assert
    assert result == 300.0
```

---

## Fragen?

Bei Fragen öffnen Sie bitte ein [Issue](https://github.com/YOUR_ORG/PMS-Webapp/issues) oder kontaktieren Sie das Team.
