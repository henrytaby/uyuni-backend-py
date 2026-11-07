# 14 — Migration Playbook

> **Plan por fases para migrar el backend FastAPI actual a NestJS sin romper producción (stride-wise migration) y orden crítico de implementación.**

---

## 1. Estrategia general

**No** es big-bang rewrite. Es **stride-wise migration** con coexistencia temporal:

```
Fase 0: Setup monorepo
   ↓
Fase 1: Auth + Tenancy (NestJS)    → smoke test
   ↓
Fase 2: RBAC + Audit              → smoke test
   ↓
Fase 3: Catalogs                  → smoke test
   ↓
Fase 4: Domain modules (Tasks, Core, Assets)  → 1 a la vez
   ↓
Fase 5: ETL + Platform admin      → smoke test
   ↓
Fase 6: Cut-over final (deprecate FastAPI)
   ↓
Fase 7: Cleanup Frontend (Angular 21 consume new DTOs)
   ↓
Fase 8: Hardening (rate limit, observability, ADRs)
```

Durante las fases 1-5, ambos backends corren en paralelo. La base Postgres es **compartida** solo si el frontend aún usa endpoints FastAPI. **Pero se recomienda BD separada** y migrar datos via `pg_dump | psql`.

---

## 2. Fase 0 — Setup monorepo (Día 1-2)

### Objetivos
- Inicializar Nx workspace.
- Configurar Docker compose (Postgres + Redis + Mailhog).
- Configurar CI base (lint, typecheck).
- Pre-commit hooks (Husky + lint-staged).

### Tareas
1. `pnpx create-nx-workspace@latest uyuni-saas --preset=apps`.
2. `npx nx g @nx/nest:application api`.
3. `npx nx g @nx/angular:application web --standalone`.
4. `pnpm add -D husky lint-staged && npx husky init`.
5. Crear `.env.example`, `docker-compose.yml`.
6. Crear `libs/shared` barrel `@saas/shared`.
7. GitHub Actions: workflow `ci.yml` con lint, typecheck, build.

### Criterios de salida
- `pnpm dev:api` responde `200` en `/health/live`.
- `pnpm dev:web` muestra landing Angular.
- CI verde.

---

## 3. Fase 1 — Auth + Tenancy (Semana 1-2)

### Objetivos
- Implementar `Plan`, `Tenant`, `User`, `TenantUser`, `RevokedToken`, `UserLogLogin` en Prisma.
- Migración inicial con seeds (`Free` plan, demo tenant, admin@demo.local).
- Activar RLS Postgres.
- Login por email.
- Lockout + refresh rotation + blacklist.
- `TenantGuard` + `TenantContextInterceptor`.

### Tareas (orden crítico)
1. `pnpm --filter api prisma init` y escribir `schema.prisma` con tenant + auth (ver `03-DATA-SPEC.md`).
2. `pnpm --filter api prisma migrate dev --name init`.
3. Aplicar `prisma/sql/rls.sql` (script idempotente).
4. Seeds: `plans.seed.ts`, `demo-tenant.seed.ts`.
5. Implementar `AuthModule` con ports/adapters (`JwtPort`, `BcryptPort`, `UserRepositoryPort`).
6. Implementar `AuthController`: login, refresh, logout, me, me/tenants, PUT tenant-context.
7. Implementar `TenancyModule` con `TenantGuard`, `TenantContextInterceptor`, `tenantAls`.
8. Implementar `TenantsController`: POST (signup), GET /:id, POST /:id/invitations (con cuota y lock pesimista).
9. Tests: AUTH-1..AUTH-12 (ver `04-AUTH-SPEC.md §9`).
10. Tests: TEN-1..TEN-8 (con cuota).
11. **Gate anti-fuga**: `tenant-isolation.e2e-spec.ts` corriendo.

### Criterios de salida
- 2 tenants creados vía API, usuarios invitan, login exitoso.
- `Rate-After` headers en lockout.
- Cross-tenant task access devuelve 404.
- Coverage de `auth/*` + `tenancy/*` >= 90%.

### Pendientes explícitos
- Si la base legacy tiene `users.username` unique, migrar a nullable y mantener `email` unique.
- Hacer `pg_dump` de la base legacy y migrar solo `users.email`, `users.password_hash` (no tokens).
- INVALIDACION: rotar `JWT_SECRET` para forzar re-login.

---

## 4. Fase 2 — RBAC + Audit (Semana 3)

