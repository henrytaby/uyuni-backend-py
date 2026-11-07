# Recomendación de Stack para SaaS B2B Multi-Tenant desde Cero

## Contexto (decisión del usuario)

- **Núcleo de valor confirmado**: CRUD + Multi-tenant puro, **sin capa de IA/Analítica** a 2-3 años.
- Producto: Core-CRM genérico (clientes, agenda, caja) adaptable a nichos (clínicas, ferreterías, etc.).
- Frontend planificado: **Angular** (TypeScript ecosistema).
- Cuenta nueva: ningún código legacy que migrar.

## Veredicto

**NestJS (TypeScript)** con **Prisma** (o TypeORM) y **PostgreSQL**.

Segunda opción válida: **FastAPI + SQLModel** si el equipo carece de skills TypeScript. Dado que el núcleo NO incluye IA, el argumento pro-Python desaparece y la coherencia frontend/backend (Angular ↔ NestJS en TypeScript) es el factor decisivo.

## Razones (en orden de peso)

1. **Coherencia de tipos end-to-end con Angular** — DTOs compartidos en un monorepo (Nx) o paquete npm `@saas/shared`. Frontend y backend evolucionan en el mismo lenguaje: cero fricción mental, refactor tipo-end-to-end, menos bugs de contrato API.
2. **Ergonomía multi-tenant nativa** — Guards e Interceptors globales en NestJS son idiomáticos para inyectar `tenant_id` en cada request:
   - `TenantGuard` resuelve `tenantId` desde JWT/`X-Tenant-Id` y lo pega al `Request`.
   - `LoggingInterceptor` registra `tenantId` en logs y auditoría sin tocar cada endpoint.
   - `PrismaClient` extensiones (`prisma-tenant`) o middleware Prisma injectan `WHERE tenant_id` automáticamente.
3. **CLI + scaffolding primero en clase** — `nest g resource customers` genera módulo + controller + service + DTOs. Módulos RBAC/audit/tenancy ya listos (`nestjs-tenancy`, `@nestjs/throttler`, `@nestjs/swagger`). Time-to-market MVP inferior a FastAPI para CRUD puro.
4. **DI explícita robusta** — `@Injectable()` + `MODULE_metadata` son más declarativos que los `Depends()` de FastAPI para propagar contexto de tenant (sin ContextVar manual).
5. **Ecosistema empresarial maduro** — TypeORM/Prisma migraciones, Passport-JWT sólido, Jobs (BullMQ), WebSocket (Socket.io). Todo TS, una sola tooling.
6. **Contratación** — un mismo desarrollador TS opera Angular + NestJS (full-stack TS). Reduce headcount y hand-offs vs. equipo dividido Python/Angular.

## Trade-offs aceptados (y por qué son menores aquí)

| Trade-off | Por qué es aceptable en este contexto |
|---|---|
| NO hay ecosistema IA nativo | El usuario confirmó que el valor NO es IA. Si aparece IPA puntual, se expone como microservicio Python aislado. |
| Prisma vs SQL crudo | Para CRUD multi-tenant, Prisma abstrae suficientemente; si noticia joins ticos se necesita SQL crudo, fallback `$queryRaw`. |
| Menor throughput que FastAPI/asyncio | CRUD B2B no es high-throughput; bottleneck será Postgres, no framework. |
| Decoradores verbosos vs Python limpio | Compensado por tipado estricto y refactor herramientas (ts-morph, ESLint). |

## Arquitectura Target (alto nivel)

```
[Nx monorepo]
├── apps/
│   ├── api/                  # NestJS app
│   │   ├── src/
│   │   │   ├── auth/         # JWT, refresh rotation, guards
│   │   │   ├── tenants/      # Plan, Tenant, TenantUser, quota enforcement
│   │   │   ├── tenancy/      # TenantGuard, TenantInterceptor, Prisma extension
│   │   │   ├── rbac/         # @Roles/@Permissions decorators, RbacGuard
│   │   │   ├── audit/        # LoggingInterceptor + AuditEvent entity
│   │   │   ├── crm/          # customers, agenda, cash-register
│   │   │   └── main.ts
│   │   └── prisma/           # schema.prisma + migrations
│   └── web/                  # Angular app
├── libs/
│   └── shared/               # DTOs, enums, constants — TS package consumido por api+web
└── tools/                    # seeds, scripts
```

### Decisiones técnicas concretas (para implementación)

