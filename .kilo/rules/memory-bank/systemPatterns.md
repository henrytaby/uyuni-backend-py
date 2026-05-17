# System Patterns - Uyuni Backend

## Architecture Overview

### Layered Architecture
The application follows a clean layered architecture:

```
┌─────────────────────────────────────────────┐
│                 Routers (API)                │  ← HTTP handlers, validation
├─────────────────────────────────────────────┤
│                 Services                     │  ← Business logic, orchestration
├─────────────────────────────────────────────┤
│               Repositories                   │  ← Data access, queries
├─────────────────────────────────────────────┤
│                 Models                       │  ← Database entities, schemas
└─────────────────────────────────────────────┘
```

### Domain-Driven Structure (DDD-lite)
Modules are organized by domain (assets, core, tasks), with **Nested Routing** support:

- **Flat Hierarchy**: Base domains (e.g., `core`, `assets`) contain sibling submodules to avoid excessive depth
- **Nested Routing**: Each root module (e.g., `core/routers.py`) acts as a unified aggregator
- **Components per Module**:
    - `routers.py`: API Endpoints (Aggregator or Specific)
    - `service.py`: Business Logic
    - `repository.py`: Data Access (inherits from `BaseRepository`)
    - `models.py`: SQLModel Entities
    - `schemas.py`: Pydantic DTOs

## Design Patterns

### Repository Pattern
Generic base repository with type parameter:

```python
class BaseRepository[T](Protocol):
    def get_by_id(self, id: int) -> T | None: ...
    def get_all(self, skip: int, limit: int) -> list[T]: ...
    def create(self, entity: T) -> T: ...
    def update(self, entity: T) -> T: ...
    def delete(self, id: int) -> bool: ...
```

Benefits:
- Separation of concerns
- Testability through mocking
- Consistent CRUD interface

### Dependency Injection
FastAPI's `Depends()` used throughout:

```python
@router.get("/assets")
def list_assets(
    service: AssetService = Depends(get_asset_service),
    current_user: User = Depends(get_current_active_user)
):
    ...
```

### Middleware Pattern
- Audit middleware captures request context
- SQLAlchemy hooks capture entity changes
- Context variables pass request info to hooks

### Dynamic Modular Catalogs Pattern
- **Unified Registry**: A central `global_registry` stores mapping from slugs to `CatalogProvider` protocols.
- **Self-Registration**: Done inside domain catalogs module initialization (e.g. `app/modules/core/catalogs/__init__.py`) avoiding cyclical imports and redundant database route files.
- **Dual Endpoint Design**:
  - `GET /api/catalogs/{name}`: Retrieve an individual list dynamically.
  - `POST /api/catalogs/bulk`: Receive a JSON mapping of catalog requests and parameters, resolving all in a single payload to minimize network request roundtrips in frontend components.

## Key Components

### Authentication Flow
```
Login → Validate Credentials → Check Lockout → Generate Tokens
         ↓                      ↓
    Failed Attempts         Lock Account (5 failures)
```

Features:
- **Token Rotation**: Refresh tokens are rotated (invalidated) on every use
- **Robust Logout**: Tokens are revoked via blacklist (`UserRevokedToken`) upon logout

### RBAC System
```
User → Role → RoleModule → Module + Permissions (CRUD)
```

Permission check:
```python
has_permission(user, module, action) → bool
```

Features:
- **PermissionChecker**: Dependency verifies aggregated permissions from all user roles
- **Implicit Read**: Assigning a module to a role grants read access
- **Superuser**: Bypasses all RBAC key checks

### Audit System
```
Request → Middleware (capture context) → SQLAlchemy Hooks → Audit Entry
```

Architecture:
- **Access Logging**: Logs User, IP, Path, Status Code for every request
- **CDC (Change Data Capture)**: Logs `old` vs `new` values for `INSERT`, `UPDATE`, `DELETE`
- **Cold Storage**: Script to archive and prune old logs (`scripts/archive_audit.py`)

## Data Models

### Core Entities
- **User**: Authentication, role assignment
- **Role**: Permission container
- **RoleModule**: Role-Module-Permission mapping
- **Module**: System module (assets, core, tasks)

### Domain Entities
- **Asset**: Equipment/items with area, group, status
- **Area**: Physical location
- **Group**: Logical grouping
- **Status**: Asset state
- **Institution**: Organization
- **Act**: Asset transaction/assignment

- **OrgUnit**: Organizational unit (hierarchical)
- **Position**: Job position
- **Staff**: Person assignment

## Error Handling

