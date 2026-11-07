# 11 — Observability Spec

> **Structured logging (pino), tracing (OpenTelemetry), métricas (Prometheus), health checks y el `requestId` heredado del proyecto FastAPI.**

---

## 1. Filosofía (heredada)

El proyecto FastAPI actual implementa:
- `structlog` para logs estructurados (JSON key-value).
- `request_id` ContextVar para tracing por petición.
- Middleware de logging con duración.
- Path exclusions y `ACCESS_LOGS_ONLY_ERRORS`.

NestJS replica el patrón con stack TS moderno.

---

## 2. Stack de observabilidad

| Capa | Tecnología | Razón |
|---|---|---|
| Logs | **pino** + `nestjs-pino` | JSON structured, async, low overhead; bake-in context |
| Tracing | OpenTelemetry SDK + `@opentelemetry/sdk-node` | Vendor-neutral |
| Métricas | `@willsoto/nestjs-prometheus` | Exponen `/metrics` para Prometheus |
| Health | `@nestjs/terminus` | Liveness + Readiness probes |
| APM (opcional) | Sentry / Datadog | Error tracking |

---

## 3. Structured Logging con pino

### 3.1. Configuración

```ts
// apps/api/src/observability/logger.module.ts
import { LoggerModule } from 'nestjs-pino';

@Module({
  imports: [
    LoggerModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => ({
        pinoHttp: {
          transport: cfg.get('ENVIRONMENT') === 'local'
            ? { target: 'pino-pretty' }
            : undefined, // JSON en producción
          level: cfg.get('LOG_LEVEL', 'info'),
          serializers: {
            req: (req) => ({
              method: req.method,
              url: req.url,
              headers: { 'x-request-id': req.headers['x-request-id'] },
            }),
            res: (res) => ({ statusCode: res.statusCode }),
          },
          autoLogging: {
            ignore: (req) => EXCLUDED_PATHS.some(p => req.url.startsWith(p)),
          },
          customPropsMessage: (req) => ({
            requestId: req.headers['x-request-id'],
            tenantId: req.tenantContext?.tenantId,
            userId: req.user?.sub,
          }),
        },
      }),
    }),
  ],
})
export class AppLoggerModule {}
```

### 3.2. Uso en services

```ts
@Injectable()
export class TasksService {
  constructor(@InjectPinoLogger(TasksService.name) private logger: PinoLogger) {}

  async create(dto: CreateTaskDto, tenantId: string, userId: string) {
    this.logger.info({ tenantId, userId, dto }, 'Task created');
    // ...
  }
}
```

### 3.3. Output JSON ejemplo

```json
{
  "level": "info",
  "time": 1720000000000,
  "requestId": "550e8400-...",
  "tenantId": "abc-uuid",
  "userId": "u-uuid",
  "msg": "Task created",
  "dto": { "title": "..." }
}
```

### 3.4. Log levels

| Nivel | Uso |
|---|---|
| `trace` | Debug detallado; deshabilitado en prod |
| `debug` | Diagnóstico de desarrollo |
| `info` | Eventos de negocio (`task.created`, `tenant.invitation.sent`) |
| `warn` | Errores esperados (401, lockout) |
| `error` | Errores operacionales |
| `fatal` | Crashes inmediatos |

> Logs `warn`/`error` siempre con `requestId` y `tenantId` para triage.

---

## 4. Request ID

### 4.1. Middleware de generación

```ts
// apps/api/src/observability/request-id.middleware.ts
@Injectable()
export class RequestIdMiddleware implements NestMiddleware {
  use(req: Request, res: Response, next: NextFunction) {
    const requestId = req.headers['x-request-id'] as string || randomUUID();
    req.headers['x-request-id'] = requestId;
    res.setHeader('X-Request-Id', requestId);
    next();
  }
}

// app.module.ts
export class AppModule implements NestModule {
  configure(consumer: MiddlewareConsumer) {
    consumer.apply(RequestIdMiddleware).forRoutes('*');
  }
}
```

Reemplaza el bloque en `app/main.py:logging_middleware` del proyecto FastAPI.

---

## 5. Health Checks (NEW vs FastAPI actual)

El proyecto FastAPI **no tiene** health checks (`progress.md` lo marca como pending). NestJS los incluye desde día 1.

### 5.1. `HealthModule` con `@nestjs/terminus`

