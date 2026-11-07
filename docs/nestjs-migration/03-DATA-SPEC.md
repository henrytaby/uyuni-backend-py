# 03 — Data Spec

> **Modelo de datos físico (Prisma/PostgreSQL), multi-tenant con RLS, mixin de auditoría y mapeo del patrimonio SQLModel actual.**

---

## 1. Stack de persistencia

| Capa | Tecnología | Razón |
|---|---|---|---|
| ORM | Prisma 6.x | Schema declarativo, migraciones versionadas, extensiones para multi-tenant |
| Migraciones | Prisma Migrate | `prisma migrate dev` (dev), `prisma migrate deploy` (CI) |
| DB | PostgreSQL 16+ | RLS, JSONB, partial indexes, particiones hash (futuro) |
| Aislamiento | **Shared schema + `tenant_id` + RLS** | Ver ADR-002 |
| IDs | UUIDv7 (default Prisma `uuid()`) | Mismo formato heredado del proyecto actual |

> **NOTA**: Prisma genera `cuid()` por default; este spec exige `uuid()` (UUIDv4/v7 nativo PostgreSQL)
> para mantener compatibilidad con IDs secuenciales-temporales ya usados en el proyecto actual.

---

## 2. Mapeo de modelos SQLModel → Prisma

Los modelos actuales en `app/models/*` y `app/modules/**/models.py` se migran al DSL de Prisma:

| SQLModel (actual) | Prisma (target) |
|---|---|
| `class UserModel(BaseModel, table=True)` con `__tablename__` | `model UserModel { ... }` en `schema.prisma` |
| `Field(primary_key=True, default_factory=uuid.uuid7)` | `id String @id @default(uuid())` |
| `Field(foreign_key="users.id")` | `userId String` + `relation(...)` |
| `Field(index=True, unique=True)` | `@unique` y `@@index([])` |
| `AuditMixin` (created_at, updated_at, created_by_id, updated_by_id) | Trait en Prisma via `mixin` (helpers TS) + extensión |
| `relationships` con `back_populates` | `relation(fields: [userId], references: [id])` + `relation` en el otro modelo |
| UniqueConstraint | `@@unique([])` |

---

## 3. Prisma Schema — Esquema core multi-tenant

