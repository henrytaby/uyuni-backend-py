---
description: Run Ruff linting and formatting
agent: code
---
Run Ruff to check and fix linting issues.

Execute: `ruff check app/ tests/ --fix && ruff format app/ tests/`

This will:
1. Check for lint errors and auto-fix them
2. Format all Python files according to project style

After running, review any remaining issues that couldn't be auto-fixed.
