# 09 — HTTP API Spec

> **Contrato REST v1, versionado, paginación, errores, OpenAPI y convenciones heredadas del proyecto FastAPI.**

---

## 1. Versionado

- Prefijo global: `/api/v1/*`.
- Cambios breaking → bump `/api/v2/*` (mantener v1 con deprecation header).
- OpenAPI expuesto en `/api/v1/openapi.json` y documentación en `/api/v1/docs`.

**Diferencia con FastAPI actual**: el prefijo actual es `/api` sin versión. La próxima migración añade `/api/v1` desde el día 0.

---

## 2. Convenciones generales

| Convención | Regla |
|---|---|
| Method semantics | `GET` = idempotente lectura; `POST` = create; `PATCH` = partial update; `PUT` = full replace (o update de un sub-recurso); `DELETE` = soft-delete por defecto |
| Status 200 | OK con body |
| Status 201 | Created con body y `Location` header |
| Status 204 | No Content (sin body) en algunos DELETE |
| Status 400 | BadRequest — validación custom |
| Status 401 | Unauthorized — falta/invalido JWT |
| Status 403 | Forbidden — permiso denegado |
| Status 404 | NotFound — recurso no existe (incluido cross-tenant) |
| Status 409 | Conflict — plan quota, unique constraint |
| Status 422 | Unprocessable Entity — DTO validation failed |
| Status 500 | InternalServerError — logueado como error |
| Content-Type | `application/json` siempre |
| Charset | UTF-8 |
| Times | ISO 8601 UTC con `Z` |
| Ids | UUID strings |

---

## 3. Errores tipados

### 3.1. Estructura estándar de error

```json
{
  "code": "PLAN_QUOTA_EXCEEDED",
  "message": "Plan quota exceeded",
  "details": {
    "max_usuarios": 5,
    "current": 5
  },
  "requestId": "550e8400-e29b-41d4-a716-446655440000"
}
```

- `code` (string UPPER_SNAKE) — código interno estable.
- `message` (string) — mensaje humano en español por defecto (i18n-ready).
- `details` (object?) — info contextual.
- `requestId` — generado por interceptor y devuelto en headers.

### 3.2. Códigos internos estables

| Code | HTTP | Origen |
|---|---|---|
| `BAD_REQUEST` | 400 | Excepción custom `BadRequestException` |
| `VALIDATION_FAILED` | 422 | Pipe `ValidationPipe` con `class-validator` |
| `UNAUTHORIZED` | 401 | `JwtAuthGuard` |
| `INVALID_CREDENTIALS` | 401 | Login inválido |
| `TOKEN_REVOKED` | 401 | Refresh revocado |
| `FORBIDDEN` | 403 | `PermissionsGuard` default |
| `ACCOUNT_LOCKED` | 403 | Lockout exceeded |
| `NOT_FOUND` | 404 | Default dominio |
| `PLAN_QUOTA_EXCEEDED` | 409 | Cuota de Plan superada |
| `INTERNAL_SERVER_ERROR` | 500 | Catch-all |

### 3.3. Implementación

```ts
// apps/api/src/common/exceptions/business.exception.ts
export class BusinessException extends HttpException {
  constructor(
    public readonly errorCode: string,
    message: string,
    statusCode: number,
    details?: Record<string, unknown>,
    headers?: Record<string, string>,
  ) {
    super({ code: errorCode, message, details }, statusCode, { cause: undefined, headers });
  }
}

export class NotFoundException extends BusinessException {
  constructor(message = 'Resource not found') {
    super('NOT_FOUND', message, 404);
  }
}
export class ConflictException extends BusinessException {
  constructor(code: string, message: string, details?: object) {
    super(code, message, 409, details);
  }
}
```

### 3.4. `AllExceptionsFilter` global

```ts
@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  constructor(private readonly pinoLogger: NestLogger) {}

  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const res = ctx.getResponse<Response>();
    const req = ctx.getRequest<Request>();
    const requestId = req.headers['x-request-id'] as string;

    if (exception instanceof BusinessException) {
      return res.status(exception.getStatus()).json({
        ...exception.getResponse(),
        requestId,
      });
    }

    if (exception instanceof HttpException) {
      return res.status(exception.getStatus()).json({
        code: 'HTTP_ERROR',
        message: exception.message,
        requestId,
      });
    }

    this.pinoLogger.error({ err: exception, requestId }, 'Unhandled error');
    return res.status(500).json({
      code: 'INTERNAL_SERVER_ERROR',
      message: 'Internal server error',
      requestId,
    });
  }
}
```

