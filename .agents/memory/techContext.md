# Technical Context - Uyuni Backend

## Technology Stack

### Core Framework
- **FastAPI**: Modern async Python web framework with automatic OpenAPI documentation
- **Python 3.14.6**: Using modern type hints, pattern matching, and performance improvements
- **Pydantic v2**: Data validation and settings management

### Database Layer
- **SQLModel**: ORM combining SQLAlchemy and Pydantic
- **PostgreSQL**: Primary database (production)
- **SQLite**: Development/testing database
- **Alembic**: Database migration tool

### Authentication
- **JWT**: JSON Web Tokens for stateless authentication
- **bcrypt**: Password hashing algorithm
- **PyJWT**: JWT encoding/decoding library

### Code Quality
- **Ruff**: Fast Python linter (replaces flake8, isort)
- **Mypy**: Static type checker
- **pytest**: Testing framework
- **pytest-asyncio**: Async test support

### Logging & Observability
- **structlog**: Structured logging library
- Context-aware logging with request tracing

## Development Setup

### Prerequisites
```bash
Python 3.14.6
PostgreSQL 14+ (or SQLite for development)
```

### Installation
```bash
# Create virtual environment
python3.14 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
venv/bin/alembic upgrade head

# Start development server
venv/bin/uvicorn app.main:app --reload
```

### Virtual Environment
- The project uses a **venv** located at `venv/` in the project root
- **All Python commands must be run inside the venv** — use `venv/bin/<tool>` to execute tools
- Examples: `venv/bin/pytest`, `venv/bin/ruff`, `venv/bin/mypy`, `venv/bin/alembic`, `venv/bin/python`
- Never run Python tools without the venv prefix (e.g., do NOT run bare `pytest`, `ruff`, `mypy`, `alembic`)
- To activate interactively: `source venv/bin/activate`

### Environment Variables
| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_NAME` | Application name | `"Uyuni-BackEnd"` |
| `VERSION` | API version | `"v1"` |
| `PORT` | Server port | `8000` |
| `ENVIRONMENT` | Runtime environment | `"local"` |
| `BACKEND_CORS_ORIGINS` | Allowed CORS origins | `[]` |
| `DATABASE_URL` | PostgreSQL connection string | **Required** |
| `SECRET_KEY` | JWT signing key | **Required** |
| `ALGORITHM` | JWT algorithm | **Required** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (minutes) | **Required** |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh token lifetime (days) | **Required** |
| `SECURITY_LOGIN_MAX_ATTEMPTS` | Failed attempts before lockout | `5` |
| `SECURITY_LOCKOUT_MINUTES` | Account lockout duration (minutes) | `15` |
| `TIME_ZONE` | UTC offset | **Required** |
| `ENABLE_ACCESS_AUDIT` | Enable access audit logging | `True` |
| `ENABLE_DATA_AUDIT` | Enable CDC audit logging | `True` |
| `ENABLE_ACCESS_LOGS` | Master switch for access logging | `True` |
| `ACCESS_LOGS_ONLY_ERRORS` | Only log 4xx/5xx responses | `False` |

## Project Structure

```
uyuni-backend-py/
├── app/
│   ├── auth/              # Authentication module
│   │   ├── dependencies.py    # FastAPI dependencies
│   │   ├── permissions.py     # RBAC permission checking
│   │   ├── routers.py         # Auth endpoints
│   │   ├── schemas.py         # Request/response schemas
│   │   ├── service.py         # Business logic
│   │   └── utils.py           # Password/token utilities
│   ├── core/              # Core utilities
│   │   ├── audit/             # Audit logging system
│   │   ├── config.py          # Settings/configuration
│   │   ├── db.py              # Database connection
│   │   ├── exceptions.py      # Custom exceptions
│   │   ├── handlers.py        # Exception handlers
│   │   ├── logging.py         # Logging configuration
│   │   ├── repository.py      # Base repository pattern
│   │   └── routers.py         # Health check endpoint
│   ├── models/            # Database models (user, role, module, audit, mixins)
│   ├── modules/           # Domain modules
│   │   ├── commerce/          # Commerce domain (products, batches, sales, catalogs)
│   │   ├── core/              # Core business domain (users, configuration)
│   │   └── tasks/             # Task management
│   ├── util/              # Utility functions
│   └── main.py            # FastAPI application entry
├── alembic/               # Database migrations
├── tests/                 # Test suite
├── docs/                  # Documentation
├── seeds/                 # Database seed scripts
└── scripts/               # Utility scripts
    ├── archive_audit.py       # Archive and prune old audit logs
    ├── demo_audit.py          # Audit system demonstration
    └── reset_db_schema.py     # Reset database schema
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - User logout
- `GET /auth/me` - Current user info
- `PUT /auth/role` - Set active role

### Commerce Module
- `/commerce/products` - Product SKUs CRUD & status transitions
- `/commerce/product-masters` - Master product catalog definitions
- `/commerce/batches` - Import batches and landed cost control
- `/commerce/sales` - Atomic sales and items
- `/commerce/categories` - Product categories CRUD
- `/commerce/channels` - Sales channels CRUD
- `/commerce/live-baskets` - Live baskets CRUD
- `/commerce/rounds` - Investment rounds CRUD
- `/commerce/catalogs` - Dynamic catalogs hub

### Core Module
- `/core/users` - User accounts CRUD, search, and count

### Tasks Module
- `/tasks/tasks` - Task CRUD

### Dynamic Catalogs Engine
- `GET /api/catalogs/{name}` - Dynamic catalog selector
- `POST /api/catalogs/bulk` - High-performance batch catalog loader

## Database Schema (Singular Table Naming Convention)

### Core Tables
- `user` - User accounts & authentication
- `role` - User roles
- `user_role` - User-role mappings
- `role_module` - Role-permission mappings
- `module` - System modules
- `module_group` - System module groups
- `user_revoked_token` - Blacklisted revoked tokens
- `user_log_login` - User login security audit

### Audit Table
- `audit_log` - CDC change records

### Commerce Tables
- `commerce_product` - Individual product SKUs
- `commerce_product_master` - Master product definitions
- `commerce_batch` - Import containers & boxes
- `commerce_sale` - Sales transactions
- `commerce_sale_item` - Items sold per transaction
- `commerce_category` - Product categories
- `commerce_channel` - Sales channels
- `commerce_live_basket` - Live sales baskets
- `commerce_investment_round` - Investment rounds

### Tasks Table
- `task` - Operational tasks

## Deployment

### Vercel Serverless
The application is configured for Vercel serverless deployment:
- `vercel.json` contains routing configuration
- Environment variables set via Vercel dashboard
- Migrations run separately (not on each deploy)

### Production Considerations
1. Use Alembic migrations (not `create_all()`)
2. Configure connection pooling
3. Set up proper CORS origins
4. Enable HTTPS only
5. Configure rate limiting
6. Set up monitoring and alerting

## Testing

### Run Tests
```bash
# Run all tests
venv/bin/pytest

# Run with coverage
venv/bin/pytest --cov=app

# Run specific test file
venv/bin/pytest tests/test_rbac.py
```

### Test Structure
- `tests/conftest.py` - Fixtures and test configuration
- `tests/test_*.py` - Integration tests
- `tests/auth/` - Authentication-specific tests
