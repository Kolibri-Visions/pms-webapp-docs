# PMS-Webapp Multi-Agent System **Vollständige Multi-Agent-Konstellation für eine Property Management System (PMS) Webapp mit integriertem Channel Manager** --- ## 📋 Projektübersicht **Projektziel:** All-in-One Buchungssoftware für Ferienwohnungen mit integriertem Channel Manager zur Echtzeit-Synchronisation mit: - **Airbnb** - **Booking.com** - **Expedia** - **FeWo-direkt** - **Google Ferienunterkünfte** **Hauptziel:** Vermeidung von Doppelbuchungen durch bidirektionale Echtzeit-Synchronisation. --- ## 🎯 Was Sie in diesem Repository finden ### 1. **Agenten-System** (AGENT_SYSTEM.md) Komplette Übersicht über die Multi-Agent-Hierarchie mit: - 1 Master-Agent (PMS-Orchestrator) - 9 spezialisierte Sub-Agents - Agenten-Kommunikation & Übergaben - Qualitätskriterien - Done-Definitionen ### 2. **Fertige Agent-Prompts** (agents/) Einsatzbereite Prompts im **wshobson/agents Format**: - pms-orchestrator.md - Master-Agent für Gesamtkoordination - system-architect.md - System-Architektur & Tech-Stack - database-architect-pms.md - Datenmodell & RLS - backend-channel-manager.md - Channel-Manager-Integrationen - Weitere Agents (backend-core, sync-resilience, security-rls, frontend, qa, devops, documentation) ### 3. **Workflow-Definitionen** (workflows/) - development-sequence.md - Vollständige Entwicklungsreihenfolge mit Checkpoints - done-definitions.md - Detaillierte Checklisten pro Agent --- ## 🚀 Schnellstart ### Empfohlene Entwicklungsreihenfolge **Phase 1: Architektur & Design (Ultra-Technisch)**
1. Aktiviere system-architect
   → Output: System-Architektur, Tech-Stack, OpenAPI-Spec, Failure-Mode-Analyse

2. Aktiviere database-architect-pms
   → Output: Datenmodell, RLS-Policies, Migration-Scripts
**Phase 2: Backend-Implementierung**
3. Parallel: backend-channel-manager + backend-core-pms
   → Channel-Manager-Integrationen + Core-PMS-Features

4. Sequential: sync-resilience → security-rls
   → Resilience-Layer + RLS-Implementation
**Phase 3-6: Frontend, Testing, DevOps, Dokumentation**
5. frontend-pms → UI/UX Implementation
6. qa-testing-pms → Comprehensive Testing
7. devops-pms → Deployment & Monitoring
8. documentation-pms → Technical & Stakeholder Docs
**Siehe workflows/development-sequence.md für vollständige Details.**
