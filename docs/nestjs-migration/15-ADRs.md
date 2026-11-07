# 15 — Architecture Decision Records (ADRs)

> **Decisiones arquitectónicas del proyecto, con contexto, alternativas, justificación y consecuencias.
> Cualquier desviación de un spec debe registrarse aquí con el ADR correspondiente.**

Formato: **MADR** (Markdown Any Decision Record).

---

## ADR-001 — Stack: NestJS + TypeScript en lugar de FastAPI + Python

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision Makers**: Product Owner, Tech Lead
- **Context**:
  - El core del valor del SaaS a 2-3 años es **CRUD + Multi-tenant puro** (confirmado por el usuario), **sin capa IA confirmada**.
  - Frontend será Angular 21 (TypeScript ecosistema).
  - El proyecto FastAPI actual es sólido pero single-tenant; migrarlo a multi-tenant costaría ~85% de un proyecto desde cero.
  - IA "tal vez" en futuro.
- **Decision**:
  - **Start from scratch con NestJS + TypeScript + Prisma + PostgreSQL en monorepo Nx con Angular 21**.
  - FastAPI se mantiene como referencia de dominio + patrimonio funcional (auth, RBAC, audit, catalogs, etc.) pero no como código base.
  - Si la capa IA aparece, se desarrolla como **microservicio Python aislado** que comparte la DB por `tenant_id`.
- **Alternatives**:
  1. Migrar el proyecto FastAPI actual a multi-tenant (3-6 meses, no reutiliza TS del frontend).
  2. Híbrido FastAPI para IA + NestJS para CRUD (paralelo, doble mantenimiento).
  3. Django + DRF (ecosistema Django admin有益 para CRM pero menos TS-coherente).
- **Rationale**:
  - Coherencia end-to-end Angular 21 ↔ NestJS con DTOs compartidos es el factor decisivo.
  - Multi-tenant idiomatic via Guards/Interceptors es natural en NestJS.
  - Hedging de IA: micro-servicio Python aislado tiene costo ~0 hoy y manejable en 12-18 meses si aparece.
  - Equipo full-stack TS reduce fricción vs. mixtos Python/Angular.
- **Consequences**:
  - (+) Coherencia de tipos end-to-end con frontend.
  - (+) Idiomatic multi-tenant en NestJS.
  - (+) CLI + scaffolding.
  - (-) Ecosistema IA Python se pierde (mitigado por micro-servicio aislado si hace falta).
  - (-) Curva de aprendizaje NestJS si el equipo no lo conoce.

---

## ADR-002 — Multi-tenant strategy: Shared Database + `tenant_id` + RLS PostgreSQL

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision Makers**: Tech Lead, Backend team
- **Context**:
  - SaaS B2B con potenciales 1000s de tenants pequeños (clínicas, ferreterías).
  - Nichos no altamente regulados (salvo clínicas — ver future tiers).
  - Necesitamos reporting cross-tenant (`GROUP BY tenant_id`).
- **Decision**:
  - **Shared schema con `tenant_id` en todas las tablas de dominio**.
  - **RLS PostgreSQL activado** desde día 1 como defense-in-depth.
  - **Schema-per-tenant reservado para tier Enterprise/regulated** (~5% de tenants).
- **Alternatives**:
  1. DB-per-tenant → costo Neon/Supabase multiplicado, migraciones multiplicadas.
  2. Schema-per-tenant global → `SET search_path` por request en Prisma (complejo).
  3. Shared sin RLS → defensa DI únicamente (riesgo ante bug).
- **Rationale**: equilibrio costo/aislamiento correcto para 95% de nichos.
- **Consequences**:
  - (+) Una sola migración por feature.
  - (+) Reporting cross-tenant trivial.
  - (+) Costo controlado.
  - (-) Bug en DI puede exponer datos → mitigado con RLS y gate CI anti-fuga.
  - (-) Si se necesita tier Enterprise, migrar schema-per-tenant no es trivial.

---

## ADR-003 — DI en NestJS: Tokens vs class-based

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision Makers**: Backend team
- **Decision**:
  - Usar **String tokens** (`'TaskRepositoryPort'`) para inyectar Ports (interfaces), no class-based DI.
  - Concretions like `TaskPrismaRepository` se inyectan via `useClass`.
- **Rationale**:
  - Interfaces TS no existen en runtime — tokens strings son necesarios para DI.
  - Mantiene DIP visible (puerto vs adapter).
  - Facilita testing via `useValue: mockDeep<TaskRepositoryPort>()`.
- **Consequences**:
  - (+) Clean Architecture respetada.
  - (+) Tests aislados del detalle de infraestructura.
  - (-) Requiere disciplina al importar tokens (alias `@InjectableToken`).

