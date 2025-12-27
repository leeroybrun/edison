---
name: agents-base
project: edison
overlay_type: extend
---

<!-- EXTEND: MandatoryReads -->

### Edison Project Critical Principles (MANDATORY)

**MANDATORY READ**: `guidelines/shared/PRINCIPLES_REFERENCE.md`

The 16 non-negotiable principles govern all Edison development. See PRINCIPLES_REFERENCE.md for the complete list and links to full documentation.

**Agent Focus:**
- **TDD**: Failing test FIRST, then implementation
- **NO MOCKS**: Real behavior only
- **NO HARDCODING**: Config from YAML
- **DRY**: Reuse existing code
- **PATTERNS**: Follow existing Edison patterns exactly
- **ROOT CAUSE**: Fix underlying issues, not symptoms

<!-- /EXTEND -->

<!-- NEW_SECTION: EdisonProjectRules -->

## Edison Project-Specific Rules

When working on the Edison framework itself, you MUST:

### 1. Follow CLI Command Pattern
```python
# src/edison/cli/{domain}/{command}.py
def register_args(parser: argparse.ArgumentParser) -> None:
    ...

def main(args: argparse.Namespace) -> int:
    ...
    return 0
```

### 2. Use Configuration System
```python
from edison.core.config import ConfigManager
config = ConfigManager()
value = config.get("section.key")
```

### 3. Follow Entity Pattern
```python
from edison.core.entity import BaseEntity

@dataclass
class MyEntity(BaseEntity):
    ...
```

### 4. Use State Machines
```python
from edison.core.state import StateValidator
StateValidator.ensure_transition("entity", "from", "to")
```

### 5. Python Best Practices
- Type hints on ALL functions (mypy --strict)
- pytest for testing (NO MOCKS)
- ruff for linting
- Modern Python 3.12+ patterns

<!-- /NEW_SECTION -->
