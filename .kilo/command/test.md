---
description: Run tests with pytest
agent: code
---
Run the test suite using pytest.

Execute: `pytest $ARGUMENTS`

If $1 is provided, run tests for that specific file or directory (e.g., `/test tests/test_auth.py`).
If no arguments, run the full test suite.

After running, analyze any failures and fix them if requested.
Use `pytest -v` for verbose output and `pytest --cov=app` for coverage.
