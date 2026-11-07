# 12 — Security Spec

> **Rate limiting, CORS, helmet, secrets management, OWASP Top-10, headers, mitigaciones heredadas (lockout, blacklist) y nuevas (rate limit, helmet).**

---

## 1. Postura de seguridad

El proyecto FastAPI ya implementa:
- bcrypt (cost factor 12) para password hashing.
- JWT con blacklist en logout.
- Lockout de 5 intentos fallidos.
- Timing attack mitigation en login.
- Refresh token rotation.
- Audit logging.

NestJS **hereda todo** + añade lo que falta (marcado como pending en `progress.md`):
- **Rate limiting** en endpoints sensibles.
- **Helmet** para headers HTTP.
- **CORS** explícito (no `*`).
- **Secrets** fuera del código (env / Vault).
- **OWASP Top-10** checklist active.

---

## 2. OWASP Top-10 — controles activos

| # | Riesgo | Mitigación en NestJS |
|---|---|---|
| A01 | Broken Access Control | `JwtAuthGuard` + `TenantGuard` + `PermissionsGuard` + **RLS Postgres** defense-in-depth |
| A02 | Cryptographic Failures | bcrypt cost 12, TLS 1.3, no secrets en code, `JWT_SECRET` ≥ 256 bits |
| A03 | Injection | Prisma parameterized queries; `class-validator` whitelist; **no raw SQL** salvo archivo RLS con `?placeholder` |
| A04 | Insecure Design | Threat modeling por bounded context; spec review (este SDD) antes de implementar |
| A05 | Security Misconfiguration | `helmet`, `cors` whitelist, `dotenv` validado con Joi, sin `app.run(debug=true)` en prod |
| A06 | Vulnerable Components | `pnpm audit --prod` en CI; Dependabot; locks `pnpm-lock.yaml` |
| A07 | Identification & Auth Failures | Lockout 5 intentos, refresh rotation, blacklist, verificación email pendiente |
| A08 | Software/Data Integrity Failures | `pv` (package verification); subresource integrity in CDN |
| A09 | Logging & Monitoring Failures | Pino structured + OpenTelemetry + Sentry (ver `11-OBSERVABILITY-SPEC.md`) |
| A10 | SSRF | Whitelist de URLs outbound (mailer, webhooks); validación con `URL` parser |
| A07+ | Brute force | `@nestjs/throttler` global + override por endpoint |

---

## 3. Rate Limiting (NEW)

```ts
// apps/api/src/security/throttler.module.ts
@Module({
  imports: [
    ThrottlerModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (cfg: ConfigService) => [
        {
          ttl: cfg.get('THROTTLE_TTL_MS', 60000),
          limit: cfg.get('THROTTLE_LIMIT', 60),
        },
      ],
    }),
  ],
  providers: [{ provide: APP_GUARD, useClass: ThrottlerGuard }],
})
export class AppThrottlerModule {}
```

### Overrides por endpoint

```ts
// Auth: 5 attempts / minute per IP
@Throttle({ default: { limit: 5, ttl: 60000 } })
@Post('login')
async login(...) { ... }

// Tenancy invitations: 10 / hour per user/tenant
@Throttle({ default: { limit: 10, ttl: 3_600_000 } })
@Post('tenants/:id/invitations')
async invite(...) { ... }

// Bulk catalogs: alta cardinalidad → no rate limit específico pero sí default
@SkipThrottle()
@Post('catalogs/bulk')
async bulk(...) { ... }
```

### Storage adapter

En prod: `@nestjs/throttler-storage-redis` (compartir contadores entre pods). En local/test: in-memory.

---

## 4. Helmet — headers HTTP

```ts
// main.ts
import helmet from 'helmet';
app.use(helmet());
```

Headers activados:
- `Content-Security-Policy: default-src 'self'`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`

> CSP tuning cuidado si Swagger UI se sirve desde `/api/v1/docs` — permite scripts self.

---

## 5. CORS (whitelist)

Ver `09-HTTP-API-SPEC.md §10`. Nunca `*` en prod.

---

## 6. Secrets management

### 6.1. `.env.example` (al repo, sin valores)

```bash
# Auth
JWT_SECRET=change_me_min_32_chars
JWT_ACCESS_EXPIRES_MINUTES=15
JWT_REFRESH_EXPIRES_DAYS=7

# Security
SECURITY_LOGIN_MAX_ATTEMPTS=5
SECURITY_LOGIN_LOCKOUT_MINUTES=15
THROTTLE_TTL_MS=60000
THROTTLE_LIMIT=60

# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/uyuni

# Observability
LOG_LEVEL=info
SENTRY_DSN=
OTEL_EXPORTER_OTLP_ENDPOINT=

