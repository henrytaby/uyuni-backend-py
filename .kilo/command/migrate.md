---
description: Run Alembic database migrations
agent: code
---
Run Alembic database migrations.

If `$1` is `generate`, create a new migration:
`venv/bin/alembic revision --autogenerate -m "$ARGUMENTS"`

Otherwise, run migrations to the latest revision:
`venv/bin/alembic upgrade head`

**Important**: Always use `venv/bin/alembic` — never run bare `alembic` as it may use the system Python instead of the project venv (Python 3.12).

Important:
- All models must be imported in `alembic/env.py` to be detected
- Never use `create_all()` in production, always use Alembic
- Review auto-generated migrations before applying
