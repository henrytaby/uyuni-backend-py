---
name: test
description: Run test suite using pytest with optional file or directory targeting
---

# Test Execution Skill

Run integration and unit tests using `pytest` inside the project virtual environment.

## Execution

```bash
venv/bin/pytest $ARGUMENTS
```

### Usage Examples
- Full suite: `venv/bin/pytest`
- Specific file: `venv/bin/pytest tests/auth/test_active_role.py`
- Specific test name pattern: `venv/bin/pytest -k "create"`
- Verbose output: `venv/bin/pytest -v`
- Coverage report: `venv/bin/pytest --cov=app`

> [!IMPORTANT]
> Always use `venv/bin/pytest` — never run bare `pytest` to prevent using the system Python instead of the project venv (Python 3.14.6).