---

## 4. Paginación (heredada del proyecto actual)

El proyecto FastAPI usa `offset` + `limit`. Lo preservamos en NestJS.

### 4.1. Query params

```
GET /api/v1/tasks?offset=0&limit=100&sort_by=createdAt&sort_order=desc&search=foo
```

| Param | Default | Validation | Propósito |
|---|---|---|---|
| `offset` | 0 | `@IsInt() @Min(0)` | Skip |
| `limit` | 100 | `@IsInt() @Min(1) @Max(500)` | Take |
| `sort_by` | undefined | string, validated against DTO fields | Sort column |
| `sort_order` | `asc` | `@IsIn(['asc','desc'])` | Direction |
| `search` | undefined | `@IsString()` | Búsqueda global en `searchable_fields` |

### 4.2. Response envolvente (NEW)

```ts
interface Paginated<T> {
  data: T[];
  total: number;
  offset: number;
  limit: number;
}
```

> El proyecto FastAPI actual devuelve directamente el array sin envolvente. NestJS añade el envelope para envolver `total` sin necesidad de un segundo endpoint `GET /count`. Ver ADR-007.

### 4.3. `PaginationDto` compartido

```ts
// libs/shared/dto/pagination.dto.ts
export class PaginationDto {
  @IsOptional() @IsInt() @Min(0) @Type(() => Number)
  offset?: number = 0;

  @IsOptional() @IsInt() @Min(1) @Max(500) @Type(() => Number)
  limit?: number = 100;

  @IsOptional() @IsString()
  sort_by?: string;

  @IsOptional() @IsIn(['asc', 'desc'])
  sort_order?: 'asc' | 'desc' = 'asc';

  @IsOptional() @IsString()
  search?: string;
}
```

> Compartido vía `@saas/shared` para que Angular 21 pueda tipar sus servicios sin derivar tipos.

---

## 5. Búsqueda (heredada)

Cada repositorio declara `searchable_fields: string[]` (igual que `BaseRepository` FastAPI). El `search` query param se traduce a `WHERE column ILIKE '%search%'` en cualquier searchable field (cast de PostgreSQL).

```ts
// AbstractRepository
protected applySearch(where: any, search?: string): any {
  if (!search || !this.SEARCHABLE_FIELDS.length) return where;
  const or = this.SEARCHABLE_FIELDS.map(field => ({
    [field]: { contains: search, mode: 'insensitive' }, // Prisma ILIKE
  }));
  return { AND: [where, { OR: or }] };
}
```

---

## 6. `ValidationPipe` global

```ts
app.useGlobalPipes(
  new ValidationPipe({
    whitelist: true,         // strip unknown props
    forbidNonWhitelisted: true,
    transform: true,        // string→number de query params
    transformOptions: { enableImplicitConversion: true },
    errorHttpStatusCode: 422,
  }),
);
```

Errores de validación → `VALIDATION_FAILED` con `details` array por campo.

### Response 422 ejemplo

```json
{
  "code": "VALIDATION_FAILED",
  "message": "Validation failed",
  "details": [
    { "field": "title", "constraint": "minLength", "message": "title must be at least 3 chars" }
  ],
  "requestId": "..."
}
```

---

## 7. Headers estándar

### Request

| Header | Req/Opc | Propósito |
|---|---|---|
| `Authorization: Bearer <jwt>` | Requerido salvo @Public | Autenticación |
| `X-Tenant-Id: <uuid>` | Requerido en endpoints tenant-scoped | Tenant activo |
| `X-Request-Id: <uuid>` | Opcional (generado si falta) | Tracing |
| `Content-Type: application/json` | Requerido en body | — |

### Response

| Header | Siempre presente |
|---|---|
| `X-Request-Id` | Sí (igual al recibido o generado) |
| `X-Tenant-Id` | Echo del activo (debug) |
| `Location` | En 201 Created |

---

## 8. Endpoints — mapa completo

### Auth

| Method | Path | Guard |
|---|---|---|
| POST | `/api/v1/auth/login` | — |
| POST | `/api/v1/auth/refresh` | — |
| POST | `/api/v1/auth/logout` | JwtAuthGuard |
| GET  | `/api/v1/auth/me` | JwtAuthGuard |
| GET  | `/api/v1/auth/me/tenants` | JwtAuthGuard |
| PUT  | `/api/v1/auth/tenant-context` | JwtAuthGuard |

### Tenancy

