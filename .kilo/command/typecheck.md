---
description: Run Mypy type checking
agent: code
---
Run Mypy static type checking on the project.

Execute: `venv/bin/mypy app/ --ignore-missing-imports`

**Important**: Always use `venv/bin/mypy` — never run bare `mypy` as it may use the system Python instead of the project venv (Python 3.12).

After running, analyze any type errors and fix them.
Focus on:
- Missing type hints
- Incorrect type annotations
- Import resolution issues