---

## ADR-004 — Aislamiento multi-tenant: Prisma extension + Postgres RLS (defense in depth)

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - **Capa 1**: Prisma extension `tenant-scope` inyecta `WHERE tenantId` automáticamente.
  - **Capa 2**: RLS PostgreSQL bloquea fugas si la capa 1 falla.
  - **NO** se usa exclusively uno de los dos.
- **Rationale**:
  - Prisma extension es DX-friendly y aplica filtros sin explicitarlos en cada query.
  - RLS es definitive (Postgres lo hace incluso si el código no lo hace).
- **Consequences**:
  - (+) Aislamiento robusto.
  - (-) Compejidad inicial mayor — Prisma + SQL script RLS en CI.
  - (-) Performance ligeramente menor por RLS check (negligible con índice `tenant_id`).

---

## ADR-005 — Mixin `AuditMixin` en Prisma: duplicar campos vs generator

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - **Duplicar** los 4 campos (`createdAt`, `updatedAt`, `createdBy`, `updatedBy`) en cada modelo de dominio.
  - NO usar `prisma-generator-mixin` o similar.
- **Rationale**:
  - Prisma no tiene herencia de campos.
  - Generadores añaden tooling y complejidad.
  - Duplicar 4 campos por ~15 modelos = 60 líneas — trivial.
  - Explicit > implicit (SOLID: KISS).
- **Consequences**:
  - (+) Schema legible; sin tooling extra.
  - (+) Migraciones straightforward.
  - (-) DRY teórico — compensado por claridad.

---

## ADR-006 — Cuota de Plan: `SELECT … FOR UPDATE` (pesimist lock)

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - Validación de `plan.max_usuarios` vía `SELECT … FOR UPDATE` en transacción Prisma.
- **Alternatives**:
  1. Optimistic concurrency con `version` field → requiere retry backoff.
  2. Trigger Postgres → no accesible desde app code.
- **Rationale**: cuota es baja contención pero errores graves si se excede.
- **Consequences**:
  - (+) Garantiza cuota incluso con invitaciones concurrentes.
  - (-) Locks breves — acceptable para MVP.

---

## ADR-007 — Pagination envelope `Paginated<T>` vs array suelto

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - Toda lista devuelva `Paginated<T> = { data: T[], total, offset, limit }`.
- **Rationale**:
  - Proyecto FastAPI actual exige dos endpoints (`GET /` y `GET /count`). El envelope los unifica y reduce rutas.
  - Frontend comparte el tipo `Paginated<T>` desde `@saas/shared`.
- **Consequences**:
  - (+) API más simple.
  - (-) Breaking change vs FastAPI actual →_versions controlled por `/api/v1`.

---

## ADR-008 — Errores de validación: 422 (no 400)

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - `ValidationPipe` de NestJS usa `errorHttpStatusCode: 422`.
  - Errores custom de negocio → 400.
- **Rationale**: distinción semántica — 400 es "request malformado semánticamente", 422 es "DTO invalido". Está alineado con REST modernos (GitHub, Stripe).

---

## ADR-009 — Partición de `audit_logs` por mes (futuro)

- **Status**: Proposed (cuando supere 1M filas)
- **Date**: 2026-07-06
- **Decision**:
  - `PARTITION BY RANGE (timestamp)` con mensuales de `audit_logs`.
- **Rationale**: tablas de auditoría crecen indefinidamente; partición facilita archiving (DROP partition) sin VACUUM.
- **Consequences**:
  - (+) Operativo más simple.
  - (-) Requiere Prisma raw + script de mantenimiento CI.

---

## ADR-010 — AsyncLocalStorage vs request-scoped providers

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - **Usar AsyncLocalStorage** para propagar `TenantContext`, `AuditContext`, `RequestId`.
  - **No** usar request-scoped providers (`Scope.REQUEST`) de NestJS.
- **Rationale**: request-scoped providers en NestJS tienen overhead significativo; ALS es tan eficiente como instance-per-request en la mayoría de cargas, y reutilizable en workers/BullMQ.
- **Consequences**:
  - (+) Performance óptima.
  - (+) Funciona en jobs asíncronos.
  - (-) Learning curve para devs no familiarizados con ALS.

---

## ADR-011 — E2E con PostgreSQL real (Testcontainers) vs SQLite in-memory

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - E2E siempre con PostgreSQL real vía Testcontainers (Dinámic in CI).
  - Unit/Integration tests pueden mockear Prisma sin DB.
- **Rationale**:
  - RLS no existe en SQLite.
  - JSONB, partial indexes, `SET LOCAL` difieren.
  - El FastAPI actual usa SQLite para tests — pero NestJS multi-tenant necesita Postgres.
