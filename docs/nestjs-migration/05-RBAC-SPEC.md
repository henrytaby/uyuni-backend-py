# 05 — RBAC Spec

> **Role-Based Access Control multi-tenant: módulos, permisos CRUD, scope, decoradores y guards idiomatics de NestJS.**

---

## 1. Modelo RBAC (heredado + multi-tenant)

```mermaid
erDiagram
    User ||--o{ TenantUser : "membership"
    Tenant ||--o{ TenantUser : "member"
    TenantUser }o--|| Tenant : ""
    TenantUser {
        string rol  # 'Admin' | 'Empleado' | 'Auditor'
    }

    Role ||--o{ RoleModule : "permissions"
    Module ||--o{ RoleModule : "permissions"
    Role {
        string slug
        bool isActive
    }
    Module {
        string slug
        bool isActive
    }
    RoleModule {
        bool canCreate
        bool canUpdate
        bool canDelete
        bool scopeAll
    }
```

### Diferencia crítica vs FastAPI actual

| Aspecto | FastAPI actual | NestJS multi-tenant |
|---|---|---|
| Donde viven los roles | Global `user_roles` | Membresía en `tenant_users.rol` (string) |
| ¿Roles son global config o por tenant? | Globales | Globales como `Role` (catálogo), pero su asignación a un User es **por tenant** |
| Verificación de permiso | `PermissionChecker.__call__(user, X-Active-Role)` | `PermissionsGuard` + `@Permissions(slug, action)` |
| Header rol activo | `X-Active-Role` (slug) | `X-Tenant-Id` (resuelve `tenant_users.rol` automáticamente) |
| Superuser bypass | Directo en `PermissionChecker` | Directo en `PermissionsGuard`, igual |

> Los roles `Admin`, `Empleado`, etc. se modelan como strings en `tenant_users.rol` **dentro de un enum admin**. Si se necesita flexibilidad total
> (crear roles custom por tenant), se mantiene la tabla `roles` + `role_modules` como catálogo pero **la asignación user→rol** vive en `tenant_users.rol`.

---

## 2. Módulos del sistema (slug table)

Catálogo global (no por tenant) de módulos disponibles en el SaaS:

| slug | descripción |
|---|---|
| `core_org_units` | Unidades Organizacionales |
| `core_staff` | Personal |
| `core_staff_positions` | Cargos |
| `assets_fixed_assets` | Activos Fijos |
| `assets_areas` | Áreas |
| `assets_asset_groups` | Grupo de Activos |
| `assets_asset_statuses` | Estado de Activos |
| `assets_institutions` | Instituciones |
| `assets_acts` | Actas |
| `tasks_general` | Tareas |
| `audit_logs` | Auditoría (solo lectura excepto platform admin) |
| `tenancy_users` | Gestión de usuarios del tenant (invitar, revoke) |
| `tenancy_billing` | Plan y billing (solo Admin del tenant) |

---

## 3. Permission Actions (enum)

```ts
export enum PermissionAction {
  CREATE = 'create',
  READ = 'read',
  UPDATE = 'update',
  DELETE = 'delete',
}
```

**READ es implícito**: cuando un `RoleModule` está activo para un Rol y un Módulo, leer está garantizado (igual que en el proyecto actual).

---

## 4. `PermissionsGuard` (idiomatic NestJS)

```ts
// apps/api/src/rbac/permissions.guard.ts
@Injectable()
export class PermissionsGuard implements CanActivate {
  constructor(
    private readonly reflector: Reflector,
    private readonly permissionsService: PermissionsService,
  ) {}

  async canActivate(ctx: ExecutionContext): Promise<boolean> {
    const required = this.reflector.get<PermissionMeta>(
      'permissions',
      ctx.getHandler(),
    );
    if (!required) return true;

    const req = ctx.switchToHttp().getRequest();
    const user = req.user as JwtPayload;
    if (user.isSuperuser) return true; // bypass platform admin

    const tenantId = user.tenantId;
    if (!tenantId) {
      throw new ForbiddenException('No tenant context active');
    }

    const role = user.role; // inyectado por TenantGuard
    const allowed = await this.permissionsService.check({
      roleSlug: role,
      moduleSlug: required.module,
      action: required.action,
      tenantId,
    });

    if (!allowed) {
      throw new ForbiddenException(
        `No '${required.action}' permission for module '${required.module}'`,
      );
    }
    return true;
  }
}
```

### `@Permissions()` decorator

```ts
// apps/api/src/rbac/permissions.decorator.ts
export type PermissionMeta = { module: string; action: PermissionAction };
export const Permissions = (module: string, action: PermissionAction) =>
  SetMetadata('permissions', { module, action });

// Uso en controller:
@Post()
@Permissions('tasks_general', PermissionAction.CREATE)
create(...) { ... }
```

---

## 5. `PermissionsService` (Application layer)

