# AI Agents Configuration & Workspace Standard (`.agents/`)

This directory defines the cross-platform, vendor-agnostic AI agent configuration for the **Uyuni Backend** project. It works as an interoperable standard across modern AI coding assistants (Cursor, Gemini CLI, Antigravity, Claude Code, Copilot, Roo Code, Windsurf, Qwen, etc.).

---

## Directory Structure

```
.agents/
├── README.md               # This documentation file
├── skills/                 # Executable standardized agent skills
│   ├── test/SKILL.md       # Pytest execution workflow
│   ├── lint/SKILL.md       # Ruff linting & formatting workflow
│   ├── typecheck/SKILL.md  # Mypy type-checking workflow
│   └── migrate/SKILL.md    # Alembic database migration workflow
├── memory/                 # Persistent Memory Bank (Architectural Context)
│   ├── projectbrief.md     # Core requirements, target users, goals
│   ├── productContext.md   # User personas and business problem statements
│   ├── systemPatterns.md   # DDD-lite, Repository Pattern, RBAC, CDC Audit
│   ├── techContext.md      # Tech stack details, environment variables, DB
│   ├── progress.md         # Milestones, known technical debt, roadmap
│   └── developerPersona.md # Senior backend engineer conventions & style
├── personas/               # Specialized agent personas and sub-agents
│   ├── code.md             # Primary Senior Backend Developer persona
│   └── architect.md        # Database & Software Architecture specialist
└── plans/                  # Architecture and feature planning documents
    ├── stack-recommendation-from-scratch-saas.md
    ├── 1776174314502-sunny-knight.md
    └── 1778856093470-cosmic-squid.md
```

---

## Conventions & Rules

1. **Virtual Environment**: All execution commands MUST use the project venv located at `venv/bin/<tool>`.
2. **Quality Gates**:
   - `venv/bin/pytest` must pass with 0 failures.
   - `venv/bin/ruff check app/ tests/` and `venv/bin/ruff format app/ tests/` must be clean.
   - `venv/bin/mypy app/ --ignore-missing-imports` must pass without errors.
3. **Single Source of Truth**: The root [`AGENTS.md`](../AGENTS.md) file acts as the primary entry point and points to this directory.