### Custom Exceptions
```python
class CustomException(Exception):
    def __init__(self, detail: Any, headers: Optional[dict[str, str]] = None):
        self.detail = detail
        self.headers = headers

class NotFoundException(CustomException): ...
class BadRequestException(CustomException): ...
class UnauthorizedException(CustomException): ...
class ForbiddenException(CustomException): ...
class InternalServerErrorException(CustomException): ...
```

### Global Handlers
Registered in `app/core/handlers.py` — each handler maps an exception to its HTTP status code:
- `NotFoundException` → 404 response
- `BadRequestException` → 400 response
- `UnauthorizedException` → 401 response
- `ForbiddenException` → 403 response
- `InternalServerErrorException` → 500 response (with logging)

## Configuration

### Environment Variables
```python
class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "Uyuni-BackEnd"
    VERSION: str = "v1"
    PORT: int = 8000
    ENVIRONMENT: str = "local"

    # CORS
    BACKEND_CORS_ORIGINS: list[AnyHttpUrl] = []

    # Database
    DATABASE_URL: str

    # Auth
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Security Lockout
    SECURITY_LOGIN_MAX_ATTEMPTS: int = 5
    SECURITY_LOCKOUT_MINUTES: int = 15

    # Utils
    TIME_ZONE: int
    PROJECT_ROOT: str = ...

    # Audit
    ENABLE_ACCESS_AUDIT: bool = True
    ENABLE_DATA_AUDIT: bool = True

    # Log Controls
    ENABLE_ACCESS_LOGS: bool = True
    ACCESS_LOGS_ONLY_ERRORS: bool = False
    AUDIT_EXCLUDED_PATHS: list[str] = [...]
    AUDIT_LOG_EXCLUDE_STATUS_CODES: list[int] = [404]
    AUDIT_LOG_INCLUDED_METHODS: list[str] = ["GET", "POST", "PUT", "PATCH", "DELETE"]
```

### Database Connection
- Async engine for queries
- Session per request (dependency injection)
- Connection pooling for production

## Testing Strategy

### Test Categories
1. **Unit Tests**: Services, utilities
2. **Integration Tests**: API endpoints
3. **Security Tests**: Auth, RBAC

### Test Fixtures
```python
@pytest.fixture
def db_session(): ...

@pytest.fixture
def test_user(): ...

@pytest.fixture
def auth_headers(): ...
```

### In-Memory SQLite
Tests run against an **In-Memory SQLite** database (`tests/conftest.py`) to ensure speed and isolation.

## Deployment

### Vercel Serverless
- `vercel.json` configuration
- Environment variables via Vercel dashboard
- Alembic migrations run separately

### Database Migrations
```bash
venv/bin/alembic revision --autogenerate -m "description"
venv/bin/alembic upgrade head
```

**Critical**: Models MUST be imported in `alembic/env.py` to be detected.

## Documentation

- `/docs` - Swagger UI
- `/redoc` - Custom CDN version (to avoid errors)
- `/` - Landing page

### Reference Documentation
- `docs/RBAC_GUIDE.md` - Role-Based Access Control
- `docs/AUTHENTICATION_GUIDE.md` - JWT Authentication
- `docs/ALEMBIC_GUIDE.md` - Database Migrations
- `docs/AUDIT_GUIDE.md` - Audit System
- `docs/ASSETS_MODULE_GUIDE.md` - Assets module usage
- `docs/AUTH_ANALYSIS.md` - Authentication analysis
- `docs/CODE_STANDARDS_REVIEW.md` - Code standards review
- `docs/CORE_MODULE_GUIDE.md` - Core module usage
- `docs/DESIGN_PATTERNS_GUIDE.md` - Design patterns reference
- `docs/DEVELOPER_GUIDE.md` - Developer onboarding guide
- `docs/EXCEPTION_HANDLING_GUIDE.md` - Exception handling patterns
- `docs/FRONTEND_AUTH_GUIDE.md` - Frontend authentication integration
- `docs/OBSERVABILITY_GUIDE.md` - Observability and monitoring
- `docs/PROJECT_ANALYSIS.md` - Project analysis
- `docs/PROJECT_ANALYSIS_REVIEW.md` - Project analysis review
- `docs/QUALITY_GUIDE.md` - Code quality standards
- `docs/QUERY_SYSTEM_GUIDE.md` - Query system guide
- `docs/SOLID_GUIDE.md` - SOLID principles reference
- `docs/TESTING_GUIDE.md` - Testing strategy and patterns

### Utility Scripts
- `scripts/archive_audit.py` - Archive and prune old audit logs (cold storage)
- `scripts/demo_audit.py` - Audit system demonstration
- `scripts/reset_db_schema.py` - Reset database schema