```prisma
// apps/api/prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
  // extensions multi-tenant via $extends
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// ─────────────────────────────────────────────────────────────────────
// 1. TENANCY (core SaaS)
// ─────────────────────────────────────────────────────────────────────

model Plan {
  id           String   @id @default(uuid())
  name         String   @unique                      // 'Free','Pro','Enterprise'
  maxUsuarios  Int      @map("max_usuarios")
  precio       Float    @default(0)
  isActive     Boolean  @default(true) @map("is_active")
  createdAt    DateTime @default(now()) @map("created_at")
  updatedAt    DateTime @updatedAt     @map("updated_at")
  tenants      Tenant[]

  @@map("plans")
}

model Tenant {
  id           String   @id @default(uuid())
  name         String
  slug         String   @unique                       // subdomain potential
  isActive     Boolean  @default(true) @map("is_active")
  planId       String   @map("plan_id")
  plan         Plan     @relation(fields: [planId], references: [id])
  createdAt    DateTime @default(now()) @map("created_at")
  updatedAt    DateTime @updatedAt     @map("updated_at")
  createdBy    String?  @map("created_by_id")
  updatedBy    String?  @map("updated_by_id")
  memberships  TenantUser[]
  // domain tables
  users        User[]  // (no - global User. Use memberships)
  @@map("tenants")
}

/// Tabla pivote — User × Tenant × Role
model TenantUser {
  id          String   @id @default(uuid())
  tenantId    String   @map("tenant_id")
  userId      String   @map("user_id")
  rol         String                                   // 'Admin', 'Empleado', 'Auditor', ...
  isActive    Boolean  @default(true) @map("is_active")
  invitedById  String? @map("invited_by_id")
  acceptedAt  DateTime? @map("accepted_at")
  createdAt   DateTime @default(now()) @map("created_at")
  updatedAt   DateTime @updatedAt     @map("updated_at")

  tenant      Tenant   @relation(fields: [tenantId], references: [id])
  user        User     @relation(fields: [userId],   references: [id])

  @@unique([tenantId, userId])                            // no duplicate memberships
  @@index([tenantId])
  @@index([userId])
  @@map("tenant_users")
}

// ─────────────────────────────────────────────────────────────────────
// 2. AUTH (Persona física — global; login por email)
// ─────────────────────────────────────────────────────────────────────

model User {
  id                   String   @id @default(uuid())
  email                String   @unique                        // login
  passwordHash         String   @map("password_hash")
  firstName            String?  @map("first_name")
  lastName             String?  @map("last_name")
  isVerified          Boolean  @default(false) @map("is_verified")
  isActive            Boolean  @default(true)  @map("is_active")
  isSuperuser         Boolean  @default(false) @map("is_superuser")

  // Security
  failedLoginAttempts Int      @default(0) @map("failed_login_attempts")
  lockedUntil         DateTime? @map("locked_until")
  lastLoginAt         DateTime? @map("last_login_at")

  createdAt   DateTime @default(now()) @map("created_at")
  updatedAt   DateTime @updatedAt     @map("updated_at")

  memberships   TenantUser[]
  revokedTokens RevokedToken[]
  logLogins     UserLogLogin[]

  @@map("users")
}

model RevokedToken {
  id        String   @id @default(uuid())
  token     String   @unique
  userId    String   @map("user_id")
  revokedAt DateTime @default(now()) @map("revoked_at")
  user      User     @relation(fields: [userId], references: [id])
  @@index([userId])
  @@map("revoked_tokens")
}

model UserLogLogin {
  id              String   @id @default(uuid())
  userId          String?  @map("user_id")
  username        String?                                   // email intentado
  token           String?
  tokenExpiration DateTime? @map("token_expiration")
  ipAddress       String   @map("ip_address")
  hostInfo        String   @map("host_info")
  isSuccessful    Boolean  @map("is_successful")
  loggedOutAt     DateTime? @map("logged_out_at")
  createdAt       DateTime @default(now()) @map("created_at")
  user           User?     @relation(fields: [userId], references: [id])

  @@index([userId])
  @@map("user_log_logins")
}

// ─────────────────────────────────────────────────────────────────────
// 3. RBAC (Roles + Módulos por Tenant)
// ─────────────────────────────────────────────────────────────────────

model Role {
  id          String   @id @default(uuid())
  name        String
  slug        String   @unique
  description String?
  isActive    Boolean  @default(true) @map("is_active")
  icon        String?
  sortOrder   Int?     @map("sort_order")
  createdAt   DateTime @default(now()) @map("created_at")
  updatedAt   DateTime @updatedAt     @map("updated_at")
  roleModules RoleModule[]

  @@map("roles")
}

model ModuleGroup {
  id          String   @id @default(uuid())
  name        String   @unique
  slug        String   @unique
  description String?
  sortOrder   Int?     @map("sort_order")
  icon        String?
  isActive    Boolean  @default(true) @map("is_active")
  modules     Module[]

  @@map("module_groups")
}

model Module {
  id          String   @id @default(uuid())
  name        String   @unique
  slug        String   @unique
  description String?
  isActive    Boolean  @default(true) @map("is_active")
  icon        String?
  route       String?
  sortOrder   Int?     @map("sort_order")
  groupSlug   String?  @map("group_slug")
  group       ModuleGroup? @relation(fields: [groupSlug], references: [slug])
  roleModules RoleModule[]

  @@map("modules")
}

model RoleModule {
  id          String   @id @default(uuid())
  description String?
  isActive    Boolean  @default(true) @map("is_active")

  canCreate   Boolean  @default(false) @map("can_create")
  canUpdate   Boolean  @default(false) @map("can_update")
  canDelete   Boolean  @default(false) @map("can_delete")
  scopeAll    Boolean  @default(false) @map("scope_all")

  roleSlug    String?  @map("role_slug")
  role        Role?    @relation(fields: [roleSlug], references: [slug])
  moduleSlug  String?  @map("module_slug")
  module      Module?  @relation(fields: [moduleSlug], references: [slug])

  createdAt   DateTime @default(now()) @map("created_at")
  updatedAt   DateTime @updatedAt     @map("updated_at")

  @@unique([roleSlug, moduleSlug])
  @@map("role_modules")
}

// ─────────────────────────────────────────────────────────────────────
// 4. AUDIT (heredado del proyecto actual)
// ─────────────────────────────────────────────────────────────────────

model AuditLog {
  id          String   @id @default(uuid())
  tenantId    String?  @map("tenant_id")                     // NEW: multi-tenant
  userId      String?  @map("user_id")
  username    String?
  action      String                                       // 'CREATE','UPDATE','DELETE','ACCESS'
  entityType  String   @map("entity_type")                   // 'Task','User','Endpoint'
  entityId    String?  @map("entity_id")
  changes     Json?
  ipAddress   String?  @map("ip_address")
  userAgent   String?  @map("user_agent")
  timestamp   DateTime @default(now()) @map("timestamp")

  @@index([tenantId, timestamp])
  @@index([userId])
  @@map("audit_logs")
}

// ─────────────────────────────────────────────────────────────────────────
// 5. DOMAIN TABLES — todas con tenant_id (TenantMixin)
// ─────────────────────────────────────────────────────────────────────

// TASKS
model Task {
  id          String   @id @default(uuid())
  tenantId    String   @map("tenant_id") @tenantScoped
  title       String
  description String?
  completed   Boolean  @default(false)
  isActive    Boolean  @default(true) @map("is_active")   // soft-delete
  createdBy   String?  @map("created_by_id")
  updatedBy   String?  @map("updated_by_id")
  createdAt   DateTime @default(now()) @map("created_at")
  updatedAt   DateTime @updatedAt     @map("updated_at")

  tenant      Tenant   @relation(fields: [tenantId], references: [id])
  @@index([tenantId])
  @@map("tasks")
}

// ORG UNITS (Core)
model OrgUnit {
  id                 String   @id @default(uuid())
  tenantId           String   @map("tenant_id") @tenantScoped
  name               String
  parentId           String?  @map("parent_id")
  externalId         Int?     @map("external_id")          // ETL mapping
  itemNumber         Int?     @map("item_number")
  externalParentId   Int?     @map("external_parent_id")
  isActive           Boolean  @default(true) @map("is_active")
  createdBy          String?  @map("created_by_id")
  updatedBy          String?  @map("updated_by_id")
  createdAt          DateTime @default(now()) @map("created_at")
  updatedAt          DateTime @updatedAt     @map("updated_at")
  tenant             Tenant   @relation(fields: [tenantId], references: [id])
  positions          StaffPosition[]
  parent             OrgUnit? @relation("OrgUnitParent", fields: [parentId], references: [id])
  children           OrgUnit[] @relation("OrgUnitParent")

  @@index([tenantId])
  @@map("core_org_unit")
}

model StaffPosition {
  id           String   @id @default(uuid())
  tenantId     String   @map("tenant_id") @tenantScoped
  name         String
  orgUnitId    String?  @map("org_unit_id")
  externalId   Int?     @map("external_id")
  isActive     Boolean  @default(true) @map("is_active")
  createdAt    DateTime @default(now()) @map("created_at")
  updatedAt    DateTime @updatedAt     @map("updated_at")
  orgUnit      OrgUnit? @relation(fields: [orgUnitId], references: [id])
  tenant       Tenant   @relation(fields: [tenantId], references: [id])
  staff        Staff[]
  @@index([tenantId])
  @@map("core_staff_position")
}

model Staff {
  id           String   @id @default(uuid())
  tenantId     String   @map("tenant_id") @tenantScoped
  firstName    String   @map("first_name")
  lastName     String   @map("last_name")
  documentNumber String? @map("document_number")
  positionId   String?  @map("position_id")
  externalId   Int?     @map("external_id")
  isActive     Boolean  @default(true) @map("is_active")
  createdAt    DateTime @default(now()) @map("created_at")
  updatedAt    DateTime @updatedAt     @map("updated_at")
  position     StaffPosition? @relation(fields: [positionId], references: [id])
  tenant       Tenant   @relation(fields: [tenantId], references: [id])
  @@index([tenantId])
  @@map("core_staff")
}

// ASSETS DOMAIN
model Institution {
  id         String   @id @default(uuid())
  tenantId   String   @map("tenant_id") @tenantScoped
  name       String
  isActive   Boolean  @default(true) @map("is_active")
  createdAt  DateTime @default(now()) @map("created_at")
  updatedAt  DateTime @updatedAt     @map("updated_at")
  tenant     Tenant   @relation(fields: [tenantId], references: [id])
  @@index([tenantId])
  @@map("assets_institution")
}

model Area {
  id            String   @id @default(uuid())
  tenantId      String   @map("tenant_id") @tenantScoped
  name          String
  institutionId String?  @map("institution_id")
  isActive      Boolean  @default(true) @map("is_active")
  createdAt     DateTime @default(now()) @map("created_at")
  updatedAt     DateTime @updatedAt     @map("updated_at")
  institution   Institution? @relation(fields: [institutionId], references: [id])
  tenant        Tenant   @relation(fields: [tenantId], references: [id])
  fixedAssets   FixedAsset[]
  @@index([tenantId])
  @@map("assets_area")
}

model AssetGroup {
  id          String   @id @default(uuid())
  tenantId    String   @map("tenant_id") @tenantScoped
  name        String
  isActive    Boolean  @default(true) @map("is_active")
  createdAt   DateTime @default(now()) @map("created_at")
  updatedAt   DateTime @updatedAt     @map("updated_at")
  tenant      Tenant   @relation(fields: [tenantId], references: [id])
  fixedAssets FixedAsset[]
  @@index([tenantId])
  @@map("assets_asset_group")
}

model AssetStatus {
  id           String   @id @default(uuid())
  tenantId     String   @map("tenant_id") @tenantScoped
  name         String
  isActive     Boolean  @default(true) @map("is_active")
  createdAt    DateTime @default(now()) @map("created_at")
  updatedAt    DateTime @updatedAt     @map("updated_at")
  tenant       Tenant   @relation(fields: [tenantId], references: [id])
  fixedAssets  FixedAsset[]
  @@index([tenantId])
  @@map("assets_asset_status")
}

model Act {
  id           String   @id @default(uuid())
  tenantId     String   @map("tenant_id") @tenantScoped
  code         String
  description  String?
  date         DateTime
  isActive     Boolean  @default(true) @map("is_active")
  createdAt    DateTime @default(now()) @map("created_at")
  updatedAt    DateTime @updatedAt     @map("updated_at")
  tenant       Tenant   @relation(fields: [tenantId], references: [id])
  fixedAssets  FixedAsset[]   @relation("AssetActLink")
  @@index([tenantId])
  @@map("assets_act")
}

model AssetActLink {
  fixedAssetId String @map("fixed_asset_id")
  actId        String @map("act_id")
  fixedAsset   FixedAsset @relation(fields: [fixedAssetId], references: [id])
  act          Act        @relation(fields: [actId], references: [id])

  @@id([fixedAssetId, actId])
  @@map("assets_asset_act_link")
}

model FixedAsset {
  id                    String   @id @default(uuid())
  tenantId              String   @map("tenant_id") @tenantScoped
  oldCode               String?  @map("old_code")
  newCode               String?  @map("new_code")
  description           String
  serialNumber          String?  @map("serial_number")
  locationDetail        String?  @map("location_detail")
  observations          String?
  isSaf                 Boolean  @default(true) @map("is_saf")
  isPhysicallyVerified  Boolean  @default(false) @map("is_physically_verified")
  isDecommissioned      Boolean  @default(false) @map("is_decommissioned")
  registeredAt          DateTime? @map("registered_at")
  sourceFiles           String?  @map("source_files")
  groupId               String   @map("group_id")
  statusId              String   @map("status_id")
  areaId                String   @map("area_id")
  orgUnitId             String   @map("org_unit_id")
  assignedStaffId       String?  @map("assigned_staff_id")
  custodianStaffId      String?  @map("custodian_staff_id")
  createdAt             DateTime @default(now()) @map("created_at")
  updatedAt             DateTime @updatedAt     @map("updated_at")
  createdBy             String?  @map("created_by_id")
  updatedBy             String?  @map("updated_by_id")

  group                 AssetGroup @relation(fields: [groupId], references: [id])
  status                AssetStatus @relation(fields: [statusId], references: [id])
  area                  Area        @relation(fields: [areaId], references: [id])
  orgUnit               OrgUnit     @relation(fields: [orgUnitId], references: [id])
  assignedStaff         Staff?      @relation("AssignedStaff", fields: [assignedStaffId], references: [id])
  custodianStaff        Staff?      @relation("CustodianStaff", fields: [custodianStaffId], references: [id])
  acts                  Act[]       @relation("AssetActLink")
  tenant                Tenant      @relation(fields: [tenantId], references: [id])

  @@index([tenantId])
  @@map("assets_fixed_asset")
}
```

