# Spec Driven Development (SDD) — Migración a NestJS Enterprise

> **Documento maestro de la especificación técnica para migrar Uyuni Backend de FastAPI/Python a NestJS/TypeScript.**
> Este conjunto de documentos define **qué** construir y **cómo**, no implementación de código.
> La implementación se deriva siguiendo cada doc en orden.

---

## 📋 Tabla de Contenidos

| # | Documento | Propósito | Audiencia |
|---|---|---|---|
| 00 | `00-SDD-OVERVIEW.md` | Este índice + filosofía SDD + alcance | Todos |
| 01 | `01-FOUNDATIONS-SPEC.md` | Objetivos, no-funcionales, glosario, principios | Product Owner + Architects |
| 02 | `02-ARCHITECTURE-SPEC.md` | Clean Architecture + NestJS idiomatic mapping | Architects + Tech Leads |
| 03 | `03-DATA-SPEC.md` | Modelo de datos, Prisma schema, multi-tenant, RLS | DBAs + Backend |
| 04 | `04-AUTH-SPEC.md` | Autenticación JWT, lockout, rotación, context | Backend + Security |
| 05 | `05-RBAC-SPEC.md` | RBAC con tenant + módulos + permisos CRUD | Backend + Security |
| 06 | `06-TENANCY-SPEC.md` | Multi-tenant, plans, invitations, quotas | Architects + Backend |
| 07 | `07-AUDIT-SPEC.md` | Access logging + CDC + structured logging | Backend + Compliance |
| 08 | `08-CATALOGS-SPEC.md` | Catálogos dinámicos + batch loader | Backend + Frontend |
| 09 | `09-HTTP-API-SPEC.md` | Contrato REST, versionado, errores, paginación | Frontend + Backend |
| 10 | `10-TESTING-SPEC.md` | Pirámide, Jest, Testcontainers, gates CI | QA + Backend |
| 11 | `11-OBSERVABILITY-SPEC.md` | Structured logs, Health, Métricas | DevOps + SRE |
| 12 | `12-SECURITY-SPEC.md` | Rate limit, CORS, helmet, secrets, OWASP | Security + DevOps |
| 13 | `13-PROJECT-STRUCTURE-SPEC.md` | Monorepo Nx, librería shared, módulos | Todos |
| 14 | `14-MIGRATION-PLAYBOOK.md` | Plan por fasesٜfrom FastAPI a NestJS | Tech Lead + PM |
| 15 | `15-ADRS.md` | Architecture Decision Records | Architects |

---

## 🎯 Filosofía Spec Driven Development (SDD)

La especificación antecede al código. Antes de levantar NestJS, todo agente/desarrollador
debe cumplir el siguiente ciclo:

```
1. LEER el spec correspondiente
2. DISEÑAR el impacto (ADRs si aplica)
3. IMPLEMENTAR en NestJS con TS
4. VALIDAR con tests del spec (10-TESTING-SPEC.md)
5. ACTUALIZAR el spec si el aprendizaje exigió desviación
```

**Regla de oro**: cualquier cambio que viole un spec debe registrarse como **desviación
documentada** en `15-ADRS.md` con motivo técnico o de negocio explícito.

---

## 🎯 Alcance

### Qué se incluye (in-scope)

- Migración completa del backend a **NestJS v11 + TypeScript 5.x**.
- **Patrimonio funcional preservado** del proyecto FastAPI actual:
  - Auth con JWT + refresh rotation + lockout + blacklist.
  - RBAC con módulos + permisos CRUD + superuser bypass.
  - Audit: Access logging + CDC (Change Data Capture).
  - Catálogos dinámicos (registry + bulk loader).
  - Módulos de dominio: assets, core (org-units, positions, staff), tasks.
  - ETL (sync equivalente a `sync_siger.py`).
- **Patrimonio arquitectónico ampliado** (no presente hoy en FastAPI):
  - Multi-tenant B2B con planes + cuotas.
  - Login estrictamente por **email** (no username).
  - Shared schema + `tenant_id` + RLS PostgreSQL.
  - API versionada `/api/v1`.
  - Health checks (liveness + readiness).
  - Rate limiting por IP/usuario/tenant.
  - Observabilidad con OpenTelemetry.
- Clean Architecture + SOLID + DRY + KISS con estándar NestJS.
-frontend consumidor: **Angular 21** (TS compartido en monorepo Nx).

### Qué se excluye (out-of-scope, postergado)

- Migración del frontend Angular 21 (es objeto de otro spec separado).
- IA / RAG (postergado; si aparece, se añadirá como micro-servicio Python aislado).
- Billing Stripe (reservado en schema pero no implementado).
- Migración de datos históricos de la base SQLite actual (generar dump se
  trata operativamente, no en este spec).

---

## 🧭 Principios Rectores (heredados del proyecto actual)

1. **Clean Architecture** — separación estricta: Domain → Application → Infrastructure → Presentation.
2. **SOLID** — SRP/OCP/LSP/ISP/DIP cumplimiento comprobable.
3. **DRY / KISS** — ningún conocimiento duplicado; complejidad mínima necesaria.
4. **TypeScript estricto** — `strict: true`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`.
5. **Tipado end-to-end** — DTOs compartidos entre Angular 21 y NestJS vía `@saas/shared`.
6. **Idiomatic NestJS** — Modules / Providers / Guards / Interceptors / Pipes; no "FastAPI port".
7. **Security by design** — input validation, RLS PostgreSQL, secrets en Vault, cepa OWASP.
8. **Observabilidad desde día 1** — logs estructurados, traces, métricas, health checks.
9. **Testing no negociable** — gate CI anti-fugas de `tenantId`; 90% coverage en dominio.
10. **Documentación viva** — OpenAPI autogen, ADRs actuales, Mermaid en cada spec.

---

## ⚙️ Stack Tecnológico Final

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | TypeScript | 5.x |
| Framework | NestJS | 11.x |
| ORM | Prisma | 6.x |
| DB | PostgreSQL | 16+ |
| Migraciones | Prisma Migrate | — |
| Validación | `class-validator` + `class-transformer` | — |
| JWT | `@nestjs/jwt` + `@nestjs/passport` | Passport-jwt |
| Hashing | `bcrypt` (Node) | — |
| Logging | `pino` + `nestjs-pino` | — |
| Tests | `Jest` + `supertest` | — |
| E2E DB | Testcontainers | — |
| Lint | ESLint + Prettier | — |
| Monorepo | Nx | 20.x |
| Frontend | Angular | 21.x |
| AI (futuro) | Micro-servicio FastAPI Python aislado | — |

---

## 🧭 Cómo usar estos docs

```
docs/nestjs-migration/
├── 00-SDD-OVERVIEW.md             ← ESTÁS AQUÍ
├── 01-FOUNDATIONS-SPEC.md
├── 02-ARCHITECTURE-SPEC.md
├── 03-DATA-SPEC.md
├── 04-AUTH-SPEC.md
├── 05-RBAC-SPEC.md
├── 06-TENANCY-SPEC.md
├── 07-AUDIT-SPEC.md
├── 08-CATALOGS-SPEC.md
├── 09-HTTP-API-SPEC.md
├── 10-TESTING-SPEC.md
├── 11-OBSERVABILITY-SPEC.md
├── 12-SECURITY-SPEC.md
├── 13-PROJECT-STRUCTURE-SPEC.md
├── 14-MIGRATION-PLAYBOOK.md
└── 15-ADRs.md
```

**Lectura recomendada en orden numérico 01 → 15.** Cada doc cita al anterior cuando aplica.