- **Consequences**:
  - (+) Tests reflejan producción.
  - (-) E2E más lento (~30s vs 5s) — aceptable.

---

## ADR-012 — Gate CI anti-fuga de tenant (no negociable)

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - Test E2E `tenant-isolation.e2e-spec.ts` debe estar siempre verde. PR que lo rompe no se mergea.
- **Rationale**: fugas de tenant son el riesgo mayor de un SaaS multi-tenant.
- **Consequences**:
  - (+) Garantía de aislamiento.
  - (-) Pudo silenciar bugs en refactor si no se mantiene actualizado.

---

## ADR-013 — ESLint custom anti `prisma.<model>.findMany` sin `where`

- **Status**: Proposed
- **Date**: 2026-07-06
- **Decision**:
  - ESLint rule custom falla si un service hace `prisma.<model>.findMany` (sin where o sin `scopedWhere()`).
- **Rationale**: complemento del gate E2E — captura antes de runtime.
- **Consequences**:
  - (+) Detecta fugas en code review.
  - (-) Implementación custom rule — costo inicial.

---

## ADR-014 — Logger: `nestjs-pino` vs `winston-nestjs`

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**: `nestjs-pino`.
- **Rationale**: pino es más rápido, JSON nativo, ALS-friendly, integración NestJS pulida.

---

## ADR-015 — Throttler storage: Redis vs in-memory

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - **Redis** (`@nestjs/throttler-storage-redis`) en prod. **In-memory** en tests.
- **Rationale**: Multi-pod/K8s requiere estado compartido para rate limit.

---

## ADR-016 — JWT signing: HS256 (now) → RS256 (future microservices)

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - HS256 ahora (monolito).
  - Migrar a RS256 si aparecen microservices que validan JWT (key pair pub/priv).
- **Rationale**: HS256 simple; RS256 necesario solo cuando hay clientes que validan el token en otros servicios.

---

## ADR-017 — Monorepo: Nx

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**: Nx workspace con `apps/api`, `apps/web`, `libs/shared`.
- **Rationale**:
  - DTOs TS compartidos necesita same-repo.
  - Nx fuerza project graph, cache de tasks, generators.
  - Para <5 devs Nx es canónico.

---

## ADR-018 — Husky + lint-staged pre-commit

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**: Pre-commit ejecuta eslint + prettier + tsc en staged files.
- **Rationale**: captura errores antes de review.

---

## ADR-019 — ETL migrated como Job BullMQ (no cron plan)

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - `sync-siger.service.ts` invocable via `@nestjs/schedule` (cron) en MVP.
  - Migrar a BullMQ queue cuando crezca volumen (retries, observability).
- **Rationale**: BullMQ necesita Redis; cron simple en MVP suficiente.

---

## ADR-020 — Refresh token rotation: blacklist + version

- **Status**: Accepted
- **Date**: 2026-07-06
- **Decision**:
  - Cada refresh invalida el anterior (blacklist en `revoked_tokens`).
  - Mantiene el esquema del FastAPI actual.
- **Alternatives**:
  - `tokens_version` en `User` + JWT claim `v`: reject all previous con bump de version.
  - Decisión: blacklist para granularidad.
- **Rationale**: hereda patrón probado en FastAPI.

---

## Plantilla para futuros ADRs

```markdown
## ADR-XXX — Title

- **Status**: Proposed | Accepted | Rejected | Deprecated
- **Date**: YYYY-MM-DD
- **Decision Makers**:
- **Context**:
- **Decision**:
- **Alternatives**:
- **Rationale**:
- **Consequences**:
  - (+)
  - (-)
```

---

## Índice

| ADR | Tema | Status |
|---|---|---|
| 001 | NestJS vs FastAPI | Accepted |
| 002 | Multi-tenant strategy | Accepted |
| 003 | DI tokens vs class-based | Accepted |
| 004 | Aislamiento layers | Accepted |
| 005 | Mixin Prisma | Accepted |
| 006 | Cuota con FOR UPDATE | Accepted |
| 007 | Pagination envelope | Accepted |
| 008 | 422 para validation | Accepted |
| 009 | Partición audit por mes | Proposed |
| 010 | AsyncLocalStorage | Accepted |
| 011 | E2E con Postgres real | Accepted |
| 012 | Gate anti-fuga | Accepted |
| 013 | ESLint rule custom | Proposed |
| 014 | pino vs winston | Accepted |
| 015 | Throttler-storage-redis | Accepted |
| 016 | HS256 vs RS256 | Accepted |
| 017 | Nx monorepo | Accepted |
| 018 | Husky pre-commit | Accepted |
| 019 | ETL con BullMQ | Accepted |
| 020 | Refresh rotation | Accepted |