> El atributo `@tenantScoped` arriba **es una convención** (no nativa de Prisma).
> Se materializa vía una extensión de Prisma Client (ver §6) que añade `WHERE tenant_id = X` automáticamente.

---

## 4. Multi-tenant con Row-Level Security (RLS) de PostgreSQL

### 4.1. Política RLS — script idempotente a aplicar tras `prisma migrate deploy`

```sql
-- prisma/sql/rls.sql  (ejecutado en CI post-migrate)

ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_isolation ON tasks;
CREATE POLICY tenant_isolation ON tasks
  USING (tenant_id = current_setting('app.tenant_id', true)::uuid);

-- Repetir por cada tabla tenant-scoped:
-- core_org_unit, core_staff_position, core_staff,
-- assets_institution, assets_area, assets_asset_group, assets_asset_status,
-- assets_act, assets_fixed_asset
```

### 4.2. Cómo se inyecta `app.tenant_id` desde NestJS

**Importante**: Prisma no soporta `SET LOCAL` por request de forma nativa. Dos estrategias:

1. **Recomendada**: Prisma extension que envuelve `query` y añade `where: { tenantId }` automáticamente en el cliente JS. No depende de RLS.
2. **Defensa en profundidad (Postgres RLS) usando `$executeRawUnsafe`**: cada transacción Prisma participa en `$transaction` con un prefijo:

