# Edison Critical Principles

**MANDATORY READ** for all Orchestrators, Agents, and Validators working on the Edison project.

This document contains the non-negotiable principles that govern all Edison development.

---

## CRITICAL PRINCIPLES (NON-NEGOTIABLE)

### 1. STRICT TDD
Write failing test FIRST (RED), then implement (GREEN), then refactor.

**Workflow:**
1. Write test that describes expected behavior
2. Run test - it MUST fail (RED)
3. Implement minimal code to pass
4. Run test - it MUST pass (GREEN)
5. Refactor code while keeping tests passing
6. Commit with evidence of RED-GREEN order

### 2. NO MOCKS
Test real behavior, real code, real libs - NO MOCKS EVER.

**Instead of mocks:**
- Use `tmp_path` fixture for file system tests
- Use SQLite for database tests
- Use real HTTP clients with test servers
- Use pytest fixtures for setup/teardown

**Forbidden:**
```python
# NEVER DO THIS
from unittest.mock import Mock, patch, MagicMock
@patch("module.function")
def test_with_mock(mock_func): ...
```

### 3. NO LEGACY
Delete old code completely - NO backward compatibility, NO fallbacks.

**When refactoring:**
- Remove old implementation entirely
- Update ALL callers
- Update ALL tests
- No deprecation warnings
- No compatibility shims

### 4. NO HARDCODED VALUES
All config from YAML - NO magic numbers/strings in code.

**Bad:**
```python
TIMEOUT = 30
API_URL = "https://api.example.com"
```

**Good:**
```python
from edison.core.config import ConfigManager
config = ConfigManager()
timeout = config.get("session.timeout")
```

### 5. 100% CONFIGURABLE
Every behavior must be configurable via YAML.

- State machines defined in YAML
- Timeouts in YAML
- Feature flags in YAML
- All paths in YAML

### 6. DRY (Don't Repeat Yourself)
Zero code duplication - extract to shared utilities.

- Common patterns → utility functions
- Repeated logic → shared modules
- Similar structures → base classes

### 7. SOLID Principles

- **S**ingle Responsibility: One reason to change
- **O**pen/Closed: Open for extension, closed for modification
- **L**iskov Substitution: Subtypes substitutable for base types
- **I**nterface Segregation: Small, focused interfaces
- **D**ependency Inversion: Depend on abstractions

### 8. KISS (Keep It Simple, Stupid)
No over-engineering.

- Simplest solution that works
- No premature optimization
- No speculative generalization

### 9. YAGNI (You Aren't Gonna Need It)
Remove speculative features.

- Only implement what's needed now
- Remove unused code
- No "just in case" features

### 10. LONG-TERM MAINTAINABLE
Code must be maintainable for years.

- Clear naming
- Comprehensive type hints
- Self-documenting code
- Minimal comments (code explains itself)

### 11. UN-DUPLICATED & REUSABLE
DON'T REINVENT THE WHEEL.

Before implementing any logic/lib/etc:
1. Search existing codebase
2. Look for similar patterns
3. Check if something can be extended
4. Only create new if truly needed

### 12. STRICT COHERENCE AND UNITY
Code must be coherent and unified.

Before implementing:
1. Study existing patterns
2. Understand current structure
3. Match existing style exactly
4. Ensure consistency across codebase

### 13. ROOT CAUSE FIXES
NEVER apply dirty fixes.

- Don't simplify tests to make them pass
- Don't remove logic to bypass issues
- ALWAYS find and fix the root cause
- Investigate deeply before changing

### 14. REFACTORING ESSENTIALS
When refactoring, update EVERYTHING.

- ALL related code
- ALL callers
- ALL tests (unit, integration, e2e)
- ALL usage sites
- NO legacy fallbacks

### 15. SELF VALIDATION
Before marking task done:

1. Re-analyze from fresh perspective
2. Check all principles followed
3. Verify nothing forgotten
4. Review as if you were a colleague
5. Only then mark complete

### 16. GIT SAFETY
NEVER use destructive git commands.

**Forbidden (unless explicitly requested):**
- `git reset`
- `git checkout` (for reverting)
- `git rebase -i`
- `git push --force`

---

## Testing Guidelines

### Update All Tests
When updating code, ALL related tests must be updated:
- Unit tests
- Integration tests
- E2E tests

### Root Cause Analysis
When a test fails:
1. Analyze the failure deeply
2. Determine if code is wrong OR test is wrong
3. NEVER simplify test just to pass
4. Fix the actual root cause

### Long Test Suites
For long-running test suites:
1. Use long timeout (30min+)
2. Redirect output to file
3. Analyze output thoroughly
4. Fix issues in parallel if multiple

---

## Enforcement

These principles are enforced by:
- **Validators**: Check for violations during review
- **CI/CD**: Automated checks for patterns
- **Code Review**: Human verification

Violations will cause task rejection.