| Method | Path | Guard |
|---|---|---|
| POST | `/api/v1/tenants` | Public (signup) |
| GET  | `/api/v1/tenants/:id` | JwtAuthGuard + TenantGuard (Admin) |
| PUT  | `/api/v1/tenants/:id/plan` | PlatformAdmin |
| POST | `/api/v1/tenants/:id/invitations` | Auth + Tenant + Admin |
| GET  | `/api/v1/tenants/:id/users` | Auth + Tenant + Admin |
| DELETE | `/api/v1/tenants/:id/users/:userId` | Auth + Tenant + Admin |
| PUT  | `/api/v1/tenants/:id/users/:userId/role` | Auth + Tenant + Admin |

### RBAC

| Method | Path | Guard |
|---|---|---|
| GET | `/api/v1/roles` | Auth + Tenant + Admin |
| GET | `/api/v1/roles/:slug/modules` | Auth + Tenant + Admin |
| PUT | `/api/v1/roles/:slug/modules/:moduleSlug` | Auth + Tenant + Admin |
| GET | `/api/v1/me/permissions` | Auth + Tenant |

### Domain (cada subdominio es proxy del patrón)

- `GET/POST /api/v1/tasks` — `tasks_general` permisos CRUD.
- `GET/POST /api/v1/org-units` — `core_org_units`.
- `GET/POST /api/v1/positions` — `core_staff_positions`.
- `GET/POST /api/v1/staff` — `core_staff`.
- `GET/POST /api/v1/fixed-assets` — `assets_fixed_assets`.
- `GET/POST /api/v1/areas` — `assets_areas`.
- `GET/POST /api/v1/asset-groups` — `assets_asset_groups`.
- `GET/POST /api/v1/asset-statuses` — `assets_asset_statuses`.
- `GET/POST /api/v1/institutions` — `assets_institutions`.
- `GET/POST /api/v1/acts` — `assets_acts`.

### Catalogs

| Method | Path |
|---|---|
| GET  | `/api/v1/catalogs/:name` |
| POST | `/api/v1/catalogs/bulk` |

### Health (ver `11-OBSERVABILITY-SPEC.md`)

| Method | Path |
|---|---|
| GET | `/health` |
| GET | `/health/live` |
| GET | `/health/ready` |

---

## 9. OpenAPI

- Generado por NestJS (`DocumentBuilder`) con `swaggerOptions.persistAuthorization`.
- Servido en `/api/v1/docs` (Swagger UI), `/api/v1/redoc` (ReDoc alternativo).
- Schemas en `app.main.ts`:

```ts
const config = new DocumentBuilder()
  .setTitle('Uyuni SaaS API')
  .setDescription('B2B Multi-tenant Core-CRM')
  .setVersion('v1')
  .addBearerAuth()
  .addTag('Auth')
  .addTag('Tenancy')
  .addServer('/api/v1')
  .build();
SwaggerModule.setup('api/v1/docs', app, SwaggerModule.createDocument(app, config));
```

---

## 10. CORS

```ts
app.enableCors({
  origin: ['http://localhost:4200', 'https://app.uyuni.local'],
  credentials: true,
  methods: ['GET','POST','PUT','PATCH','DELETE'],
  allowedHeaders: ['Authorization','Content-Type','X-Tenant-Id','X-Request-Id'],
  exposedHeaders: ['X-Request-Id','X-Tenant-Id','Location','Retry-After'],
});
```

---

## 11. Tests requeridos (contratos)

| ID | Nombre | Valida |
|---|---|---|
| HTTP-1 | 400 BadRequest con code + message + requestId | estructura estable |
| HTTP-2 | 422 ValidationFailed con details por campo | details no undefined |
| HTTP-3 | 401 sin Authorization | estructura |
| HTTP-4 | 404 cross-tenant | mismo code `NOT_FOUND` |
| HTTP-5 | 409 PlanQuotaExceeded | details con `max_usuarios` |
| HTTP-6 | header `X-Request-Id` echo | mismo valor en response |
| HTTP-7 | 201 con Location header | URL del nuevo recurso |
| HTTP-8 | Paginated envelope con `data`, `total`, `offset`, `limit` | estructura |
| HTTP-9 | OpenAPI expuesto en `/api/v1/docs` | 200 HTML |
| HTTP-10 | `limit=0` devuelve 422 | min=1 |

---

## 12. Referencias

- `02-ARCHITECTURE-SPEC.md` — layering.
- `15-ADRs.md` — ADR-007 (envelope `Paginated<T>`), ADR-008 (422洗澡 vs 400).
- Código ancestro: `app/core/routers.py`, `app/core/exceptions.py`, `app/core/handlers.py`.
