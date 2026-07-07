# Uyuni Backend - Project Instructions

## Project Overview
Uyuni Backend is a Python/FastAPI enterprise backend with JWT auth, RBAC, audit logging, and modular domain architecture (assets, core, tasks).

## Tech Stack
- **Framework**: FastAPI (Python 3.14) with Pydantic v2
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Database**: PostgreSQL (prod) / SQLite (dev/test)
- **Auth**: JWT with access/refresh token rotation, bcrypt
- **Migrations**: Alembic
- **Logging**: structlog
- **Quality**: Ruff (lint), Mypy (types), pytest

## Architecture
```
Routers (API) → Services (logic) → Repositories (data) → Models (entities)
```

### Module Structure (DDD-lite)
Each domain module contains: `routers.py`, `service.py`, `repository.py`, `models.py`, `schemas.py`
- **Flat Hierarchy**: Base domains contain sibling submodules
- **Nested Routing**: Root module routers act as unified aggregators

## Key Patterns
- **Repository Pattern**: Generic `BaseRepository[T]` with CRUD interface (`get_by_id`, `get_all`, `count`, `create`, `update`, `delete`)
- **Dependency Injection**: FastAPI `Depends()` throughout
- **RBAC**: User → Role → RoleModule → Module + Permissions (`can_create`, `can_update`, `can_delete`, `scope_all`; read is implicit)
- **Audit**: Middleware captures request context + SQLAlchemy hooks for CDC
- **ETL Synchronization**: Python scripts (e.g. `sync_siger.py`) using Upsert and Soft-Delete (`is_active=False`) mapping sequential external IDs to internal `UUIDv7` keys (`external_id`).
- **Dynamic Modular Catalogs**: A decoupled, zero-boilerplate registration mechanism (`CatalogProvider` protocol) mapping catalog slugs to queries inside domain modules (`app/modules/core/catalogs/__init__.py`). It registers providers into the central `global_registry` and exposes a dynamic individual selector (`GET /api/catalogs/{name}`) alongside an efficient high-performance batch loader (**`POST /api/catalogs/bulk`**) that gathers multiple datasets in a single HTTP request to minimize selectbox-population overhead on the frontend.

## Code Conventions
- Strict Clean Code principles (SOLID, DRY, KISS)
- Complete type hints required
- Use structlog for all logging (never print())
- Custom exceptions: `NotFoundException`, `ForbiddenException`, `BadRequestException`, `UnauthorizedException`, `InternalServerErrorException` (all extend `CustomException`)
- All models must be imported in `alembic/env.py`
- Use Alembic migrations (never `create_all()` in production)
- In-Memory SQLite for tests

## Virtual Environment
- The project uses a **venv** located at `venv/` in the project root
- **All Python commands must be run inside the venv** — use `venv/bin/<tool>` to execute tools
- Examples: `venv/bin/pytest`, `venv/bin/ruff`, `venv/bin/mypy`, `venv/bin/alembic`, `venv/bin/python`
- Never run Python tools without the venv prefix (e.g., do NOT run bare `pytest`, `ruff`, `mypy`, `alembic`)
- To activate interactively: `source venv/bin/activate`

## Commands
- `/test` - Run tests with pytest
- `/lint` - Run Ruff linting and formatting
- `/typecheck` - Run Mypy type checking
- `/migrate` - Run Alembic database migrations

**Note**: All commands automatically use the project venv (`venv/bin/`).

## AI Agent Configuration (`.kilo/`)

This project uses a `.kilo/` configuration directory for AI agent tooling.
Other AI tools (Cursor, Gemini, Qwen, Kimi, Cline, etc.) can reference these files for full project context.

### Root Config
- `kilo.json` - Points to all instruction files and sets `code` as default agent

### Agents (`.kilo/agent/`)
- `code.md` - **Primary agent**: Senior Backend Developer with full edit/bash permissions. Handles coding, testing, migrations, and linting.
- `architect.md` - **Sub-agent**: Architecture and database design specialist. Read-heavy with restricted edits. Invoked internally by `code` for strategic decisions.

### Commands (`.kilo/command/`)
- `test.md` - Defines `/test` command: runs `pytest $ARGUMENTS` with optional file/directory targeting
- `lint.md` - Defines `/lint` command: runs `ruff check --fix` + `ruff format` on `app/` and `tests/`
- `typecheck.md` - Defines `/typecheck` command: runs `mypy app/ --ignore-missing-imports`
- `migrate.md` - Defines `/migrate` command: runs `alembic upgrade head` or `alembic revision --autogenerate` with a message

### Memory Bank (`.kilo/rules/memory-bank/`)
Detailed project context maintained across sessions:
- `projectbrief.md` - Project objectives, features, structure, target users, and success metrics
- `productContext.md` - User personas (Admin, Asset Manager, Staff Manager, Auditor), workflows, and technical constraints
- `systemPatterns.md` - Architecture layers, design patterns (Repository, DI, RBAC, Audit), data models, error handling, and testing strategy
- `techContext.md` - Tech stack details, dev setup, environment variables, project structure, API endpoints, database schema, and deployment
- `progress.md` - Completed milestones (5 phases), in-progress items, pending features, known issues, and technical debt
- `developerPersona.md` - Developer role definition: Senior Backend Architect with 10 core competencies and response style guidelines