### Objetivos
- `Roles`, `Modules`, `RoleModules` modelos.
- `PermissionsGuard` + `@Permissions` decorator.
- `PermissionsService` con cache en memoria opcional.
- `AccessAuditInterceptor` + `cdcExtension + auditFieldsExtension`.
- Seeds: roles (`Admin`, `Empleado`, `Auditor`), modules (`tasks_general`, etc.), role-modules.

### Tareas
1. Migrar `Role`, `Module`, `ModuleGroup`, `RoleModule` al Prisma schema.
2. Migración; aplicar RLS solo si quieres segregar por tenant (`role_modules` es global).
3. Implementar `RbacModule`, `PermissionsGuard`, `PermissionsService`.
4. Implementar `AuditModule` con `AccessAuditInterceptor` global + Prisma extensions CDC + audit fields.
5. Tests RBAC: RBAC-1..RBAC-8.
6. Tests AUD-1..AUD-8.

### Criterios de salida
- Empleado recibe 403 al DELETE.
- Auditor recibe 403 al CREATE.
- Audit log se inserta por CREATE/UPDATE/DELETE con `tenant_id` y `old/new`.
- `audit_logs` no se puede modificar.

---

## 5. Fase 3 — Catalogs (Semana 3)

### Tareas
1. Implementar `CatalogsModule` con `CatalogRegistry`, `CatalogsService`, `CatalogsController`.
2. Portar `GerenciasProvider` y `DepartamentosProvider` con multi-tenant.
3. Validar `POST /catalogs/bulk` y `GET /catalogs/{name}`.
4. Tests CAT-1..CAT-8.

### Criterios de salida
- Bulk resuelve 10 catalogos en < 200ms.
- Cross-tenant garantizado por test CAT-7.

---

## 6. Fase 4 — Módulos de dominio (Semanas 4-6)

### Orden recomendado (de menos a más complejo)

#### 4.1 Tasks (Semana 4, 2 días)
1. Generar `nest g resource tasks` (`apps/api/src/modules/tasks/`).
2. `TaskRepositoryPort` + `TaskPrismaRepository extends TenantScopedRepository<Task>`.
3. `TasksService` + DTOs en `@saas/shared`.
4. `TasksController` con `@Permissions('tasks_general', ...)`.
5. Tests unit + integration + e2e.

#### 4.2 Core (Semana 5, 3 días)
- OrgUnits (hierarchical con `parent_id`).
- StaffPositions (FK a orgUnit).
- Staff (FK a position y orgUnit).
- Tests para relaciones jerárquicas.

#### 4.3 Assets (Semana 6, 4 días)
FixedAsset (con M2M `Act` via `AssetActLink`).
Areas, AssetGroups, AssetStatuses, Institutions, Acts.
Mantener relaciones complejas (ej. `assignedStaff` y `custodianStaff` self-referencia en `Staff`).

### Criterios de salida por submódulo
- CRUD completo + endpoint `/count` ya envuelto en `Paginated<T>`.
- Lint: ningún `prisma.<model>.findMany` sin `where.tenantId` (regla ESLint custom).
- Tests E2E de cada submódulo.
- Coverage del módulo >= 90%.

---

## 7. Fase 5 — ETL + Platform Admin (Semana 7)

### ETL — `sync-siger.service.ts`

Portar `scripts/sync_siger.py`:
1. Conexión a DB externa via `external-datasource.adapter.ts` (`mysql2` o `pg`).
2. Helper `upsert(external_id, ...)` con `ON CONFLICT`.
3. Helper `softDelete(missing_ids)` que pone `is_active=false`.
4. Mapeo `external_id` (int) → UUID interno.
5. Scheduling con `@nestjs/schedule` (cron diario) o BullMQ job (mejor para retries).

### Platform Admin endpoints
- `GET /api/v1/platform/tenants` — lista todos.
- `PUT /api/v1/platform/tenants/:id/suspend`.
- `PUT /api/v1/platform/tenants/:id/plan`.

Protección: `@PlatformAdmin()` decorator with check `User.isSuperuser=true`.

---

## 8. Fase 6 — Cut-over

### Estrategia de switchover
1. Cambiar DNS/routing de `api.uyuni.local` → nuevo NestJS.
2. Mantener FastAPI en `api-legacy.uyuni.local` por 2 semanas (read-only).
3. Monitorear Sentry + logs.
4. Deprecate FastAPI en README principal tras 30 días sin errores.