```ts
// apps/api/src/observability/health.module.ts
@Module({
  imports: [TerminusModule, PrismaModule],
  controllers: [HealthController],
})
export class HealthModule {}

// health.controller.ts
@Controller('health')
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private prisma: PrismaHealthIndicator,
  ) {}

  @Get('live')
  @Public()
  liveness() {
    return this.health.check([
      async () => ({ api: { status: 'up' } }),
    ]);
  }

  @Get('ready')
  @Public()
  readiness() {
    return this.health.check([
      async () => this.prisma.pingCheck('database', { timeout: 300 }),
    ]);
  }
}
```

### 5.2. Respuestas

`200 { status: 'ok', info: { database: { status: 'up' } } }`
`503 { status: 'error', error: { database: { status: 'down' } } }`

### 5.3. K8s probes (cuando se despliegue con k8s)

```yaml
livenessProbe:
  httpGet: { path: /health/live, port: 3000 }
readinessProbe:
  httpGet: { path: /health/ready, port: 3000 }
```

---

## 6. Métricas Prometheus

```ts
// apps/api/src/observability/metrics.module.ts
@Module({
  imports: [
    PrometheusModule.register({
      path: '/metrics',
      defaultMetrics: { enabled: true },
    }),
  ],
})
export class AppMetricsModule {}
```

Métricas expuestas:

- `http_requests_total{method,route,status}`
- `http_request_duration_seconds{method,route}` (histogram)
- `tenant_active_total` (gauge)
- `audit_logs_total{action,entity_type,tenant_id}` (counter)

### Custom metrics provider

```ts
@Injectable()
export class TenancyMetricsService {
  constructor(@InjectPinoMetric() private metrics: PrometheusService) {}

  incTenantActive() {
    this.metrics.registerCounter({
      name: 'tenant_active_total',
      help: 'Active tenants count',
    }).inc();
  }
}
```

---

## 7. Tracing con OpenTelemetry

```ts
// apps/api/src/observability/tracing.ts
import { NodeSDK } from '@opentelemetry/sdk-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';
import { HttpInstrumentation } from '@opentelemetry/instrumentation-http';
import { ExpressInstrumentation } from '@opentelemetry/instrumentation-express';
import { PgInstrumentation } from '@opentelemetry/instrumentation-pg';

export function startTracing() {
  const sdk = new NodeSDK({
    traceExporter: new OTLPTraceExporter({ url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT }),
    instrumentations: [new HttpInstrumentation(), new ExpressInstrumentation(), new PgInstrumentation()],
  });
  sdk.start();
}
```

Inicializar en `main.ts` **antes** de crear la app NestJS:

```ts
// main.ts
import { startTracing } from './observability/tracing';
startTracing();
const app = await NestFactory.create(AppModule, {缓冲 logger: false });
```

---

## 8. Configuración

```ts
LOG_LEVEL: Joi.string().valid('trace','debug','info','warn','error','fatal').default('info'),
ENVIRONMENT: Joi.string().valid('local','staging','prod').default('local'),
ENABLE_ACCESS_LOGS: Joi.boolean().default(true),
ACCESS_LOGS_ONLY_ERRORS: Joi.boolean().default(false),
OTEL_EXPORTER_OTLP_ENDPOINT: Joi.string().uri().optional(),
SENTRY_DSN: Joi.string().uri().optional(),
```

---

## 9. Anti-patrones prohibidos

1. `console.log` en código de producción — usar `PinoLogger`.
2. Logs con datos sensibles (`password`, `token`, PII sin redacción).
3. Logs sin `requestId` — rompe correlación en dashboards.
4. Health checks que dependen de servicios externos (no endpoints públicos).
5. Métricas con cardinalidad alta (`tenant_id` como label es OK; `user_id` no).
6. Logs asíncronos que pierden `AsyncLocalStorage` context.

---

## 10. Mapeo con el proyecto FastAPI actual

| FastAPI (ancestro) | NestJS |
|---|---|
| `app/core/logging.py:configure_logging` | `AppLoggerModule.forRootAsync` |
| `app/main.py:logging_middleware` con `structlog.contextvars` | `RequestIdMiddleware` + pino customProps |
| `structlog.get_logger().info(...)` | `PinoLogger.info(...)` |
| `request_id` ContextVar | `x-request-id` header + pino context |
| Sin health checks | `@nestjs/terminus` |
| Sin métricas | `@willsoto/nestjs-prometheus` |
| Sin tracing | OpenTelemetry SDK |

---

## 11. Referencias

- `12-SECURITY-SPEC.md` — Sentry y manejo de secrets.
- `15-ADRs.md` — ADR-014 (pino vs winston).
- `07-AUDIT-SPEC.md` — auditoría de dominio (distinta de logs).
- Código ancestro: `app/core/logging.py`, `app/main.py` middleware block.
