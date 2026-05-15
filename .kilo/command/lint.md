---
description: Run Ruff linting and formatting
agent: code
---
Run Ruff to check and fix linting issues.

Execute: `venv/bin/ruff check app/ tests/ --fix && venv/bin/ruff format app/ tests/`

**Important**: Always use `venv/bin/ruff` — never run bare `ruff` as it may use the system Python instead of the project venv (Python 3.12).

This will:
1. Check for lint errors and auto-fix them
2. Format all Python files according to project style

After running, review any remaining issues that couldn't be auto-fixed.
