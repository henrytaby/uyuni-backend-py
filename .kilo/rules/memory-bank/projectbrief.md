# Project Brief - Uyuni Backend

## Overview
Uyuni Backend is a Python/FastAPI backend application designed to serve as the API layer for the Uyuni system. It provides a robust foundation for enterprise-level applications with comprehensive authentication, authorization, and modular architecture.

## Core Objectives
1. Provide a secure and scalable REST API
2. Implement Role-Based Access Control (RBAC) for granular permissions
3. Support modular domain-driven architecture
4. Enable comprehensive audit logging for compliance
5. Facilitate asset management and organizational structure management

## Technology Stack
- **Framework**: FastAPI (Python 3.10+)
- **ORM**: SQLModel (SQLAlchemy + Pydantic)
- **Database**: PostgreSQL
- **Authentication**: JWT with access/refresh token rotation
- **Migrations**: Alembic
- **Logging**: Structlog (structured logging)
- **Testing**: Pytest
- **Code Quality**: Ruff (linting), Mypy (type checking)

## Key Features
- JWT-based authentication with token rotation
- Account lockout mechanism for security
- Granular RBAC with CRUD permissions per module
- Audit trail system with SQLAlchemy hooks
- Modular domain structure (assets, core, tasks)
- Generic repository pattern for data access
- Custom exception handling

## Project Structure
```
app/
├── auth/           # Authentication and authorization
├── core/           # Core utilities, config, database
│   └── audit/      # Audit logging system
├── models/         # SQLModel database models
├── modules/        # Domain modules
│   ├── assets/     # Asset management domain
│   ├── core/       # Core business domain (org units, positions, staff)
│   └── tasks/      # Task management domain
└── util/           # Utility functions
```

## Target Users
- System administrators managing organizational structures
- Asset managers tracking institutional assets
- Developers building on top of the API
- Enterprise clients requiring audit compliance

## Success Metrics
- Clean code following SOLID principles
- Comprehensive test coverage
- Type-safe codebase with mypy validation
- Consistent error handling
- Well-documented API endpoints
