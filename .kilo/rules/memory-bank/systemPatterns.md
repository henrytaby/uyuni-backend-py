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
class NotFoundException(HTTPException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)

class ForbiddenException(HTTPException):
    def __init__(self, detail: str = "Access denied"):
        super().__init__(status_code=403, detail=detail)
```

### Global Handlers
Registered in `app/core/handlers.py`:
- `NotFoundException` → 404 response
- `ForbiddenException` → 403 response
- Generic `Exception` → 500 response (with logging)

## Configuration

### Environment Variables
```python
class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30
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
alembic revision --autogenerate -m "description"
alembic upgrade head
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
