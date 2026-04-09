---
description: Run Alembic database migrations
agent: code
---
Run Alembic database migrations.

If `$1` is `generate`, create a new migration:
`alembic revision --autogenerate -m "$ARGUMENTS"`

Otherwise, run migrations to the latest revision:
`alembic upgrade head`

Important:
- All models must be imported in `alembic/env.py` to be detected
- Never use `create_all()` in production, always use Alembic
- Review auto-generated migrations before applying
