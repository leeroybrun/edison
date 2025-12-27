---
name: orchestrator-base
project: edison
overlay_type: extend
---

<!-- EXTEND: MandatoryReads -->

### Edison Project Critical Principles (MANDATORY)

**MANDATORY READ**: `guidelines/shared/PRINCIPLES_REFERENCE.md`

The 16 non-negotiable principles govern all Edison development. See PRINCIPLES_REFERENCE.md for the complete list and links to full documentation.

**Orchestrator Enforcement:**
- **TDD**: Ensure agents write tests FIRST
- **NO MOCKS**: Reject any mock/patch usage
- **NO HARDCODING**: Verify config in YAML only
- **NO LEGACY**: Reject backward-compat code
- **ROOT CAUSE**: Ensure fixes address root issues
- **QUALITY GATES**: mypy --strict, ruff, pytest must pass

<!-- /EXTEND -->

<!-- NEW_SECTION: EdisonOrchestrationRules -->

## Edison Project Orchestration Rules

When orchestrating work on Edison:

### 1. Delegation
- Delegate Python tasks to agents with `python` pack active
- Ensure agents understand Edison architecture patterns
- Verify agents read CRITICAL_PRINCIPLES before work

### 2. Validation Requirements
- ALL changes must pass mypy --strict
- ALL changes must pass ruff check
- ALL changes must pass pytest
- NO MOCKS in any test code
- NO hardcoded values in any code

### 3. Quality Gates
Before marking any task complete, verify:
- [ ] TDD followed (test commits before implementation)
- [ ] No mock usage
- [ ] No hardcoded values
- [ ] All tests passing
- [ ] Type check passing
- [ ] Lint passing

### 4. Evidence Collection
Collect these evidence files:
- `command-type-check.txt` - mypy output
- `command-lint.txt` - ruff output
- `command-test.txt` - pytest output

<!-- /NEW_SECTION -->