```ts
prisma.$transaction(async (tx) => {
  await tx.$executeRaw`SET LOCAL app.tenant_id = ${tenantId}`;
  return tx.task.create({ data: { ...dto, tenantId } });
});
```

**Ver `06-TENANCY-SPEC.md` para la implementación completa con `AsyncLocalStorage`.**

---

## 5. Mixin de auditoría (heredado `AuditMixin`)

El `AuditMixin` de Python (created_at, updated_at, created_by_id, updated_by_id) se emula en Prisma con:

### 5.1. Helper TS para definir el mixin

```ts
// libs/shared/prisma/mixins.ts
import { Prisma } from '@prisma/client';

export function withAuditMixin<T extends typeof Prisma.ModelName>(model: T) {
  return {
    createdAt: DateTime @default(now()),
    updatedAt: DateTime @updatedAt,
    createdBy: String?,
    updatedBy: String?,
  };
}
```

> Prisma **no tiene herencia real de campos**. La alternativa es usar un **codigo-generador**
> (`prisma-generator-extended`) o simplemente **duplicar los 4 campos en cada modelo**.
> Ver ADR-005 para la decisión sobre mixin vs duplicación.
>
> **Recomendación pragmática**: duplicar los 4 campos en cada modelo de dominio.
> Es explicito, no requiere tooling extra y Prisma Migrate lo trata idénticamente.

