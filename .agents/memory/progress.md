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
- [x] Optimización y robustecimiento de Fichas Maestras (`commerce_product_master`):
  - Creación de secuencia atómica en PostgreSQL (`commerce_product_master_item_number_seq`) para `item_number`.
  - Inmutabilidad estricta y autogeneración por el backend de `item_number` (cero intervención manual del cliente).
  - Flexibilización de `code` como campo opcional (`NULL` / código de barras) sin `UNIQUE` global, dejando la arquitectura 100% preparada para Multi-Tenancy.
  - Limpieza de datos en Local y VPS: `code = NULL` y `features` con el detalle extendido en Markdown.
- [x] Copiloto IA de Comercio (`app/modules/commerce/assistant/`):
  - Arquitectura multi-proveedor con fallback inteligente: Groq (`openai/gpt-oss-120b`) → Mistral (`ministral-8b-latest`) → Gemini (`gemini-3.5-flash`).
  - Motor de búsqueda semántica con expansión de sinónimos (`domotica`, `auto`, `celular`, etc.) y filtrado exhaustivo de stop words / verbos de consulta.
  - Pool de candidatos ampliado a 35 ítems para consultas por categoría, permitiendo que la IA evalúe la pertinencia funcional completa del inventario real.
  - Sincronización 1:1 entre citas en Markdown de la IA y tarjetas interactivas del frontend (`matched_products`).
  - Implementación del modelo de Tri-Precio Comercial (`published_price`, `minimum_price`, `official_price`) con cálculo dinámico de margen de regateo y detección de Precio Fijo.
  - Integración completa con el drawer interactivo en Angular 21 + PrimeNG 21 (`commerce-assistant-drawer`).
  - Suite de 16 pruebas unitarias específicas y 109 pruebas globales pasando al 100%.
  - Hook de auto-calibración en el arranque del servidor (`main.py` lifespan) y en scripts ETL para evitar desfasajes tras restauraciones de backups o migraciones con Navicat.
  - Actualización de documentación de integración frontend (`03_FRONTEND_INTEGRATION_GUIDE.md`).
- [x] Motor de Multi-Fotografías y Galería Multimedia para Fichas Maestras (`commerce_product_image`):
  - Entidad SQLModel `ProductImage` y tabla singular `commerce_product_image` con campos: `url`, `public_id`, `image_type` (`CATALOG`, `REAL`, `MARKETING`, `BANNER`), `title`, `original_filename`, `file_size_bytes`, `width`, `height`, `format`, `is_cover`, `sort_order`, `created_at`, `updated_at`.
  - Migración Alembic `6843e3c5c10e_create_commerce_product_image_table.py` aplicada tanto en BD Local (`localhost`) como en BD VPS (`172.23.51.247`).
  - Jerarquía estructurada en Cloudinary: `uyuni/products/{item_number}/{image_type}/` (ej. `uyuni/products/242/catalog/`).
  - Endpoints REST completos:
    - `POST /api/commerce/product-masters/{id}/images` (subida masiva multipart drag & drop de 10+ fotos con validación de tipo y tamaño).
    - `GET /api/commerce/product-masters/{id}/images` (filtrado por `image_type` y `product_id`).
    - `PATCH /api/commerce/product-masters/{id}/images/{image_id}/cover` (definir portada oficial y sincronizar `ProductMaster.cover_image_url`).
    - `PUT /api/commerce/product-masters/{id}/images/reorder` (reordenamiento de galería drag & drop).
    - `PATCH /api/commerce/product-masters/{id}/images/{image_id}` (actualización de título y metadatos).
    - `DELETE /api/commerce/product-masters/{id}/images/{image_id}` (eliminación física en Cloudinary y en BD, con reasignación inteligente de portada).
  - Suite de pruebas unitarias exhaustiva (16 tests en `tests/test_commerce.py`, 85 tests en toda la aplicación, 100% pasando).
  - Documentación técnica y guía de integración para frontend con PrimeNG 21 en `docs/commerce/03_FRONTEND_INTEGRATION_GUIDE.md`.
