# Project Brief - Uyuni Backend

## Overview
Uyuni Backend is a Python/FastAPI enterprise backend application designed to serve as the transactional API and ERP engine for commercial ventures (such as Nova Box Bolivia and white-label client businesses). It provides a robust foundation with comprehensive authentication, RBAC authorization, modular architecture, and CDC audit logging.

## Core Objectives
1. Provide a secure, high-performance, and scalable REST API
2. Implement Role-Based Access Control (RBAC) with domain manifests and granular permissions
3. Support modular domain-driven architecture (DDD-Lite)
4. Enable comprehensive CDC audit logging for compliance and operational tracking
5. Power transactional commercial operations (sales, batches, inventory, pricing controls)

## Technology Stack
- **Framework**: FastAPI (Python 3.14.6)
- **ORM**: SQLModel (SQLAlchemy 2.0 + Pydantic v2)
- **Database**: PostgreSQL (with strict Singular Table Naming Convention)
- **Authentication**: JWT with access/refresh token rotation
- **Migrations**: Alembic
- **Logging**: Structlog (structured logging)
- **Testing**: Pytest (In-Memory SQLite)
- **Code Quality**: Ruff (linting), Mypy (type checking)

## Key Features
- JWT-based authentication with token rotation
- Account lockout mechanism for security
- Granular RBAC with CRUD permissions per module
- Audit trail system with SQLAlchemy event hooks (CDC)
- Modular domain structure (commerce, core, tasks)
- Dynamic modular catalogs with high-performance bulk loader (`/api/catalogs/bulk`)
- Generic repository pattern for data access
- Custom exception handling

## Project Structure
```
app/
├── auth/           # Authentication and authorization
├── core/           # Core utilities, config, database, manifests, catalogs
│   └── audit/      # Audit logging system
├── models/         # SQLModel database models (user, role, module, audit, mixins)
├── modules/        # Domain modules
│   ├── commerce/   # Commerce domain (products, batches, sales, catalogs)
│   ├── core/       # Core business domain (users, configuration)
│   └── tasks/      # Task management domain
└── util/           # Utility functions
```

## Target Users
- System administrators managing accounts and security
- Commercial managers and sales operators
- Developers building on top of the API
- Enterprise clients requiring audit compliance

## Success Metrics
- Clean code following SOLID principles
- Comprehensive test coverage (52+ passing tests)
- Type-safe codebase with mypy validation (0 errors in 100+ files)
- Strict singular table naming across the entire database
- Consistent error handling and well-documented API endpoints
