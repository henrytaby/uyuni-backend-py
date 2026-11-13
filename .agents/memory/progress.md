# Progress - Uyuni Backend

## Current Status: Active Development

### Completed Milestones

#### Phase 1: Core Infrastructure ✅
- [x] FastAPI application setup
- [x] SQLModel database configuration
- [x] Alembic migrations setup
- [x] Environment configuration with Pydantic Settings
- [x] Structured logging with structlog
- [x] Request ID middleware for traceability

#### Phase 2: Authentication & Authorization ✅
- [x] JWT-based authentication
- [x] Access/refresh token rotation
- [x] Token revocation on logout (blacklist)
- [x] Account lockout mechanism (5 failed attempts)
- [x] RBAC system with granular permissions
- [x] Permission checking middleware
- [x] Implicit read access for assigned modules
- [x] Superuser bypass for RBAC checks

#### Phase 3: Domain Modules ✅
- [x] Commerce module (products, product_masters, batches, sales, live_baskets, investment_rounds, categories, channels)
- [x] Core module (user accounts, roles, permissions, manifests)
- [x] Tasks module (basic CRUD)
- [x] Nested routing architecture
- [x] Dynamic Modular Catalogs with bulk loader (`/api/catalogs/bulk`)
- [x] Depuration of legacy public sector modules (`assets`, `core_staff`, `core_org_unit`, `core_staff_position`)
- [x] Mandatory Singular Table Naming Convention across all 19 database tables

#### Phase 4: Audit System ✅
- [x] Audit middleware for request capture (Access logging)
- [x] SQLAlchemy hooks for entity changes (CDC - Change Data Capture)
- [x] Context variables for request tracing
- [x] Audit entry storage
- [x] Cold storage script for archiving old logs

#### Phase 5: Code Quality ✅
- [x] Ruff linting configuration
- [x] Mypy type checking
- [x] Custom exception handling
- [x] Repository pattern implementation
- [x] Clean Code principles (SOLID, DRY, KISS)

### Recent Improvements (March 2026)
- [x] Fixed typos in model comments ("Relatoinship" → "Relationship")
- [x] Added complete type hints to auth/utils.py
- [x] Replaced print() with proper structlog logging in audit middleware
- [x] Standardized exception handling (NotFoundException across all routers)
- [x] Added warning comment about create_all() vs Alembic in db.py
- [x] Fixed mypy type errors in repository.py and service.py
- [x] Created Memory Bank documentation

### Recent Improvements (November 2026)
- [x] Saneamiento y optimización del sistema de auditoría (`audit_log`):
  - Implementación del filtro **Zero-Noise**: se descartan automáticamente updates sin cambios reales (`changes: null`).
  - Exclusión de entidades internas de sistema (`Module`, `ModuleGroup`, `RoleModule`, `UserLogLogin`, `UserRevokedToken`) en hooks CDC.
  - Configuración de `ENABLE_ACCESS_AUDIT=False` por defecto y en `.env` para prevenir inflación masiva de backups con peticiones HTTP (`/api/catalogs/bulk`, etc.), delegando tráfico a stdout estructurado.
  - Preservación íntegra de `ContextVars` (usuario, IP, User-Agent) para que todas las mutaciones transaccionales de negocio (ventas, stock, usuarios) conserven atribución total.
  - Purga controlada de 1,836 registros basura en Local y 322 en VPS PostgreSQL (`172.23.51.247/uyuni_prod`).
- [x] Sincronización y migración completa del catálogo desde Google Sheets (240 fichas maestras, 242 productos, 127 ventas, lotes, canales y categorías) tanto en base de datos Local como en VPS.
- [x] Actualización de guías de despliegue para Render (SPA rewrites, Brotli, IP extraction) y VPS Ubuntu (Certbot rate limit mitigation, Cloudflare, ZeroSSL).
- [x] Actualización de `docs/AUDIT_GUIDE.md` y Memory Bank con la arquitectura de auditoría optimizada.

### In Progress
- [ ] Rate limiting for authentication endpoints
- [ ] Health check endpoint with database connectivity
- [ ] Connection pooling configuration

### Pending (Enterprise Features)
- [ ] API versioning (/api/v1/)
- [ ] OpenAPI documentation enhancement
- [ ] Performance monitoring integration
- [ ] CI/CD pipeline configuration
- [ ] Docker multi-stage builds
- [ ] Kubernetes deployment manifests

## Known Issues
None currently identified.

## Technical Debt
1. No rate limiting on authentication endpoints
2. Health check endpoint not implemented
3. Connection pooling not explicitly configured

## Next Steps
1. Implement rate limiting for login endpoint
2. Add health check endpoint
3. Configure connection pooling for production

## Architecture Decisions (ADRs)
- **Nested Routing**: Modules use aggregated routers for clean global routing
- **Flat Hierarchy**: Submodules are siblings to avoid excessive depth
- **In-Memory SQLite**: Used for tests to ensure speed and isolation
- **Token Rotation**: Refresh tokens invalidated on every use for security
