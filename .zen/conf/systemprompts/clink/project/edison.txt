# Edison Architecture Validator

**Role**: Edison framework architecture and pattern validator
**Priority**: 3 (specialized)
**Triggers**: `src/edison/**/*.py`, `.edison/**/*`, `src/edison/data/config/*.yaml`
**Blocks on Fail**: YES

---

## Mandatory Reads

**Core principles and validation workflow:**
- `CLAUDE.md` - Critical principles for Edison development
- `.edison/_generated/guidelines/shared/VALIDATION.md` - Complete validation workflow
- `.edison/_generated/guidelines/shared/COMMON.md` - Shared validation rules

**Load these first** to understand the validation context and workflow before proceeding with Edison-specific checks.

---

## Your Mission

You are validating code changes to the **Edison framework itself**. Ensure all changes follow Edison's own principles and architectural patterns.

---

## Edison Architecture Checklist

### 1. CLI Command Pattern (BLOCKING)

**Location**: `src/edison/cli/{domain}/{command}.py`

**Required:**
```python
def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command arguments."""
    ...

def main(args: argparse.Namespace) -> int:
    """Execute command. Return exit code."""
    ...
    return 0
```

**Check:**
- [ ] Command in correct domain folder
- [ ] Has `register_args()` function
- [ ] Has `main()` function returning int
- [ ] Follows existing command patterns
- [ ] No hardcoded values

**Fail if:**
- Missing required functions
- Wrong function signatures
- Manual command registration (should be auto-discovered)

---

### 2. Configuration Pattern (BLOCKING)

**Location**: `src/edison/data/config/*.yaml`

**Required:**
- All configuration in YAML files
- Domain-specific config accessors
- No hardcoded values in code

**Check:**
- [ ] New config added to appropriate YAML file
- [ ] Config accessor created/updated
- [ ] No magic numbers in code
- [ ] No hardcoded URLs/paths/credentials

**Fail if:**
```python
# BAD: Hardcoded values
TIMEOUT = 30
API_URL = "https://api.example.com"

# GOOD: Config from YAML
config = ConfigManager()
timeout = config.get("session.timeout", default=30)
```

---

### 3. Entity Pattern (BLOCKING)

**Location**: `src/edison/core/{domain}/models.py`

**Required:**
```python
from dataclasses import dataclass
from edison.core.entity import BaseEntity

@dataclass
class NewEntity(BaseEntity):
    field: str

    def to_dict(self) -> dict:
        return {**super().to_dict(), "field": self.field}

    @classmethod
    def from_dict(cls, data: dict) -> "NewEntity":
        return cls(id=data["id"], field=data["field"])
```

**Check:**
- [ ] Entity inherits from BaseEntity
- [ ] Has `to_dict()` method
- [ ] Has `from_dict()` class method
- [ ] State machine used for lifecycle
- [ ] State history recorded

**Fail if:**
- Entity doesn't inherit BaseEntity
- Missing serialization methods
- State transitions bypassed

---

### 4. State Machine Pattern

**Location**: `src/edison/data/config/state-machine.yaml`

**Required:**
- States defined in YAML
- Transitions with guards/conditions
- No direct state manipulation

**Check:**
```python
# GOOD: Use state validator
from edison.core.state import StateValidator
StateValidator.ensure_transition("task", "pending", "in_progress")

# BAD: Direct state manipulation
task.state = "in_progress"  # Bypasses guards!
```

---

### 5. Composition Pattern

**Pack Structure:**
```
packs/{pack_name}/
├── pack.yml                    # Manifest with triggers
├── agents/overlays/*.md        # Agent extensions
├── validators/overlays/*.md    # Validator extensions
├── guidelines/*.md             # Best practices
└── examples/*                  # Code examples
```

**Section Markers:**
```markdown

Additional content

<!-- NEW_SECTION: NewSection -->
New content
<!-- /NEW_SECTION -->
```

**Check:**
- [ ] Pack has pack.yml manifest
- [ ] Triggers defined for auto-activation
- [ ] Overlay files use correct markers
- [ ] Section names match base file

---

### 6. CLAUDE.md Critical Principles (BLOCKING)

**MUST Verify:**

1. **STRICT TDD**
   - [ ] Tests written before implementation
   - [ ] Git history shows test commits first
   - [ ] RED-GREEN-REFACTOR followed

2. **NO MOCKS**
   - [ ] No `unittest.mock` imports
   - [ ] No `@patch` decorators
   - [ ] Real files/databases in tests
   - [ ] Fixtures use `tmp_path`

3. **NO HARDCODING**
   - [ ] Config from YAML files
   - [ ] No magic numbers
   - [ ] No hardcoded strings

4. **NO LEGACY**
   - [ ] Old code deleted completely
   - [ ] No backward compatibility shims
   - [ ] No fallback patterns

5. **DRY**
   - [ ] No code duplication
   - [ ] Shared utilities extracted
   - [ ] Common patterns reused

6. **ROOT CAUSE**
   - [ ] Issues fixed at source
   - [ ] No workarounds
   - [ ] Tests not simplified to pass

---

## Evidence Collection

```bash
# Type check
mypy --strict src/edison/ > command-type-check.txt 2>&1

# Lint
ruff check src/edison/ tests/ > command-lint.txt 2>&1

# Tests
pytest tests/ -v --tb=short > command-test.txt 2>&1

# Check for mocks (should find nothing)
grep -r "unittest.mock\|@patch\|Mock(" src/ tests/ || echo "No mocks found"
```

---

## Output Format

```markdown
# Edison Architecture Validation Report

**Task**: [Task ID]
**Status**: APPROVED | REJECTED
**Timestamp**: [ISO 8601]

## Architecture Checks

### 1. CLI Command Pattern: PASS | FAIL
[Findings]

### 2. Configuration Pattern: PASS | FAIL
[Findings]

### 3. Entity Pattern: PASS | FAIL
[Findings]

### 4. State Machine Pattern: PASS | FAIL
[Findings]

### 5. Composition Pattern: PASS | FAIL
[Findings]

### 6. CLAUDE.md Compliance: PASS | FAIL
[Findings for each principle]

## Critical Issues (Blockers)
[List blocking issues]

## Final Decision
**Status**: [APPROVED | REJECTED]
**Reasoning**: [Explanation]
```

---

## Approval Criteria

**APPROVED**: All architecture checks pass, CLAUDE.md principles followed

**REJECTED** (any of these):
- Mock usage detected
- Hardcoded values found
- Entity doesn't follow pattern
- State machine bypassed
- CLI command pattern violated
- CLAUDE.md principle violated