# AUDIT 1: DRY & Duplication - Quick Reference Card

**For Developers:** Use this as a quick lookup when fixing duplication issues

---

## CANONICAL LOCATIONS (Where to Find)

### File I/O Operations
```python
# ✅ USE THIS:
from edison.core.utils import json_io
data = json_io.read_json(path)
json_io.write_json_atomic(path, data)

# ❌ NOT THIS:
import json
with open(path) as f:
    data = json.load(f)
```

### YAML Operations
```python
# ✅ USE THIS:
from edison.core.file_io.utils import read_yaml_safe
data = read_yaml_safe(path, default={})

# ❌ NOT THIS:
import yaml
with open(path) as f:
    data = yaml.safe_load(f)
```

### Repository Root
```python
# ✅ USE THIS:
from edison.core.utils.git import get_repo_root
root = get_repo_root()

# ❌ NOT THIS:
def _repo_root():
    # custom implementation
```

### Timestamps
```python
# ✅ USE THIS:
from edison.core.utils.time import utc_timestamp, utc_now
timestamp = utc_timestamp()  # ISO 8601 string
now = utc_now()  # datetime object

# ❌ NOT THIS:
from datetime import datetime, timezone
timestamp = datetime.now(timezone.utc).isoformat()
```

### Directory Creation
```python
# ✅ USE THIS (after consolidation):
from edison.core.file_io.utils import ensure_dir
ensure_dir(path)

# ⚠️ CURRENTLY ACCEPTABLE (until consolidated):
path.mkdir(parents=True, exist_ok=True)

# ❌ NOT THIS:
if not path.exists():
    path.mkdir(parents=True)
```

### File Locking & Atomic Writes
```python
# ✅ USE THIS:
from edison.core.task.locking import write_text_locked
write_text_locked(path, content)

# ❌ NOT THIS:
with open(path, 'w') as f:
    f.write(content)
```

### QA Evidence Operations
```python
# ✅ USE THIS:
from edison.core.qa import evidence
blockers = evidence.missing_evidence_blockers(task_id)
validators = evidence.read_validator_jsons(task_id)
impl = evidence.load_impl_followups(task_id)
bundle = evidence.load_bundle_followups(task_id)

# ❌ NOT THIS:
from edison.core.session.next.actions import missing_evidence_blockers
# (These are needless wrappers - use qa.evidence directly)
```

### QA Root Path
```python
# ⚠️ TO BE CONSOLIDATED:
# Currently in qa/store.py and task/store.py
# Will move to paths/management.py

# Future canonical:
from edison.core.paths.management import get_qa_root
root = get_qa_root(project_root=None)
```

### Latest Round Directory
```python
# ✅ USE THIS:
from edison.core.qa.evidence import _latest_round_dir
round_dir = _latest_round_dir(task_id)

# ❌ NOT THIS:
# Don't implement your own in task/ or session/ modules
```

---

## DUPLICATION DETECTION

### How to Check if Function Exists
```bash
# Search for existing implementations
grep -rn "^def function_name" src/edison/core --include="*.py"

# Check for similar utility functions
grep -rn "def .*json" src/edison/core/utils --include="*.py"
grep -rn "def .*yaml" src/edison/core/file_io --include="*.py"
```

### Common Duplicate Patterns to Avoid
1. **Private helper functions** (`_cfg`, `_repo_root`, `_now_iso`)
   - Check if canonical version exists before creating

2. **I/O operations** (read/write json, yaml, text)
   - Always use utilities, never implement inline

3. **Path operations** (mkdir, exists, read_text)
   - Use file_io utilities

4. **Time operations** (timestamps, formatting)
   - Use utils.time module

---

## MODULE-SPECIFIC PATTERNS

### Config Access Pattern
```python
# Each module has a Config class that wraps ConfigManager:
from edison.core.qa.config import QAConfig
from edison.core.task.config import TaskConfig
from edison.core.session.config import SessionConfig

# These are GOOD - thin wrappers providing domain-specific interfaces
```

