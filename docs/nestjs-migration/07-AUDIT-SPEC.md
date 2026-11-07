# 07 — Audit Spec

> **Access Logging + Change Data Capture (CDC) + Structured Logging en NestJS. Migración del sistema heredado del proyecto FastAPI.**

---

## 1. Visión general (heredada + extendida con `tenantId`)

El proyecto FastAPI actual implementa dos capas de auditoría:

1. **Access Logging** — registra cada petición HTTP (`user`, `ip`, `path`, `method`, `status_code`).
2. **CDC (Change Data Capture)** — registra cambios `old/new` en `INSERT/UPDATE/DELETE` de entidades de dominio.

En NestJS se preservan ambas, **migrando los mecanismos**:

| FastAPI actual | NestJS target |
|---|---|
| `AuditMiddleware` (BaseHTTPMiddleware) | `AccessAuditInterceptor` (NestJS Interceptor) |
| SQLAlchemy `event.listen(Session, 'after_flush')` | Prisma `$extends({ query })` hooks |
| `ContextVar` de `contextvars` | `AsyncLocalStorage` de Node |
| `audit_logs` tabla con `user_id` | `audit_logs` tabla + `tenant_id` (new) |

---

## 2. Modelo de datos `AuditLog`

```prisma
model AuditLog {
  id          String   @id @default(uuid())
  tenantId    String?  @map("tenant_id")  // NUEVO vs FastAPI
  userId      String?  @map("user_id")
  username    String?
  action      String                      // 'CREATE' | 'UPDATE' | 'DELETE' | 'ACCESS'
  entityType  String   @map("entity_type")
  entityId    String?  @map("entity_id")
  changes     Json?
  ipAddress   String?  @map("ip_address")
  userAgent   String?  @map("user_agent")
  timestamp   DateTime @default(now())
  @@index([tenantId, timestamp])
  @@index([userId])
  @@map("audit_logs")
}
```

Invariante: NUNCA se hace `DELETE` ni `UPDATE` sobre `audit_logs` desde la API. Solo `INSERT`. Excepción: admin script de archivo.

---

## 3. Access Logging — `AccessAuditInterceptor`

Reemplaza `app/core/audit/middleware.py`:

```ts
// apps/api/src/audit/access-audit.interceptor.ts
@Injectable()
export class AccessAuditInterceptor implements NestInterceptor {
  constructor(
    @Inject('AuditRepositoryPort') private auditRepo: AuditRepositoryPort,
    private reflector: Reflector,
  ) {}

  async intercept(ctx: ExecutionContext, next: CallHandler) {
    const req = ctx.switchToHttp().getRequest();
    if (this.shouldSkip(req)) return next.handle();

    const start = Date.now();
    let resp: any;
    try {
      resp = await lastValueFrom(next.handle());
    } finally {
      const res = ctx.switchToHttp().getResponse();
      const userAls = accessAls.getStore();
      await this.auditRepo.insert({
        tenantId: userAls?.tenantId,
        userId: userAls?.userId,
        username: userAls?.username,
        action: 'ACCESS',
        entityType: 'Endpoint',
        entityId: req.url,
        changes: { method: req.method, statusCode: res.statusCode, durationMs: Date.now() - start },
        ipAddress: req.ip,
        userAgent: req.headers['user-agent'],
      });
    }
    return resp;
  }

  private shouldSkip(req: Request): boolean {
    // Rutas excluidas: /docs, /health, /openapi.json ...
    return EXCLUDED_PATHS.some(p => req.url.startsWith(p));
  }
}
```

### 3.1. `AuditModule` y registro global

```ts
@Module({
  providers: [
    { provide: 'AuditRepositoryPort', useClass: PrismaAuditRepository },
  ],
  exports: ['AuditRepositoryPort'],
})
export class AuditModule {}

// app.module.ts
@Module({
  imports: [AuditModule],
  providers: [{ provide: APP_INTERCEPTOR, useClass: AccessAuditInterceptor }],
})
export class AppModule {}
```

---

## 4. CDC con Prisma extensions

Reemplaza `app/core/audit/hooks.py` (SQLAlchemy `after_flush`):

```ts
// apps/api/src/audit/cdc.extension.ts
import { Prisma } from '@prisma/client';
import { cdcAls } from './cdc-context';

const TRACKED_MODELS = new Set([
  'task', 'fixedAsset', 'area', 'assetGroup', 'assetStatus',
  'institution', 'act', 'orgUnit', 'staffPosition', 'staff',
]);

export const cdcExtension = Prisma.defineExtension({
  query: {
    $allModels: {
      async create({ args, model, query }) {
        if (!TRACKED_MODELS.has(model)) return query(args);
        const result = await query(args);
        await this.logChange('CREATE', model, result, null, result);
        return result;
      },
      async update({ args, model, query }) {
        if (!TRACKED_MODELS.has(model)) return query(args);
        const old = await this.findOld(model, args.where);
        const result = await query(args);
        await this.logChange('UPDATE', model, result, old, result);
        return result;
      },
      async delete({ args, model, query }) {
        if (!TRACKED_MODELS.has(model)) return query(args);
        const old = await this.findOld(model, args.where);
        const result = await query(args);
        await this.logChange('DELETE', model, result, old, null);
        return result;
      },
    },
  },
});
```

> Prisma extension `query` hooks se ejecutan dentro del mismo `prisma.$transaction`, garantizando atomicidad con la mutación (igual que SQLAlchemy hooks).

---

## 5. Contexto de auditoría (AsyncLocalStorage)

