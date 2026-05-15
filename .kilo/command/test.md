---
description: Run tests with pytest
agent: code
---
Run the test suite using pytest.

Execute: `venv/bin/pytest $ARGUMENTS`

If $1 is provided, run tests for that specific file or directory (e.g., `/test tests/test_auth.py`).
If no arguments, run the full test suite.

**Important**: Always use `venv/bin/pytest` — never run bare `pytest` as it may use the system Python instead of the project venv (Python 3.12).

After running, analyze any failures and fix them if requested.
Use `venv/bin/pytest -v` for verbose output and `venv/bin/pytest --cov=app` for coverage.
