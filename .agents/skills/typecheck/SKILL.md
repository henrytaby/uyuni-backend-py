---
name: typecheck
description: Run Mypy static type checking on the codebase
---

# Static Type Checking Skill

Run Mypy static type verification across the application codebase.

## Execution

```bash
venv/bin/mypy app/ --ignore-missing-imports
```

### Focus Areas
- Ensure all functions, parameters, and methods have complete type annotations.
- Verify Pydantic v2 and SQLModel schema types.
- Check return types and nullable unions (`X | None`).

> [!IMPORTANT]
> Always use `venv/bin/mypy` — never run bare `mypy`.