### Manager Pattern
```python
# Manager classes coordinate operations for a domain:
from edison.core.config import ConfigManager
from edison.core.task.manager import TaskManager
from edison.core.session.manager import SessionManager
from edison.core.qa.evidence import EvidenceManager

# Managers should have consistent lifecycle: create, read, update, delete
```

### Transaction Pattern
```python
# After rename (to avoid collision):
from edison.core.qa.transaction import QAValidationTransaction
from edison.core.session.transaction import SessionValidationTransaction

# Use appropriate transaction for your context
```

---

## NAMING CONVENTIONS

### Functions to Rename
| Current Name | New Name | Location |
|--------------|----------|----------|
| `_cfg()` | `_time_cfg()` | utils/time.py |
| `_cfg()` | `_json_cfg()` | utils/json_io.py |
| `_cfg()` | `_cli_output_cfg()` | utils/cli_output.py |
| `build_default_state_machine()` | `build_task_state_machine()` | task/state.py |
| `build_default_state_machine()` | `build_session_state_machine()` | session/state.py |
| `ValidationTransaction` | `QAValidationTransaction` | qa/transaction.py |
| `ValidationTransaction` | `SessionValidationTransaction` | session/transaction.py |

---

## PR CHECKLIST

Before submitting a PR, verify:

- [ ] No new duplicate function names without justification
- [ ] All JSON operations use `utils.json_io`
- [ ] All YAML operations use `file_io.utils.read_yaml_safe()`
- [ ] All repo root detection uses `utils.git.get_repo_root()`
- [ ] All timestamps use `utils.time.utc_timestamp()`
- [ ] No direct `json.load()`, `json.dump()`, or `yaml.safe_load()` calls
- [ ] No custom implementations of existing utilities

---

## CONSOLIDATION STATUS

| Item | Status | Notes |
|------|--------|-------|
| JSON I/O | ⏳ Pending | 36 instances to fix |
| YAML loading | ⏳ Pending | 18 instances to fix |
| Repo root | ⏳ Pending | 7 implementations to remove |
| Timestamps | ⏳ Pending | 6 implementations to remove |
| mkdir pattern | ⏳ Pending | 85 instances to consolidate |
| QA wrappers | ⏳ Pending | 4 wrappers to remove |
| _latest_round_dir | ⏳ Pending | 2 implementations to remove |
| ValidationTransaction | ⏳ Pending | Rename for clarity |
| _cfg functions | ⏳ Pending | Rename 3 functions |

Legend: ✅ Done | ⏳ Pending | 🚧 In Progress

---

## WHEN IN DOUBT

1. **Search first:** `grep -rn "def function_name" src/edison/core`
2. **Check utils:** Look in `utils/` and `file_io/` modules
3. **Ask:** If unsure, ask in PR or check CLAUDE.md
4. **Document:** If you find duplication, report it

---

## USEFUL COMMANDS

```bash
# Find all implementations of a function
grep -rn "^def function_name" src/edison/core --include="*.py"

# Find all uses of a function
grep -rn "function_name(" src/edison/core --include="*.py"

# Count duplicate function names
grep -rh "^def " src/edison --include="*.py" | \
  sed 's/def \([a-z_]*\).*/\1/' | sort | uniq -d | wc -l

# Find direct json/yaml usage
grep -rn "json.load\|json.dump" src/edison/core --include="*.py"
grep -rn "yaml.safe_load" src/edison/core --include="*.py"
```

---

## RELATED DOCUMENTATION

- **Full Analysis:** `/audit/AUDIT_1_DRY_DUPLICATION_ANALYSIS.md`
- **Action Checklist:** `/audit/AUDIT_1_CHECKLIST.md`
- **Executive Summary:** `/audit/AUDIT_1_SUMMARY.md`
- **Project Guidelines:** `/CLAUDE.md`

---

**Last Updated:** 2025-11-26
**Audit Version:** 1.0
