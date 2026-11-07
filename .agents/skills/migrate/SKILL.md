---
name: migrate
description: Run or generate Alembic database migrations
---

# Database Migration Skill

Manage database schema versions using Alembic.

## Execution

### Apply Migrations
```bash
venv/bin/alembic upgrade head
```

### Generate Migration
```bash
venv/bin/alembic revision --autogenerate -m "descripcion_del_cambio"
```

### Critical Rules
1. **Model Registration**: All SQLModel models must be imported in `alembic/env.py` before generating a migration.
2. **Review Changes**: Always inspect the auto-generated migration script in `alembic/versions/` before applying `upgrade head`.
3. **Production Safety**: Never use `create_all()` in production; always apply schema changes via Alembic migrations.

> [!IMPORTANT]
> Always use `venv/bin/alembic` — never run bare `alembic`.

