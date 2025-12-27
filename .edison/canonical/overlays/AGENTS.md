---
name: AGENTS
project: edison
overlay_type: extend
---

<!-- EXTEND: composed-additions -->

## Edison Project Critical Principles

**MANDATORY READ**: `guidelines/shared/PRINCIPLES_REFERENCE.md`

The 16 non-negotiable principles govern all Edison development. See PRINCIPLES_REFERENCE.md for the complete list and authoritative source references.

### Key Principles for All Roles

- **TDD**: Tests first, always
- **NO MOCKS**: Real behavior only
- **NO HARDCODING**: Config from YAML
- **NO LEGACY**: Delete old code completely
- **ROOT CAUSE**: Fix underlying issues, not symptoms
- **SELF VALIDATION**: Re-analyze before marking done

### Mandatory Reads for Edison Development

**Before ANY work on Edison**, read:

1. **`guidelines/shared/PRINCIPLES_REFERENCE.md`** - Principles summary and links
2. **`CLAUDE.md`** (project root) - Authoritative source of principles
3. **`.edison/guidelines/edison/ARCHITECTURE.md`** - Edison architecture patterns
4. **`.edison/guidelines/edison/CONTRIBUTING.md`** - How to contribute

### Python Requirements

Edison is a Python 3.12+ project requiring:
- **Type hints**: `mypy --strict` must pass
- **Testing**: pytest with NO MOCKS (use `tmp_path`, SQLite, real behavior)
- **Linting**: ruff check must pass

---

## Edison Prompt Engineering Rules

**When modifying Edison agents, validators, constitutions, or guidelines**, follow these rules:

{{include-section:.edison/guidelines/edison/PROMPT_ENGINEERING.md#core-principles}}

{{include-section:.edison/guidelines/edison/PROMPT_ENGINEERING.md#anti-patterns}}

{{include-section:.edison/guidelines/edison/PROMPT_ENGINEERING.md#quality-checklist}}

**Full Documentation**: `docs/PROMPT_DEVELOPMENT.md`

---

## Edison Self-Development

This project uses Edison to develop Edison itself. Active configurations:

**Packs**: `python` (auto-activated by `**/*.py` files)

**Validators**:
- Python validator (type checking, linting, testing)
- Edison architecture validator (CLI patterns, config system, entities)

**Evidence Collection**:
```bash
mypy --strict src/edison/ > command-type-check.txt
ruff check src/edison/ tests/ > command-lint.txt
pytest tests/ -v --tb=short > command-test.txt
```

<!-- /EXTEND -->
