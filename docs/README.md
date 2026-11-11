# Uyuni Backend — Documentación

## Documentación de referencia (FastAPI actual)

Esta carpeta contiene la documentación del proyecto FastAPI actual (legacy):
- **[`deployment/`](./deployment/README.md)**: Suite completa de despliegue, infraestructura en la nube y replicación para nuevas empresas (marca blanca)
  - `CLIENT_REPLICATION_PLAYBOOK.md` (Manual de replicación y despliegue dedicado por empresa)
  - `RENDER_DEPLOYMENT_GUIDE.md` (Guía de despliegue en Render.com con Docker y UptimeRobot)
  - `SERVERLESS_DEPLOYMENT_GUIDE.md` (Guía de arquitectura serverless en la nube: Neon + Vercel/Render + Cloudflare + Cloudinary)
  - `UBUNTU_VPS_DEPLOYMENT_GUIDE.md` (Guía de instalación y despliegue tradicional en VPS Ubuntu)
- `COMMERCE_MODULE_GUIDE.md` (y suite completa en [`docs/commerce/`](./commerce/README.md))
- `RBAC_GUIDE.md`, `AUTHENTICATION_GUIDE.md`, `ALEMBIC_GUIDE.md`, `AUDIT_GUIDE.md`
- `ASSETS_MODULE_GUIDE.md`, `CORE_MODULE_GUIDE.md`, `QUERY_SYSTEM_GUIDE.md`
- `DEVELOPER_GUIDE.md`, `EXCEPTION_HANDLING_GUIDE.md`, `FRONTEND_AUTH_GUIDE.md`
- `OBSERVABILITY_GUIDE.md`, `QUALITY_GUIDE.md`, `SOLID_GUIDE.md`, `TESTING_GUIDE.md`
- `DESIGN_PATTERNS_GUIDE.md`, `CODE_STANDARDS_REVIEW.md`
- `AUTH_ANALYSIS.md`, `PROJECT_ANALYSIS.md`, `PROJECT_ANALYSIS_REVIEW.md`

## 🆕 Spec Driven Development (SDD) — Migración a NestJS

> La carpeta [`nestjs-migration/`](./nestjs-migration/00-SDD-OVERVIEW.md) contiene la
> especificación técnica completa para migrar el backend a **NestJS v11 + TypeScript + Prisma**
> como SaaS multi-tenant B2B.

**Lectura recomendada**: empezar por [`nestjs-migration/00-SDD-OVERVIEW.md`](./nestjs-migration/00-SDD-OVERVIEW.md).

## Tabla de especificaciones

| # | Documento | Propósito |
|---|---|---|
| 00 | [SDD Overview](./nestjs-migration/00-SDD-OVERVIEW.md) | Índice + filosofía Spec Driven Development + alcance |
| 01 | [Foundations](./nestjs-migration/01-FOUNDATIONS-SPEC.md) | Objetivos, NFRs, glosario, principos |
| 02 | [Architecture](./nestjs-migration/02-ARCHITECTURE-SPEC.md) | Clean Architecture en NestJS + mapeo FastAPI |
| 03 | [Data](./nestjs-migration/03-DATA-SPEC.md) | Prisma schema, multi-tenant, RLS PostgreSQL |
| 04 | [Auth](./nestjs-migration/04-AUTH-SPEC.md) | JWT, lockout, refresh rotation, login por email |
| 05 | [RBAC](./nestjs-migration/05-RBAC-SPEC.md) | Guards, decorators, módulos y permisos CRUD |
| 06 | [Tenancy](./nestjs-migration/06-TENANCY-SPEC.md) | TenantGuard, plans, cuotas, invitations |
| 07 | [Audit](./nestjs-migration/07-AUDIT-SPEC.md) | Access logs + CDC con Prisma extensions |
| 08 | [Catalogs](./nestjs-migration/08-CATALOGS-SPEC.md) | Catálogos dinámicos + bulk loader |
| 09 | [HTTP API](./nestjs-migration/09-HTTP-API-SPEC.md) | REST v1, versionado, errors, paginación |
| 10 | [Testing](./nestjs-migration/10-TESTING-SPEC.md) | Jest, Testcontainers, gate anti-fuga CI |
| 11 | [Observability](./nestjs-migration/11-OBSERVABILITY-SPEC.md) | Pino, OpenTelemetry, Prometheus, Health |
| 12 | [Security](./nestjs-migration/12-SECURITY-SPEC.md) | Rate limit, helmet, CORS, OWASP Top-10 |
| 13 | [Project Structure](./nestjs-migration/13-PROJECT-STRUCTURE-SPEC.md) | Monorepo Nx, app api, app web, libs/shared |
| 14 | [Migration Playbook](./nestjs-migration/14-MIGRATION-PLAYBOOK.md) | Plan por fases + cronograma + Definition of Done |
| 15 | [ADRs](./nestjs-migration/15-ADRs.md) | Architecture Decision Records |
