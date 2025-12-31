# GitHub Setup Guide

Dieser Guide beschreibt die vollständige Einrichtung des GitHub Repositories für PMS-Webapp basierend auf Phase 9 (Release Plan).

**Status:** Phase 17A - GitHub Setup
**Datum:** 2025-12-22

---

## Inhaltsverzeichnis

1. [Repository Setup](#1-repository-setup)
2. [Branch Protection Rules](#2-branch-protection-rules)
3. [GitHub Actions Secrets](#3-github-actions-secrets)
4. [Team & Permissions](#4-team--permissions)
5. [Branch-Strategie](#5-branch-strategie)
6. [Commit Convention](#6-commit-convention)
7. [Checkliste](#7-checkliste)

---

## 1. Repository Setup

### 1.1 Repository erstellen (bereits erledigt ✅)

Das Repository existiert bereits:
- **Name:** `PMS-Webapp`
- **Type:** Private (oder Public, je nach Bedarf)
- **Beschreibung:** B2B SaaS für Ferienwohnungs-Agenturen - Channel Manager & Property Management System

### 1.2 Repository Settings

Navigiere zu **Settings** auf GitHub.com:

**General:**
- ✅ Allow merge commits: **Deaktiviert** (nur für `develop` → `main`)
- ✅ Allow squash merging: **Aktiviert** (Standard für Feature-Branches)
- ✅ Allow rebase merging: **Deaktiviert** (zu riskant für Team)
- ✅ Automatically delete head branches: **Aktiviert**
- ✅ Allow auto-merge: **Aktiviert** (optional, für Auto-Merge nach Approval)

**Features:**
- ✅ Issues: **Aktiviert**
- ✅ Projects: **Aktiviert** (optional)
- ✅ Wiki: **Deaktiviert** (Dokumentation in `docs/`)
- ✅ Discussions: **Deaktiviert** (verwenden Issues)

**Pull Requests:**
- ✅ Allow squash merging: **Aktiviert**
- ✅ Default to PR title and description: **Aktiviert**
- ✅ Automatically delete head branches: **Aktiviert**

---

## 2. Branch Protection Rules

### 2.1 `main` Branch Protection

Navigiere zu **Settings → Branches → Add branch protection rule**

**Branch name pattern:** `main`

**Protect matching branches:**
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: **1** (für Team > 1 Person)
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require review from Code Owners (wenn CODEOWNERS existiert)

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - **Required status checks:**
    - `CI (Minimal Backend) / backend` (vom ci-backend.yml Workflow)
    - `CodeQL / Analyze (python)` (vom CodeQL Workflow)

- ✅ **Require conversation resolution before merging**

- ✅ **Require signed commits:** **Deaktiviert** (optional, später aktivieren)

- ✅ **Require linear history:** **Deaktiviert** (Merge Commits erlaubt)

- ✅ **Include administrators:** **Aktiviert** (Admins müssen auch Regeln folgen)

- ✅ **Restrict who can push to matching branches:**
  - Nur Admins können direkt pushen (ohne PR)

- ✅ **Allow force pushes:** **Deaktiviert**

- ✅ **Allow deletions:** **Deaktiviert**

### 2.2 `develop` Branch Protection

**Branch name pattern:** `develop`

**Protect matching branches:**
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: **0** (für Solo-Dev) / **1** (für Team)
  - ✅ Dismiss stale pull request approvals when new commits are pushed

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - **Required status checks:**
    - `CI (Minimal Backend) / backend`
    - `CodeQL / Analyze (python)`

- ✅ **Require conversation resolution before merging**

- ✅ **Require linear history:** **Deaktiviert**

- ✅ **Include administrators:** **Deaktiviert** (Admins können direkt pushen für schnelle Fixes)

- ✅ **Allow force pushes:** **Deaktiviert**

- ✅ **Allow deletions:** **Deaktiviert**

### 2.3 `release/*` Branch Protection (optional)

**Branch name pattern:** `release/*`

**Protect matching branches:**
- ✅ **Require a pull request before merging**
  - ✅ Require approvals: **1**

- ✅ **Require status checks to pass before merging**

- ✅ **Allow deletions:** **Aktiviert** (nach Merge in `main` löschen)

---

## 3. GitHub Actions Secrets

### 3.1 Secrets hinzufügen

Navigiere zu **Settings → Secrets and variables → Actions → New repository secret**

**Development Secrets (für CI):**
```
SUPABASE_URL_DEV=https://xyz.supabase.co
SUPABASE_ANON_KEY_DEV=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
ENCRYPTION_KEY_DEV=<generierter-fernet-key>
REDIS_URL_DEV=redis://localhost:6379
```

**Staging Secrets:**
```
SUPABASE_URL_STAGING=https://xyz-staging.supabase.co
SUPABASE_ANON_KEY_STAGING=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
ENCRYPTION_KEY_STAGING=<generierter-fernet-key>
REDIS_URL_STAGING=redis://staging.upstash.io:6379
```

**Production Secrets:**
```
SUPABASE_URL_PROD=https://xyz-prod.supabase.co
SUPABASE_ANON_KEY_PROD=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
ENCRYPTION_KEY_PROD=<generierter-fernet-key>
REDIS_URL_PROD=redis://prod.upstash.io:6379
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

**Deployment Secrets (später hinzufügen):**
```
RAILWAY_TOKEN=<railway-api-token>
VERCEL_TOKEN=<vercel-api-token>
```

### 3.2 Environment Secrets

Für bessere Organisation können Secrets auch pro Environment definiert werden:

Navigiere zu **Settings → Environments**

**Environments erstellen:**
1. **development** (für Feature-Branch-Deploys)
2. **staging** (Auto-Deploy bei `develop` Push)
3. **production** (Manual Approval, Deploy bei `main` Tag)

**Protection Rules (Production):**
- ✅ Required reviewers: 1 Person
- ✅ Wait timer: 0 minutes (oder 5 Min für Cooldown)
- ✅ Deployment branches: Only `main` branch

---

## 4. Team & Permissions

### 4.1 Collaborators hinzufügen

Navigiere zu **Settings → Collaborators and teams → Add people**

**Rollen:**
- **Admin:** Full access (Repo Settings, Branch Protection, Secrets)
- **Maintain:** Manage issues, PRs, Settings (aber keine Branch Protection)
- **Write:** Push zu Branches, Merge PRs
- **Triage:** Manage issues und PRs (aber kein Code-Push)
- **Read:** Read-only access

**Team-Setup (Beispiel):**
- **@YOUR_USERNAME:** Admin (Owner)
- **@TEAM_MEMBER_1:** Write (Entwickler)
- **@TEAM_MEMBER_2:** Write (Entwickler)
- **@QA_TEAM:** Triage (QA, Issue Management)

---

## 5. Branch-Strategie

### 5.1 Bestehende Branches

```bash
# Branches anzeigen
git branch -a

# Output:
# * main
#   develop
#   remotes/origin/main
#   remotes/origin/develop
```

### 5.2 Branch-Typen (Trunk-Based Development)

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

### 5.3 Branch-Workflow

**Feature entwickeln:**
```bash
git checkout develop
git pull origin develop
git checkout -b feature/add-booking-com
# ... entwickeln ...
git add .
git commit -m "feat(channel-manager): add Booking.com adapter"
git push origin feature/add-booking-com
# PR erstellen: feature/add-booking-com → develop
```

**Release vorbereiten:**
```bash
git checkout develop
git pull origin develop
git checkout -b release/v1.0.0
# Version bumpen in pyproject.toml, package.json, etc.
# CHANGELOG.md aktualisieren
git add .
git commit -m "chore(release): prepare v1.0.0"
git push origin release/v1.0.0
# PR erstellen: release/v1.0.0 → main
```

**Nach Merge in `main`: Tag erstellen**
```bash
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release v1.0.0: MVP Launch

Features:
- Direct Booking Engine
- Airbnb Channel Manager
- Property Management
- Multi-Tenancy (RLS)

Deployment: docs/deployment/v1.0.0.md"

git push origin v1.0.0
```

---

## 6. Commit Convention

### 6.1 Format (Conventional Commits)

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 6.2 Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Add/update tests
- `build`: Build system or dependencies
- `ci`: CI/CD configuration
- `chore`: Maintenance tasks

### 6.3 Scopes

- `backend`, `frontend`, `channel-manager`, `sync-engine`
- `database`, `auth`, `payments`, `webhooks`
- `monitoring`, `docs`

### 6.4 Beispiele

```bash
feat(channel-manager): add Booking.com adapter
fix(sync-engine): prevent duplicate booking imports
docs(api): update OpenAPI spec for bookings endpoint
chore(deps): upgrade FastAPI to 0.109.0
```

**Breaking Changes:**
```bash
feat(backend)!: migrate to Supabase RLS

BREAKING CHANGE: All API endpoints now require tenant_id header.
Migration guide: docs/migration-v2.md
```

---

## 7. Checkliste

### 7.1 Repository Setup ✅

- [x] Repository erstellt
- [x] README.md existiert
- [x] LICENSE hinzufügen (falls benötigt)
- [x] .gitignore komplett
- [x] CODEOWNERS erstellt
- [x] CONTRIBUTING.md erstellt
- [x] CHANGELOG.md erstellt

### 7.2 Branch Protection ⚠️ (manuell auf GitHub.com)

- [ ] `main` Branch Protection aktiviert
  - [ ] Require 1 approval
  - [ ] Require status checks (CI, CodeQL)
  - [ ] Restrict push to admins only
- [ ] `develop` Branch Protection aktiviert
  - [ ] Require status checks (CI, CodeQL)
  - [ ] Require 0-1 approvals (je nach Team-Größe)

### 7.3 Templates ✅

- [x] PR Template (`.github/pull_request_template.md`)
- [x] Issue Templates (Bug Report, Feature Request)

### 7.4 Automation ✅

- [x] Dependabot konfiguriert (`.github/dependabot.yml`)
- [x] CodeQL Workflow erstellt (`.github/workflows/codeql.yml`)
- [x] CI Workflow existiert (`.github/workflows/ci-backend.yml`)

### 7.5 Secrets ⚠️ (manuell auf GitHub.com)

- [ ] Development Secrets hinzufügen
- [ ] Staging Secrets hinzufügen
- [ ] Production Secrets hinzufügen
- [ ] Environments erstellen (development, staging, production)

### 7.6 Team & Permissions ⚠️ (manuell auf GitHub.com)

- [ ] Collaborators hinzufügen (falls Team)
- [ ] Rollen zuweisen (Admin, Write, Triage)
- [ ] CODEOWNERS aktualisieren mit echten GitHub-Usernames

### 7.7 Documentation ✅

- [x] CONTRIBUTING.md mit Branch-Strategie
- [x] CHANGELOG.md initialisiert
- [x] GitHub Setup Guide (dieses Dokument)

---

## 8. Nächste Schritte

Nach Abschluss des GitHub Setups:

1. **Branch Protection aktivieren** (manuell auf GitHub.com)
2. **Secrets hinzufügen** (manuell auf GitHub.com)
3. **Team einladen** (falls vorhanden)
4. **Erste Release planen** (v0.1.0 oder v1.0.0)
5. **CI/CD erweitern** (Deployment-Workflows hinzufügen)

---

## 9. Hilfreiche Links

- **Release Plan:** `docs/product/RELEASE_PLAN.md`
- **Conventional Commits:** https://www.conventionalcommits.org/
- **Trunk-Based Development:** https://trunkbaseddevelopment.com/
- **Semantic Versioning:** https://semver.org/
- **GitHub Branch Protection:** https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches
- **GitHub Actions Secrets:** https://docs.github.com/en/actions/security-guides/using-secrets-in-github-actions
- **Dependabot:** https://docs.github.com/en/code-security/dependabot
- **CodeQL:** https://docs.github.com/en/code-security/code-scanning

---

**Status:** Phase 17A abgeschlossen (lokale Files)
**Noch zu erledigen:** Branch Protection & Secrets auf GitHub.com konfigurieren