```ts
@Injectable()
export class PermissionsService {
  constructor(
    @Inject('RoleModuleRepositoryPort')
    private readonly roleModules: RoleModuleRepositoryPort,
  ) {}

  async check(req: {
    roleSlug: string;
    moduleSlug: string;
    action: PermissionAction;
    tenantId: string;
  }): Promise<boolean> {
    const roleModule = await this.roleModules.findByRoleAndModule(
      req.roleSlug,
      req.moduleSlug,
    );
    if (!roleModule || !roleModule.isActive) return false;

    const hasRole = roleModule.role?.isActive ?? false;
    const hasModule = roleModule.module?.isActive ?? false;
    if (!hasRole || !hasModule) return false;

    switch (req.action) {
      case PermissionAction.READ:    return true; // implicit
      case PermissionAction.CREATE:  return roleModule.canCreate;
      case PermissionAction.UPDATE:  return roleModule.canUpdate;
      case PermissionAction.DELETE:  return roleModule.canDelete;
    }
  }
}
```

---

## 6. Scope (`scope_all`) — heredado del proyecto actual

```ts
type PermissionScope = 'all' | 'own';
```

- `scope_all=true`: el usuario ve **todos** los registros de su tenant (ej. Admin).
- `scope_all=false`: el usuario ve solo registros donde `created_by_id = user.id` (ej. Empleado).

### Implementación en el repository

```ts
// tasks.prisma.repository.ts
async list(query: PaginationDto, tenantId: string, scope: PermissionScope, userId: string) {
  const where = {
    tenantId,
    isActive: true,
    ...(scope === 'own' ? { createdBy: userId } : {}),
  };
  return prisma.task.findMany({ where, ...pagination(query) });
}
```

El `scope` se obtiene del `TenantContext` (resuelto por `TenantGuard`, ver `06-TENANCY-SPEC.md`).

---

## 7. Order of Guards (NestJS)

```
JwtAuthGuard        → autentica el JWT y setea req.user
    ↓
TenantGuard         → valida membresía activa, resuelve tenantId + role + scope
    ↓
PermissionsGuard    → valida {module, action} en role_modules
    ↓
ValidationPipe      → valida body DTO (class-validator)
    ↓
Controller method
```

Declaración:

```ts
@UseGuards(JwtAuthGuard, TenantGuard, PermissionsGuard)
@Controller('api/v1/tasks')
export class TasksController { ... }
```

O vía decorador compuesto:

```ts
// apps/api/src/common/decorators/tenant-scoped.decorator.ts
export const TenantScoped = () =>
  applyDecorators(UseGuards(JwtAuthGuard, TenantGuard, PermissionsGuard));

@TenantScoped()
@Controller('api/v1/tasks')
export class TasksController { ... }
```

---

## 8. Módulos con permisos DEFAULT por Rol

Seed inicial del SaaS:

| Rol | Módulos con acceso | canCreate | canUpdate | canDelete | scopeAll |
|---|---|---|---|---|---|
| `Admin` | todos los dominios | ✅ | ✅ | ✅ | all |
| `Empleado` | assets, tasks, core | ✅ | ❌ | ❌ | own |
| `Auditor` | audit_logs | ❌ | ❌ | ❌ | all |

Seed file: `apps/api/prisma/seeds/role-permissions.seed.ts`.

---

## 9. Superuser / Platform Admin bypass

- `User.isSuperuser = true` → bypass RBAC (no validations of role_modules).
- NO bypass `TenantGuard` (un superuser sigue debiendo elegir un tenant para hacer operaciones dentro de él).
- **Pero**: plataforma admin puede ver **todos** los tenants a través de endpoints `/platform/*` que requieren `isSuperuser=true`.

---

## 10. Endpoints de gestión de RBAC (solo Tenant Admin)

- `GET /api/v1/roles` — listar roles disponibles.
- `GET /api/v1/roles/:slug/modules` — permisos CRUD por módulo para un rol.
- `PUT /api/v1/roles/:slug/modules/:moduleSlug` — actualizar `RoleModule` (canCreate, etc.).
- `GET /api/v1/me/permissions` — listar permisos efectivos del user actual en el tenant activo (para que Angular 21 lo use para habilitar/deshabilitar botones).

---

## 11. Tests requeridos (RBAC)

| ID | Nombre | Valida |
|---|---|---|
| RBAC-1 | Admin puede crear task | 201 |
| RBAC-2 | Empleado no puede delete | 403 |
| RBAC-3 | Empleado scope=own solo ve sus tasks | array filtrado |
| RBAC-4 | Auditor no puede crear | 403 |
| RBAC-5 | Permisos desactivados (`isActive=false`) | 403 |
| RBAC-6 | Superuser bypass | 200 sin permiso registrado |
| RBAC-7 | Sin `X-Tenant-Id` | 403 `No tenant context` |
| RBAC-8 | `GET /me/permissions` lista perms efectivos | JSON con módulos y booleans |

---

## 12. Referencias

- Código ancestro: `app/auth/permissions.py` (`PermissionChecker`).
- `06-TENANCY-SPEC.md` para `TenantGuard`.
- `10-TESTING-SPEC.md` — gates CI anti-fuga de tenant.