### 5.2. Setter automático vía Prisma extension

```ts
// apps/api/src/infrastructure/prisma/extensions/audit-fields.extension.ts
import { Prisma } from '@prisma/client';
import { tenantAls } from '../../tenancy/tenant-async-storage';

export const auditFieldsExtension = Prisma.defineExtension({
  query: {
    $allOperations: async ({ operation, model, args, query }) => {
      if (!model) return query(args);
      const ctx = tenantAls.getStore();
      if (!ctx) return query(args);

      // Antes de insert/update, inject campos de auditoría
      if (operation === 'create' && args.data) {
        args.data.createdBy = ctx.userId;
        args.data.updatedBy = ctx.userId;
      }
      if ((operation === 'update' || operation === 'upsert') && args.data) {
        args.data.updatedBy = ctx.userId;
      }
      return query(args);
    },
  },
});
```

---

## 6. Soft-delete (heredado)

El patrón actual usa `is_active=false` (no hard delete por API).

### Implementación Prisma

- Mantener `isActive Boolean @default(true)` en todos los modelos de dominio.
- Repository pattern expone `findActive` (default) y `findWithDeleted` (solo admin/platform).
- Endpoint `DELETE /api/v1/tasks/:id` ejecuta `update({ where: { id }, data: { isActive: false } })`.
- Hard delete reservado a Platform Admin (`isPlatformAdmin`).

