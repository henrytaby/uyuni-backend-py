# Uyuni Backend - Project Instructions

## Project Overview
Uyuni Backend is a Python/FastAPI enterprise backend with JWT auth, RBAC, audit logging, and modular domain architecture (assets, core, tasks).

## Tech Stack
- **Framework**: FastAPI (Python 3.14.6) with Pydantic v2
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

## AI Agent Configuration (`.agents/`)

This project uses an open, vendor-agnostic `.agents/` configuration directory for AI agent tooling and skills.
All AI tools (Cursor, Gemini CLI, Claude Code, Antigravity, Copilot, Qwen, Cline, Roo Code, etc.) can reference these files for full project context and execution workflows.

### Directory Overview
- `.agents/README.md` - Documentation of the agent standard and directory structure

### Skills (`.agents/skills/`)
Standardized agent skills with YAML frontmatter and execution steps:
- `test/SKILL.md` - Runs `venv/bin/pytest $ARGUMENTS` with optional file/directory targeting
- `lint/SKILL.md` - Runs `venv/bin/ruff check --fix` + `venv/bin/ruff format` on `app/` and `tests/`
- `typecheck/SKILL.md` - Runs `venv/bin/mypy app/ --ignore-missing-imports`
- `migrate/SKILL.md` - Runs `venv/bin/alembic upgrade head` or `venv/bin/alembic revision --autogenerate` with a message

### Personas (`.agents/personas/`)
- `code.md` - **Primary agent**: Senior Backend Developer with full edit/bash permissions. Handles coding, testing, migrations, and linting.
- `architect.md` - **Sub-agent**: Architecture and database design specialist. Read-heavy with restricted edits. Invoked for strategic and structural decisions.

### Memory Bank (`.agents/memory/`)
Detailed architectural context maintained across sessions:
- `projectbrief.md` - Project objectives, features, structure, target users, and success metrics
- `productContext.md` - User personas (Admin, Asset Manager, Staff Manager, Auditor), workflows, and technical constraints
- `systemPatterns.md` - Architecture layers, design patterns (Repository, DI, RBAC, Audit), data models, error handling, and testing strategy
- `techContext.md` - Tech stack details, dev setup, environment variables, project structure, API endpoints, database schema, and deployment
- `progress.md` - Completed milestones (5 phases), in-progress items, pending features, known issues, and technical debt
- `developerPersona.md` - Developer role definition: Senior Backend Architect with 10 core competencies and response style guidelines

### Plans (`.agents/plans/`)
- Architecture, roadmap, and transition analysis plans (e.g. SaaS multi-tenant specification).

---

## 🌐 Dominio Específico: Módulo Commerce (Nova Box Bolivia)

Este backend actúa como motor transaccional y ERP para el ecosistema comercial de **Nova Box Bolivia**:
- **Documento Maestro de Arquitectura**: Consultar `/opt/nova/nova-home-tech/docs/arquitectura/RFC-001-integracion-uyuni-novabox.md`.
- **Repositorio Comercial Origen**: `/opt/nova/nova-home-tech` (inventario histórico, fotos WebP, márgenes y manifests `NOV-XXX`).
- **Frontend de Gestión**: `/opt/uyuni/uyuni-frontend-ng` (Angular 21 + PrimeNG 21).
- **Frontend Público de Clientes**: `/opt/nova/nova-home-tech/apps/catalog-pwa` (React + Vite).
- **Módulo de Negocio (`app/modules/commerce/`)**:
  - `products`: Catálogo de SKUs (`NOV-XXX`), estados (`disponible`, `reservado`, `vendido`, `merma`), precio oficial y mínimo (`minimum_price`).
  - `batches`: Cajas y lotes importados (Ataúd 1, Ataúd 2, Amazon Next) con control de costos y punto de equilibrio.
  - `sales`: Registro atómico de ventas con métodos de pago bolivianos (QR, efectivo, flota), cliente y cálculo de ganancia neta.
  - `api/public/catalog`: Endpoint público cacheado para alimentar la PWA de clientes en tiempo real sin rebuilds.
- **Regla de Negocio Crítica**: En el servicio de ventas, nunca permitir transacciones por debajo del `minimum_price` sin confirmación explícita, y asegurar que el producto se marque como `vendido` en la misma transacción atómica.