```ts
// apps/api/src/audit/audit-context.ts
import { AsyncLocalStorage } from 'node:async_hooks';

export interface AuditContext {
  tenantId: string | null;
  userId: string | null;
  username: string | null;
  ipAddress: string | null;
  userAgent: string | null;
}

export const accessAls = new AsyncLocalStorage<AuditContext>();
export const cdcAls = new AsyncLocalStorage<AuditContext>();

export function setAuditContext(ctx: AuditContext) { /* init */ }
```

`AccessAuditInterceptor` invoca `accessAls.run({...}, () => next.handle())` y todo el
árbol async (incluida la llamada a `this.logChange()`) lo lee.

---

## 6. Setteo automático de `created_by_id`, `updated_by_id` (heredado)

Reemplaza `app/core/audit/hooks.py:set_audit_user_fields`:

```ts
// apps/api/src/infrastructure/prisma/extensions/audit-fields.extension.ts
export const auditFieldsExtension = Prisma.defineExtension({
  query: {
    $allModels: {
      async create({ args, query }) {
        const ctx = cdcAls.getStore();
        if (ctx) args.data = { ...args.data, createdBy: ctx.userId, updatedBy: ctx.userId };
        return query(args);
      },
      async update({ args, query }) {
        const ctx = cdcAls.getStore();
        if (ctx) args.data = { ...args.data, updatedBy: ctx.userId };
        return query(args);
      },
    },
  },
});
```

---

## 7. Estructura de `changes` (heredado)

```ts
interface AuditChanges {
  // UPDATE
  [field: string]: { old: unknown; new: unknown };
  // CREATE: snapshot completo del objeto creado
  // DELETE: snapshot del objeto eliminado
}
```

> **Convención**: serializar siempre valores como string para evitar drift de fechas (mismo patrón que el `audit_changes` de Python).

---

## 8. Mudanzas a cold storage (heredado `scripts/archive_audit.py`)

El proyecto FastAPI actual tiene un script de archivo para logs antiguos. En NestJS:

- Job BullMQ `archive-audit-logs` que ejecuta diariamente:
  ```ts
  await prisma.$executeRaw`
    INSERT INTO audit_logs_archive
    SELECT * FROM audit_logs
    WHERE timestamp < ${cutoffDate}
  `;
  await prisma.auditLog.deleteMany({ where: { timestamp: { lt: cutoffDate } } });
  ```
- O vía Prisma raw SQL particionado por mes (`PARTITION BY RANGE (timestamp)`).

> Ver `15-ADRs.md` ADR-009 para justificación de partición por mes.

---

## 9. Variables de entorno (heredadas del proyecto actual)

```ts
ENABLE_ACCESS_AUDIT: Joi.boolean().default(true),
ENABLE_DATA_AUDIT: Joi.boolean().default(true),
ACCESS_LOGS_ONLY_ERRORS: Joi.boolean().default(false),
AUDIT_EXCLUDED_PATHS: Joi.array().items(Joi.string()).default([
  '/docs', '/redoc', '/openapi.json', 'GET:/health', '/',
]),
AUDIT_LOG_EXCLUDE_STATUS_CODES: Joi.array().items(Joi.number()).default([404]),
AUDIT_LOG_INCLUDED_METHODS: Joi.array().items(Joi.string()).default([
  'GET', 'POST', 'PUT', 'PATCH', 'DELETE',
]),
```

---

## 10. Tests requeridos

| ID | Nombre | Valida |
|---|---|---|
| AUD-1 | POST crea audit log CREATE | log con `changes` = snapshot del objeto |
| AUD-2 | PATCH crea log UPDATE con old/new | diff por campo |
| AUD-3 | DELETE crea log DELETE con snapshot | objeto borrado registrado |
| AUD-4 | `audit_logs` no actualizable | 405/403 si se intenta |
| AUD-5 | `tenant_id` siempre presente en logs de dominio | log con `tenant_id NOT NULL` |
| AUD-6 | Access log registra cada HTTP | 1 log por request |
| AUD-7 | Excluded paths no generan log | sin registro para `/health`, `/docs` |
| AUD-8 | Excluded status codes (404) | no loguea |

---

## 11. Anti-patrones

1. Endpoint que muta entidad dominio pero no genera audit log (modelo no tracked).
2. Hook CDC que lanza error → aborta la transacción mutante (NO debe, debe loguear y continuar).
3. Storage de `password_hash` en audit `changes` → campos sensibles prohibidos en log.
4. Update de `audit_logs` (violación append-only).
5. Faltan `tenantId` en logs → errores de aislamiento.

> Para campos sensibles: agregar un `SENSITIVE_FIELDS` set en `cdc.extension.ts` que los enmascare antes de serializar:
> ```ts
> const SENSITIVE = new Set(['passwordHash', 'token']);
> if (SENSITIVE.has(field)) value = '***REDACTED***';
> ```

---

## 12. Archivo de mapeo con ancestro FastAPI

| Ancestra en FastAPI | Nueva en NestJS |
|---|---|
| `app/core/audit/middleware.py:AuditMiddleware` | `AccessAuditInterceptor` |
| `app/core/audit/hooks.py:audit_changes` (SQLAlchemy after_flush) | `cdcExtension` Prisma |
| `app/core/audit/hooks.py:set_audit_user_fields` | `auditFieldsExtension` Prisma |
| `app/core/audit/context.py` (ContextVars) | `audit-context.ts` (AsyncLocalStorage) |
| `app/models/audit.py:AuditLog` | `AuditLog` model en `schema.prisma` |
| `scripts/archive_audit.py` | BullMQ job `archive-audit-logs` |

---

## 13. Referencias

- `11-OBSERVABILITY-SPEC.md` — logs estructurados (pino), que es distinto de auditoría de dominio.
- `15-ADRs.md` — ADR-009 (partición por mes), ADR-010 (AsyncLocalStorage vs request-scoped providers).
- Código ancestro: `app/core/audit/*.py`, `scripts/archive_audit.py`.
