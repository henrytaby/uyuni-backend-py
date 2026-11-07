---
name: lint
description: Run Ruff linting and formatting on the codebase
---

# Linting & Formatting Skill

Run Ruff to check, autofix, and format Python code across the application and tests.

## Execution

```bash
venv/bin/ruff check app/ tests/ --fix && venv/bin/ruff format app/ tests/
```

### Guidelines
1. Runs linter with automatic fixes on `app/` and `tests/`.
2. Formats all files according to project configuration in `pyproject.toml`.
3. Review any manual lint errors that could not be automatically resolved.

> [!IMPORTANT]
> Always use `venv/bin/ruff` — never run bare `ruff`.

