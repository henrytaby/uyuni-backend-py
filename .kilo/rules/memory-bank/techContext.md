# Technical Context - Uyuni Backend

## Technology Stack

### Core Framework
- **FastAPI**: Modern async Python web framework with automatic OpenAPI documentation
- **Python 3.10+**: Using modern type hints and pattern matching
- **Pydantic v2**: Data validation and settings management

### Database Layer
- **SQLModel**: ORM combining SQLAlchemy and Pydantic
- **PostgreSQL**: Primary database (production)
- **SQLite**: Development/testing database
- **Alembic**: Database migration tool

### Authentication
- **JWT**: JSON Web Tokens for stateless authentication
- **bcrypt**: Password hashing algorithm
- **python-jose**: JWT encoding/decoding library

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
Python 3.10+
PostgreSQL 14+ (or SQLite for development)
```

### Installation
```bash
# Create virtual environment
python -m venv env
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload
```

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
│   ├── models/            # Database models
│   ├── modules/           # Domain modules
│   │   ├── assets/            # Asset management
│   │   ├── core/              # Organizational management
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

### Assets Module
- `/assets/assets` - Asset CRUD
- `/assets/areas` - Area CRUD
- `/assets/groups` - Group CRUD
- `/assets/statuses` - Status CRUD
- `/assets/institutions` - Institution CRUD
- `/assets/acts` - Act CRUD

### Core Module
- `/core/org-units` - Organizational units CRUD
- `/core/positions` - Positions CRUD
- `/core/staff` - Staff CRUD

### Tasks Module
- `/tasks/tasks` - Task CRUD

## Database Schema

### Core Tables
- `users` - User accounts
- `roles` - User roles
- `role_modules` - Role-permission mappings
- `modules` - System modules

### Audit Table
- `audit_entries` - Audit log records

### Domain Tables
- `assets` - Institutional assets
- `areas` - Physical locations
- `groups` - Logical groupings
- `statuses` - Asset states
- `institutions` - Organizations
- `acts` - Asset transactions

- `org_units` - Organizational units
- `positions` - Job positions
- `staff` - Staff assignments

- `tasks` - Tasks

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
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_rbac.py
```

### Test Structure
- `tests/conftest.py` - Fixtures and test configuration
- `tests/test_*.py` - Integration tests
- `tests/auth/` - Authentication-specific tests