- [x] Motor de Enlaces Externos Multi-Portal para Fichas Maestras (`commerce_product_master_external_link`):
  - Entidad SQLModel `ProductMasterExternalLink` y tabla singular `commerce_product_master_external_link` con campos: `product_master_id`, `url`, `portal`, `label`, `is_primary`, `is_public`, `sort_order`, `created_at`, `updated_at`.
  - Migración Alembic `d93fce7fce21` (extracción y desdoblamiento de 168 enlaces) y `b3ff00d4f9b4` (renombrado semántico a `commerce_product_master_external_link`, adición de `is_public` y eliminación de la columna redundante `external_info_url` en `commerce_product_master`) aplicadas con éxito tanto en BD Local (`localhost`) como en BD VPS (`172.23.51.247`).
  - Clasificación automática e inteligente de portales (`detect_portal`): Amazon (UK, ES, MX, DE, FR, IT, AU, NL, CA, JP), eBay, Alibaba, AliExpress, Walmart, MercadoLibre, YouTube, TikTok y dominios genéricos sin requerir dropdowns manuales.
  - Visibilidad pública granular: bandera `is_public: bool` que permite distinguir enlaces públicos para compradores (Amazon, YouTube) de enlaces confidenciales de almacén/compra mayorista (Alibaba, 1688).
  - Retrocompatibilidad transparente: `ProductMasterRead.external_info_url` se expone dinámicamente a partir del enlace principal activo, garantizando cero roturas en frontend.
  - Endpoints REST completos:
    - `POST /api/commerce/product-masters/{id}/links`
    - `GET /api/commerce/product-masters/{id}/links?only_public=false`
    - `PATCH /api/commerce/product-masters/{id}/links/{link_id}`
    - `PATCH /api/commerce/product-masters/{id}/links/{link_id}/primary`
    - `PUT /api/commerce/product-masters/{id}/links/reorder`
    - `DELETE /api/commerce/product-masters/{id}/links/{link_id}`
  - Suite de pruebas unitarias exhaustiva (19 tests en `tests/test_commerce.py`, 88 tests en toda la aplicación, 100% pasando).
- [x] Unificación y soporte de múltiples publicaciones en Marketplace (`link_type: 'MARKETPLACE'` vs `'REFERENCE'`):
  - Se añadió la columna `link_type` a `commerce_product_master_external_link` (`VARCHAR(20)`, con índice, default `'REFERENCE'`).
  - Migración Alembic `a91497080946`: migró los 78 enlaces existentes de `marketplace_url` a registros de tipo `'MARKETPLACE'` con `portal = 'FACEBOOK'`, y eliminó la columna física `marketplace_url` de `commerce_product_master`.
  - Soporte de múltiples publicaciones simultáneas por producto (ej. cuentas de Liz y Henry) con etiquetas personalizadas (`label`), auditoría de autor (`created_by_id`) y fecha de publicación (`created_at`).
  - Sincronización automática de `is_published_marketplace = True` al agregar una publicación comercial.
  - Exposición dinámica en `ProductMasterRead`: `marketplace_url` (retrocompatible con el primario de marketplace), `external_info_url` (primario de referencia), `reference_links`, `marketplace_links`, y sus contadores independientes.
  - Filtro por tipo en el endpoint `GET /api/commerce/product-masters/{id}/links?link_type=MARKETPLACE`.
  - Cobertura completa de tests en `tests/test_commerce.py` (88/88 tests pasando, Ruff y Mypy en 100% verde).
- [x] Arquitectura de Rondas de Inversión y Modalidades de Costeo por Lote:
  - Adición de la columna `costing_method` a `commerce_batch` con valores soportados: `WEIGHTED_RETAIL`, `SPECIFIC_ITEM`, `FLAT_AVERAGE`.
  - Migración Alembic `b712823239b1` aplicada exitosamente en Local y Neon PostgreSQL.
  - Implementación del costeo Top-Down ponderado (`allocate_relative_costs`) basado en `published_price` con absorción de mermas y reconciliación de centavos.
  - Implementación del costeo Bottom-Up (`recalculate_from_products`) para compras bajo demanda / mayoristas donde el lote totaliza a partir del `cost_price` individual.
  - Auto-sincronización de Rondas de Inversión (`recalculate_round`): actualización atómica de `capital_invested = sum(batch.total_cost)` y seguimiento de punto de equilibrio (`IN_RECOVERY` → `NEAR_BREAKEVEN` → `RECOVERED` → `LIQUIDATED`) vinculado a ventas reales.
  - Endpoints de métricas financieras de ronda (`GET /api/commerce/rounds/{id}/metrics`) y recálculo manual (`POST /api/commerce/rounds/{id}/recalculate`).
  - Cobertura completa de tests unitarios e integrados (110 tests pasando al 100%, Ruff y Mypy en verde).

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