# Mailer
MAILER_FROM=no-reply@uyuni.local
SMTP_URL=smtp://localhost:1025

# CORS
CORS_ORIGINS=http://localhost:4200
```

### 6.2. `ConfigService` con validación Joi

```ts
// apps/api/src/config/config.module.ts
@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      validationSchema: envValidationSchema,
      validationOptions: { abortEarly: true },
    }),
  ],
})
export class AppConfigModule {}
```

`validate(config)` lanza `FATAL` en boot si falta cualquier required.

### 6.3. Production secrets

- **Vault / Doppler** / AWS Secrets Manager / GCP Secret Manager.
- En CI: inyecta env vars en runtime; nunca en Docker image.
- Ratotation policy: `JWT_SECRET` cada 90 días con doble clave (new+old active).

---

## 7. Passwords

- Hashing: bcrypt cost 12 (`bcrypt.hashSync(plain, 12)`).
- Mínimo 8 chars, máx 128 (prevenir DoS bcrypt).
- No exposición de hash en responses (`excludePasswordHash` interceptor o DTO sin campo).
- ResetPassword flow (postergado en MVP pero endpoint reservado).

---

## 8. JWT Hardening

- Algoritmo: `HS256` (default) — suficiente para monolito. Si se split en microservices migrar a `RS256`.
- `JWT_SECRET` ≥ 32 chars.
- `jti` (JWT id) único por token para soportar blacklist granular.
- Verification estricta: `verifyAsync(token, { algorithms: ['HS256'] })` — éviter `alg=none`.
- No compartir `JWT_SECRET` entre access y refresh (recommendeded): define `JWT_REFRESH_SECRET`.

---

## 9. Audit de seguridad (diferente a audit de dominio)

`07-AUDIT-SPEC.md` cubre auditoría de datos. Esta sección define **eventos de seguridad** específicos:

| Evento | Origen | Log |
|---|---|---|
| LOGIN_SUCCESS | AuthController | info con `userId`, `ip` |
| LOGIN_FAILED | AuthController | warn |
| ACCOUNT_LOCKED | AuthController | warn con `unlock_at` |
| LOGOUT | AuthController | info |
| TOKEN_REFRESH | AuthController | info |
| PERMISSION_DENIED | PermissionsGuard | warn con `module`, `action` |
| QUOTA_EXCEEDED | TenantsController | warn con `plan.max_usuarios` |
| TENANT_INVITATION_SENT | TenantsController | info |
| TENANT_SUSPENDED | PlatformAdminController | warn |
| RL S_DENIED | Postgres (log) | error con `tenant_id`, `user_id` |

---

## 10. Desarrollo seguro — checklist CI

```yaml
# .github/workflows/security.yml
- pnpm audit --audit-level=moderate
- pnpm run lint:security      # custom de eslint-plugin-security
- pnpm run test:e2e:security  # tests deRBAC + tenant isolation gate
- SonarCloud scan             # SAST
- Trivy filesystem scan       # Container/image secrets
```

---

## 11. Threat model (alto nivel)

| Assets | Adversario | Vector | Mitigación |
|---|---|---|---|
| Datos de TenantA | Usuario malicious en TenantB | `GET /api/v1/tasks/{A_id}` cross-tenant | `TenantScopedRepository` + RLS Postgres + CI gate |
| JWT secret | DevOps con repo access | `git log -p` | Git secrets pre-commit; `JWT_SECRET` solo en Vault |
| Refresh tokens | Atacante MITM | Roba refresh | HTTPS-only, rotation invalida el anterior |
| Login brute-force | Hacker botnet | 1000 logins/min | Throttler IP + Lockout 5 + dummy-hash timing |
| Quota bypass | Admin TenantA con múltiples tabs | 2 invitaciones concurrentes | `SELECT … FOR UPDATE` lock pesimista |
| Audit log tampering | Empleado con acceso DB | `UPDATE audit_logs` | `audit_logs` write-only en app + RLS aun al audited role + audit de writes SQL |

---

## 12. Anti-patrones prohibidos

1. `JWT_SECRET` harcodeado en `config.ts`.
2. Swagger UI público en producción sin auth.
3..rate-limit deshabilitado en `@Public()` (health es OK).
4. Permitir `*` CORS en prod.
5. Logs con `password` o `token` sin redactar.
6. Raw SQL sin `?placeholder` o prisma `$queryRaw`/`$executeRaw`.
7. `helmet()` deshabilitado "para debugging" en prod.

---

## 13. Referencias

- `04-AUTH-SPEC.md` — lockout y blacklist.
- `06-TENANCY-SPEC.md` — RLS y cuota.
- `07-AUDIT-SPEC.md` — logs immutables.
- `15-ADRs.md` — ADR-015 (throttler-storage-redis), ADR-016 (RS256 vs HS256 futuro).