### Prisma extension soft-delete

```ts
// apps/api/src/infrastructure/prisma/extensions/soft-delete.extension.ts
export const softDeleteExtension = Prisma.defineExtension({
  query: {
    $allModels: {
      async findMany({ args, query }) {
        if (!args.where) args.where = {};
        if (args.where.isActive === undefined) args.where.isActive = true;
        return query(args);
      },
      async delete({ model, args, query }) {
        return query({
          ...args,
          data: { isActive: false },
        });
      },
    },
  },
});
```

---

## 7. Tabla pivote `tenant_users` — detalle

Ver snippet completo en `06-TENANCY-SPEC.md §4`. Aquí sus invariantes:

1. `@@unique([tenantId, userId])` — un user no puede estar duplicado en el mismo tenant.
2. `isActive=true` — para revocar acceso sin perder historial.
3. `invitedById` — trazabilidad del inviter.
4. `acceptedAt` —.started tracking tras aceptar el link email.

---

## 8. Migraciones — convenios

### Comando de flujo de trabajo

```bash
# Desarrollo (dev DB)
pnpm prisma migrate dev --name <feature_name>

# CI / Producción
pnpm prisma migrate deploy

# Reset (solo dev!)
pnpm prisma migrate reset
```

### Reglas

1. Una migración por feature (no apilar modificaciones en la misma migration file).
2. **Nunca** editar migraciones ya aplicadas (`prisma migrate resolve` para testing).
3. Aplicar `sql/rls.sql` post-migrate (script de CI separado).
4. Seed: `prisma/seed.ts` crea Plan `Free` + Tenant `demo` + User `admin@demo.local`.
5. Backfill de `tenant_id` en migraciones: nullable primero → populate → NOT NULL.

---

## 9. Tipos UUID en Prisma + PostgreSQL

- Prisma type: `String` con `@default(uuid())` → en DB se materializa como `uuid` native de PostgreSQL.
- Parámetros de chequeo `@db.Uuid` es preferible para checkpoints futuros:

```prisma
id String @id @default(uuid()) @db.Uuid
```

- En TypeScript, `uuid` se trabaja como `string` (no `Uuid` type). DTOs validan con `IsUuid()` (`class-validator`).

---

## 10. Referencias

- `06-TENANCY-SPEC.md` — implementación multi-tenant completa.
- `15-ADRs.md` — ADR-002 (multi-tenant RLS), ADR-005 (mixin duplicado).
- Código actual en `app/models/*.py`, `app/modules/**/models.py`.
