---
name: claude
project: edison
overlay_type: extend
---

<!-- EXTEND: composed-additions -->

## Edison Project Critical Principles

**MANDATORY READ**: `.edison/guidelines/edison/CRITICAL_PRINCIPLES.md`

When working on Edison, you MUST read and follow the 16 non-negotiable principles in CRITICAL_PRINCIPLES.md.

### Key Principles for Claude Code

- **TDD**: Write failing test FIRST (RED), then implement (GREEN), then refactor (see CRITICAL_PRINCIPLES.md #1)
- **NO MOCKS**: Test real behavior only - use `tmp_path`, SQLite, real libs (see CRITICAL_PRINCIPLES.md #2)
- **NO HARDCODING**: All config from YAML files (see CRITICAL_PRINCIPLES.md #4)
- **DRY**: Reuse existing code, no duplication (see CRITICAL_PRINCIPLES.md #6)
- **ROOT CAUSE**: Fix underlying issues, never workarounds (see CRITICAL_PRINCIPLES.md #13)

### Required Reading

- **`.edison/guidelines/edison/CRITICAL_PRINCIPLES.md`** - Complete documentation
- **`CLAUDE.md`** (project root) - Authoritative source

### Python Requirements

- **mypy --strict** for type checking
- **ruff** for linting
- **pytest** for testing (NO MOCKS)
- Modern Python 3.12+ patterns

---

## Edison Prompt Engineering Rules

**When modifying Edison agents, validators, constitutions, or guidelines**, follow these rules:

{{include-section:.edison/guidelines/edison/PROMPT_ENGINEERING.md#core-principles}}

{{include-section:.edison/guidelines/edison/PROMPT_ENGINEERING.md#anti-patterns}}

{{include-section:.edison/guidelines/edison/PROMPT_ENGINEERING.md#quality-checklist}}

**Full Documentation**: `docs/PROMPT_DEVELOPMENT.md`

---

## Edison Framework Development

This project uses Edison to develop Edison. The Python pack is active, providing:
- Python-specific agent overlays
- Python validator (mypy, ruff, pytest)
- Python guidelines (typing, testing, async)

**Evidence files for Edison:**
- `command-type-check.txt` - mypy output
- `command-lint.txt` - ruff output
- `command-test.txt` - pytest output

<!-- /EXTEND -->
