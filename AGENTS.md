# Uyuni Backend - Project Instructions

## Project Overview
Uyuni Backend is a Python/FastAPI enterprise backend with JWT auth, RBAC, audit logging, and modular domain architecture (assets, core, tasks).

## Tech Stack
- **Framework**: FastAPI (Python 3.10+) with Pydantic v2
- **ORM**: SQLModel (SQLAlchemy + Pydantic), async
- **Database**: PostgreSQL (prod) / SQLite (dev/test)
- **Auth**: JWT with access/refresh token rotation, bcrypt
- **Migrations**: Alembic
- **Logging**: structlog
- **Quality**: Ruff (lint), Mypy (types), pytest
- **Deployment**: Vercel Serverless

## Architecture
```
Routers (API) → Services (logic) → Repositories (data) → Models (entities)
```

### Module Structure (DDD-lite)
Each domain module contains: `routers.py`, `service.py`, `repository.py`, `models.py`, `schemas.py`
- **Flat Hierarchy**: Base domains contain sibling submodules
- **Nested Routing**: Root module routers act as unified aggregators

## Key Patterns
- **Repository Pattern**: Generic `BaseRepository[T]` with CRUD interface
- **Dependency Injection**: FastAPI `Depends()` throughout
- **RBAC**: User → Role → RoleModule → Module + Permissions (CRUD)
- **Audit**: Middleware captures request context + SQLAlchemy hooks for CDC

## Code Conventions
- Strict Clean Code principles (SOLID, DRY, KISS)
- Complete type hints required
- Use structlog for all logging (never print())
- Custom exceptions: `NotFoundException`, `ForbiddenException`
- All models must be imported in `alembic/env.py`
- Use Alembic migrations (never `create_all()` in production)
- In-Memory SQLite for tests

## Commands
- `/test` - Run tests with pytest
- `/lint` - Run Ruff linting and formatting
- `/typecheck` - Run Mypy type checking
- `/migrate` - Run Alembic database migrations

## Memory Bank
Detailed project context is maintained in `.kilo/rules/memory-bank/`:
- `projectbrief.md` - Project objectives and features
- `productContext.md` - User personas and workflows
- `systemPatterns.md` - Architecture and design patterns
- `techContext.md` - Tech stack and project structure
- `progress.md` - Milestones and current status
- `developerPersona.md` - Developer role definition