- **ORM**: Prisma (preferido) — schema declarativo, `@tenantId` con cliente extendido, migraciones versionadas; TypeORM si el equipo demanda patron Entity/Repository más próximo a SQLModel.
- **Multi-tenant**: **shared-schema + `tenant_id`** (mismo veredicto que FastAPI). Nunca "database per tenant" para nichos B2B masivos.
- **Aislamiento**: `TenantInterceptor` inyecta `prisma.tenantId` en AsyncLocalStorage; cada query Prisma recibe `where: { tenantId }` automáticamente (prisma extension `tenant-context`). Defensa en profundidad opcional con RLS de PostgreSQL (`SET LOCAL app.tenant_id`).
- **Auth**: `@nestjs/jwt` + `@nestjs/passport`, refresh token rotation en tabla `refresh_tokens`. Payload incluye `{ sub, email, tenantId, role }`.
- **RBAC**: Roles por `tenant_users.rol` (Admin/Empleado/Auditor); `@Roles()` decorator + `RolesGuard`. PermissionChecker equivalente pisado por módulo.
- **Cuota**: Validar `plan.max_usuarios` en `POST /tenants/:id/invitations` con transacción y lock pesimista (`SELECT … FOR UPDATE`).
- **Audit**: `LoggingInterceptor` global captura `(userId, tenantId, action, entity, before, after)` sin repetir lógica por controlador.
- **Frontend**: Angular standalone + Signals, selector de tenant en navbar (`X-Tenant-Id`), interceptores HTTP para JWT.
- **Tests**: Jest (unit) + Supertest (e2e) + Testcontainers (Postgres). Gate CI: cada modelo nuevo sin `tenantId` rompe el build (regla ESLint custom o test de smoke).

## Tareas de Migración/Arranque (ordenado)

> Aplica si se decide arrancar en NestJS. Sustituyendo al plan FastAPI del reporte previo.

1. Scaffold Nx monorepo con `pnpx create-nx-workspace` + preset `nest` (api) y `angular` (web).
2. Configurar Prisma + Postgres local (docker-compose) y el primer schema con Plan, Tenant, User, TenantUser y migración `init`.
3. Implementar `tenancy/TenantInterceptor.ts` + Prisma extension `tenant-context` (AsyncLocalStorage).
4. Implementar `auth/`: registro/login por **email** (NO username), JWT con `{sub,email,tenantId,role}`, refresh rotation y blacklist.
5. Implementar `rbac/RolesGuard` con decorator `@Permissions('crm.customers', 'create')` resuelto desde `tenant_users.rol`.
6. Scaffold recurso `customers` (CRUD multi-tenant), agenda, caja básica — todos con `@UseGuards(TenantGuard, JwtAuthGuard, RolesGuard)`.
7. Endpoint `POST /tenants/:id/invitations` con validación de cuota `plan.max_usuarios` (transacción + lock).
8. `audit/LoggingInterceptor` global con `tenantId` en todos los eventos CDC.
9. `libs/shared` con DTOs TS compartidos entre Angular y Nest (zod-class-validator si se quiere runtime + tipado).
10. CI GitHub Actions: lint, type-check, Jest unit, e2e con Testcontainers, gate anti-fuga de `tenantId`.
11. Despliegue: API en Fly.io/Railway, Postgres en Neon/Supabase, web en Vercel. Migraciones en CI pre-deploy.

## Validación del Plan

- [ ] Cross-check: cada modelo de dominio **Debe** tener `tenantId UUID FK` (test de smoke que enumera entidades Prisma y falla si falta).
- [ ] Cross-check: cada controlador de dominio **Debe** tener `@UseGuards(TenantGuard)` (regla ESLint custom).
- [ ] E2E: usuario del TenantA no puede leer/actualizar Customers del TenantB (assert 404, no 403 para no revelar existencia).
- [ ] E2E: invitar con `plan.max_usuarios = 3` y 3 activos devuelve `409 PLAN_QUOTA_EXCEEDED`.
- [ ] E2E: refresh de `tenantId` con `tenant.is_active=false` devuelve 403.
- [ ] Logs estructurados contienen `tenantId` en 100% de registros de dominio (test de muestreo).

## Riesgos / Decisiones Pospuestas (out of scope aquí)

- **SiRAG/IA aparece a 12+ meses**: exponer microservicio FastAPI aislado vía HTTP interno; NestJS mantiene el dominio multi-tenant CRUD.
- **Stripe billing**: pospuesto a fase 2; schema reserva `subscriptionId` y `currentPeriodEnd` nullable en `Tenant`.
- **RLS PostgreSQL**: opcional defensa en profundidad para tier Enterprise; no en MVP.
- **Real-time (agenda compartida)**: Socket.io en NestJS cuando se requiera; sin impacto en arquitectura multi-tenant.

## Cambios Post-Descubrimiento (decisiones a confirmar más tarde)

- Prisma vs TypeORM (preferido Prisma; confirmar si el equipo demanda patrón Repository activo estilo SQLModel).
- Nx vs monorepo simple (verificar si los DTOs compartidos compensan la complejidad Nx en <5 devs).
- Subdominio vs header `X-Tenant-Id` para resolver tenant (header es más simple para MVP; subdominio cuando haya branding white-label).

## Recomendación Resumida

> **Si arrancaras hoy con CRUD multi-tenant puro (sin IA) y Angular en el frontend: NestJS + Prisma + PostgreSQL.**
> FastAPI sigue siendo válido SOLO si (a) el equipo dominara Python y no TS, o (b) IA apareciera en el roadmap cercano — ninguno aplicable según tu confirmación.
