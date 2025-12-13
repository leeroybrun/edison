---
name: global
pack: python
overlay_type: extend
---

<!-- extend: tech-stack -->

## Python Technology Stack

### Type Checking: mypy

```bash
# Run type check (MANDATORY)
mypy --strict src/ > command-type-check.txt 2>&1
```

**Validation Points:**
- All functions have type annotations
- Return types specified
- No `Any` without justification
- No `# type: ignore` without comment
- Generics used correctly

### Linting: ruff

```bash
# Run linter (MANDATORY)
ruff check src/ tests/ > command-lint.txt 2>&1
```

**Validation Points:**
- All rules pass
- Import order correct
- No unused imports/variables
- Consistent naming

### Testing: pytest

```bash
# Run tests (MANDATORY)
pytest tests/ -v --tb=short > command-test.txt 2>&1
```

**Validation Points:**
- All tests passing
- NO MOCKS (per CLAUDE.md)
- Real files/databases used
- Edge cases covered

### Build

```bash
# Build check (if applicable)
python -m build > command-build.txt 2>&1 || echo "No build configured"
```

<!-- /extend -->

<!-- section: PythonChecks -->

## Python-Specific Validation

### 1. Type Safety (BLOCKING)

**Commands:**
```bash
mypy --strict src/
```

**Must Pass:**
- All function parameters have types
- All return types specified
- No `Any` without `# Reason: ...` comment
- No `# type: ignore` without explanation
- Modern syntax: `list[T]` not `List[T]`
- Modern syntax: `T | None` not `Optional[T]`

**Fail Conditions:**
- Any mypy error
- Unjustified `Any` usage
- Unjustified `# type: ignore`

### 2. Testing (BLOCKING)

**Commands:**
```bash
pytest tests/ -v
```

**Must Pass:**
- 100% test pass rate
- No skipped tests without reason
- No mocks (CRITICAL - per CLAUDE.md)
- Fixtures use real resources (tmp_path, real DBs)

**Fail Conditions:**
- Any failing test
- Mock usage detected (`unittest.mock`, `@patch`)
- Skipped tests without `@pytest.mark.skip(reason="...")`

### 3. Code Quality (BLOCKING)

**Commands:**
```bash
ruff check src/ tests/
ruff format --check src/ tests/
```

**Must Pass:**
- Zero ruff errors
- Consistent formatting
- No commented-out code
- No TODO/FIXME in production code

### 4. Modern Python Patterns

**Check For:**
- `from __future__ import annotations` at top
- dataclasses for data structures
- Protocol for duck typing
- pathlib.Path for file paths
- Context managers for resources
- Enum for constants

**Anti-Patterns to Flag:**
- `os.path` instead of `pathlib`
- `open()` without context manager
- Mutable default arguments
- Global mutable state

### 5. NO HARDCODING

**Check For:**
- Magic numbers without named constants
- Hardcoded URLs, paths, credentials
- Configuration values in code
- Environment-specific values

**Must Have:**
- Config loaded from YAML files
- Secrets from environment variables only

<!-- /section: PythonChecks -->