### Rollback plan
- Si hay errores críticos, revertir DNS.
- DB **compartida** en Fase 6 (no se/resetfea schema) — Prisma migraciones son no-destructivas vía `prisma migrate deploy`.
- RLS Postgres ya estaba activo; FastAPI lee sin RLS → ignora.

---

## 9. Fase 7 — Frontend cleanup

### Cambios en Angular 21
- Sustituir DTOs inline por `@saas/shared`.
- Login cambia de `{ username, password }` → `{ email, password }`.
- Añadir selector de tenant (`httpResource` a `/api/v1/auth/me/tenants`).
- Headers: `X-Tenant-Id` en cada request.
- Renovar `access_token` catch-401 interceptor con refresh.

---

## 10. Fase 8 — Hardening

### Tareas pendientes del proyecto FastAPI que NestJS cubre desde día 1
- Rate limit — `@nestjs/throttler` global + Redis storage.
- Health endpoints — `/health/live`, `/health/ready`.
- Observability — pino + OTel + Sentry.
- Connection pooling — PrismaClient por tenant (en el futuro) si hace falta.

### Tests de carga
- `k6` script simulando 1000 tenants × 10 req/s durante 10 min.
- SLO: p95 < 300ms.

---

## 11. Cronograma (estimación)

| Fase | Duración | Recurso | Esfuerzo |
|---|---|---|---|
| 0 — Setup | 2 días | 1 dev | 16h |
| 1 — Auth + Tenancy | 2 semanas | 2 devs | 160h |
| 2 — RBAC + Audit | 1 semana | 1 dev | 40h |
| 3 — Catalogs | 3 días | 1 dev | 24h |
| 4 — Domain modules | 3 semanas | 2 devs | 240h |
| 5 — ETL + Platform | 1 semana | 1 dev | 40h |
| 6 — Cut-over | 1 semana | 2 devs | 80h |
| 7 — Frontend cleanup | 1 semana | 1 dev Angular | 40h |
| 8 — Hardening | 1 semana | 1 dev + SRE | 40h |
| **Total** | **~10 semanas** | **2 devs backend + 1 Angular** | **~680h** |

> Equipo ajeno: con 1 dev dedicado únicamente y sin paralelizar, multiplicar por ~3 = ~30 semanas.

---

## 12. Riesgos y mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Datos legacy no migran limpiamente | Media | Alto | Script de migración con tests + dry-run previo |
| Bug de aislamiento de tenant en Prisma extension | Media | Crítico | **CI gate anti-fuga** + RLS Postgres defense-in-depth |
| Performance de Prisma findMany con tenant_filter | Baja | Medio | Índice `(tenant_id)` en cada tabla; explain analyze |
| Token refresh rotation interrumpe frontend | Media | Medio | Mantener ruta legacy `/api/auth/refresh` durante 2 semanas con compat hacia atrás |
| Equipo sin experiencia NestJS | Media | Medio | Onboarding + pair sessions + revisión de specs |
| Rate limit en producción accede a Redis | Baja | Medio | Throttler-storage-redis listo desde Fase 0 |

---

## 13. Definition of Done (por fase)

Para marcar una fase como completada:

- [ ] Tests de la fase pasando en CI.
- [ ] Coverage >= 90% en código añadido.
- [ ] Lint + type-check sin errores.
- [ ] OpenAPI generada actualizada (`/api/v1/docs`).
- [ ] Spec correspondiente actualizado si hubo desviación documentada en ADR.
- [ ] Review por al menos 1 senior.
- [ ] Despliegue en staging exitoso.
- [ ] Smoke test post-deploy verificando endpoints clave.

---

## 14. Rollback playbook

### Trigger
- Cualquier error P0 en producción dentro de 24h tras cut-over.

### Pasos
1. Revertir DNS/routing a `api-legacy`.
2. Anunciar en Slack, incidente abierto.
3. Analyzar logs en Sentry + ELK.
4. Hotfix en NestJS o revertir deployment (Github Actions redeploy `latest`).
5. Post-mortem al día siguiente.

---

## 15. Comunicación y status

- **GitHub Project board** con columnas: `Backlog` / `Spec` / `Implementation` / `PR` / `Staging` / `Done`.
- Cada fase = milestone con issues hijas.
- Daily standup con Block/Unblock.
- Spec review todos los viernes (`paired with` QA).

---

## 16. Referencias

- Spec dependiente por fase: ver `00-SDD-OVERVIEW.md`.
- Decisiones: `15-ADRs.md`.
- Memoria legacy: `.kilo/rules/memory-bank/progress.md` (estado actual FastAPI).
