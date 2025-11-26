# Edison Framework - Audit 1: Deep DRY & Duplication Analysis

## 🎯 AUDIT FOCUS

This audit targets violations of:
- **Rule #6: DRY** - Zero code duplication
- **Rule #11: UN-DUPLICATED & REUSABLE** - Don't reinvent the wheel
- **Rule #12: STRICT COHERENCE** - Consistent patterns throughout

---

## 📋 THE 13 NON-NEGOTIABLE RULES (Reference)

```
1. STRICT TDD: Write failing test FIRST (RED), then implement (GREEN), then refactor
2. NO MOCKS: Test real behavior, real code, real libs - NO MOCKS EVER
3. NO LEGACY: Delete old code completely - NO backward compatibility, NO fallbacks
4. NO HARDCODED VALUES: All config from YAML - NO magic numbers/strings in code
5. 100% CONFIGURABLE: Every behavior must be configurable via YAML
6. DRY: Zero code duplication - extract to shared utilities
7. SOLID: Single Responsibility, Open/Closed, Liskov, Interface Seg, Dependency Inv
8. KISS: Keep It Simple, Stupid - no over-engineering
9. YAGNI: You Aren't Gonna Need It - remove speculative features
10. LONG-TERM MAINTAINABLE
11. UN-DUPLICATED & REUSABLE: DON'T REINVENT THE WHEEL - reuse/extend existing
12. STRICT COHERENCE: Consistent patterns throughout entire codebase
13. ROOT CAUSE FIXES: NEVER apply dirty fixes - ALWAYS find and fix root causes
```

---

## 🔬 PHASE 1: FUNCTION-LEVEL DUPLICATION DETECTION

### 1.1 Find Functions with Similar Names

```bash
cd /Users/leeroy/Documents/Development/edison

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  FUNCTION NAME SIMILARITY ANALYSIS                                           ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Functions that appear in multiple files ==="
# Extract all function names and find duplicates
grep -rhn "^def \|^    def " src/edison --include="*.py" | \
    sed 's/.*def \([a-z_]*\).*/\1/' | \
    sort | uniq -c | sort -rn | \
    awk '$1 > 1 {print $1 " occurrences: " $2}' | head -30

echo ""
echo "=== Detailed locations for top duplicates ==="
# For each duplicate function name, show where it appears
for func in $(grep -rhn "^def \|^    def " src/edison --include="*.py" | \
    sed 's/.*def \([a-z_]*\).*/\1/' | sort | uniq -c | sort -rn | \
    awk '$1 > 2 {print $2}' | head -10); do
    echo ""
    echo "--- Function: $func ---"
    grep -rn "def $func\|def ${func}(" src/edison --include="*.py" | head -10
done
```

### 1.2 Find Classes with Similar Names

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  CLASS NAME SIMILARITY ANALYSIS                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Classes that appear in multiple files ==="
grep -rhn "^class " src/edison --include="*.py" | \
    sed 's/.*class \([A-Za-z_]*\).*/\1/' | \
    sort | uniq -c | sort -rn | \
    awk '$1 > 1 {print $1 " occurrences: " $2}' | head -20

echo ""
echo "=== Detailed class locations ==="
for cls in $(grep -rhn "^class " src/edison --include="*.py" | \
    sed 's/.*class \([A-Za-z_]*\).*/\1/' | sort | uniq -c | sort -rn | \
    awk '$1 > 1 {print $2}' | head -10); do
    echo ""
    echo "--- Class: $cls ---"
    grep -rn "^class $cls" src/edison --include="*.py"
done
```

### 1.3 Find Similar Method Signatures

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  METHOD SIGNATURE PATTERN ANALYSIS                                           ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Common method patterns (potential duplication) ==="

# Look for common CRUD patterns
echo "--- save/load patterns ---"
grep -rn "def save\|def load\|def _save\|def _load" src/edison --include="*.py" | head -20

echo ""
echo "--- get/set patterns ---"
grep -rn "def get_\|def set_\|def _get_\|def _set_" src/edison --include="*.py" | wc -l
echo "files with get/set patterns"

echo ""
echo "--- validate patterns ---"
grep -rn "def validate\|def _validate\|def is_valid" src/edison --include="*.py" | head -20

echo ""
echo "--- create/update/delete patterns ---"
grep -rn "def create\|def update\|def delete" src/edison --include="*.py" | head -20

echo ""
echo "--- read/write file patterns ---"
grep -rn "def read_\|def write_\|def _read_\|def _write_" src/edison --include="*.py" | head -20
```

---

## 🔬 PHASE 2: CODE BLOCK SIMILARITY DETECTION

### 2.1 YAML Loading Patterns

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  YAML LOADING PATTERN ANALYSIS                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== All YAML loading code ==="
grep -rn "yaml.safe_load\|yaml.load\|yaml.dump\|yaml.safe_dump" src/edison --include="*.py"

echo ""
echo "=== Files with YAML operations ==="
grep -rl "yaml.safe_load\|yaml.load" src/edison --include="*.py" | wc -l
echo "files load YAML"

echo ""
echo "=== Check if centralized (should use file_io/utils.py) ==="
echo "Expected: All YAML ops should go through file_io/utils.py"
grep -rn "yaml\." src/edison --include="*.py" | grep -v "file_io/utils.py\|import yaml" | head -20
```

### 2.2 JSON Loading Patterns

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  JSON LOADING PATTERN ANALYSIS                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== All JSON loading code ==="
grep -rn "json.load\|json.dump\|json.loads\|json.dumps" src/edison --include="*.py" | head -30

echo ""
echo "=== Check if centralized (should use utils/json_io.py) ==="
echo "Expected: All JSON ops should go through utils/json_io.py"
grep -rn "json\." src/edison --include="*.py" | grep -v "json_io.py\|import json\|schema.json" | head -20
```

### 2.3 File Reading Patterns

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  FILE READING PATTERN ANALYSIS                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Direct file open() calls (potential duplication) ==="
grep -rn "with open(\|open(" src/edison --include="*.py" | grep -v "file_io\|test_" | head -30

echo ""
echo "=== Path.read_text() / Path.write_text() usage ==="
grep -rn "\.read_text()\|\.write_text(" src/edison --include="*.py" | head -20

echo ""
echo "=== These should use centralized file_io utilities ==="
```

### 2.4 Error Handling Patterns

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  ERROR HANDLING PATTERN ANALYSIS                                             ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Custom exception classes ==="
grep -rn "class.*Exception\|class.*Error" src/edison --include="*.py"

echo ""
echo "=== Are exceptions centralized in exceptions.py? ==="
echo "Expected: All custom exceptions in src/edison/core/exceptions.py"
grep -rn "class.*Exception\|class.*Error" src/edison --include="*.py" | grep -v "exceptions.py\|import.*Exception"
```

---

## 🔬 PHASE 3: CROSS-MODULE PATTERN ANALYSIS

### 3.1 Store Pattern Deep Comparison

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  STORE PATTERN DEEP COMPARISON                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== All store.py files ==="
find src/edison -name "store.py" -type f

echo ""
echo "=== session/store.py full content ==="
cat src/edison/core/session/store.py

echo ""
echo "=== task/store.py full content ==="
cat src/edison/core/task/store.py

echo ""
echo "=== qa/store.py full content ==="
cat src/edison/core/qa/store.py

echo ""
echo "=== ANALYSIS: Look for ==="
echo "1. Similar method signatures"
echo "2. Similar file I/O patterns"
echo "3. Similar data structures"
echo "4. Code that could be extracted to a base class"
```

### 3.2 Manager Pattern Deep Comparison

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  MANAGER PATTERN DEEP COMPARISON                                             ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== All manager.py files ==="
find src/edison -name "manager.py" -type f

echo ""
echo "=== session/manager.py methods ==="
grep -n "^class \|^    def " src/edison/core/session/manager.py

echo ""
echo "=== task/manager.py methods ==="
grep -n "^class \|^    def " src/edison/core/task/manager.py

echo ""
echo "=== Compare method signatures ==="
echo "session/manager.py:"
grep "def " src/edison/core/session/manager.py | sed 's/.*def /  /' | head -20
echo ""
echo "task/manager.py:"
grep "def " src/edison/core/task/manager.py | sed 's/.*def /  /' | head -20
```

### 3.3 Config Pattern Deep Comparison

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  CONFIG PATTERN DEEP COMPARISON                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== All config.py files ==="
find src/edison -name "config.py" -type f

for f in $(find src/edison/core -name "config.py" -type f); do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "=== $f ==="
    grep -n "^class \|^def \|^    def " "$f" | head -20
done

echo ""
echo "=== Do they share YAML loading logic? ==="
for f in $(find src/edison/core -name "config.py" -type f); do
    echo "--- $f ---"
    grep -n "yaml\|load\|get_" "$f" | head -5
done
```

### 3.4 Validation Pattern Deep Comparison

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  VALIDATION PATTERN DEEP COMPARISON                                          ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== All validation.py files ==="
find src/edison -name "validation.py" -type f

for f in $(find src/edison/core -name "validation.py" -type f); do
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "=== $f ==="
    grep -n "^class \|^def \|^    def " "$f" | head -15
done
```

---

## 🔬 PHASE 4: IMPORT PATTERN ANALYSIS

### 4.1 Identify Utility Functions Used Everywhere

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  COMMON IMPORT PATTERN ANALYSIS                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Most commonly imported modules (internal) ==="
grep -rh "^from edison\|^import edison" src/edison --include="*.py" | \
    sed 's/from \(edison[^ ]*\).*/\1/' | \
    sed 's/import \(edison[^ ]*\).*/\1/' | \
    sort | uniq -c | sort -rn | head -20

echo ""
echo "=== Most commonly imported functions ==="
grep -rh "from edison.* import" src/edison --include="*.py" | \
    sed 's/.*import //' | tr ',' '\n' | \
    sed 's/^ *//' | sort | uniq -c | sort -rn | head -30

echo ""
echo "=== Are utilities properly centralized? ==="
echo "Check: Functions imported in 5+ places should be in utils/"
```

### 4.2 Check for Reimplemented Standard Patterns

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  REINVENTED WHEEL DETECTION                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Path manipulation (should use pathlib) ==="
grep -rn "os.path\." src/edison --include="*.py" | head -20

echo ""
echo "=== Subprocess calls (should use utils/subprocess.py) ==="
grep -rn "subprocess\." src/edison --include="*.py" | grep -v "utils/subprocess.py" | head -20

echo ""
echo "=== Time operations (should use utils/time.py) ==="
grep -rn "datetime\.\|time\.\|timedelta" src/edison --include="*.py" | grep -v "utils/time.py\|import" | head -20

echo ""
echo "=== Git operations (should use utils/git.py or core/git/) ==="
grep -rn "git \|\.git\|GitPython" src/edison --include="*.py" | grep -v "utils/git.py\|core/git/" | head -20
```

---

## 🔬 PHASE 5: STRING/CONSTANT DUPLICATION

### 5.1 Find Duplicated String Literals

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  STRING LITERAL DUPLICATION ANALYSIS                                         ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Repeated string literals (potential constants) ==="
grep -roh '"[^"]\{10,\}"' src/edison --include="*.py" | \
    sort | uniq -c | sort -rn | \
    awk '$1 > 2 {print}' | head -30

echo ""
echo "=== Repeated error messages ==="
grep -rh "raise.*\"" src/edison --include="*.py" | \
    sed 's/.*raise[^"]*"\([^"]*\)".*/\1/' | \
    sort | uniq -c | sort -rn | \
    awk '$1 > 1 {print}' | head -20
```

### 5.2 Find Duplicated Path Patterns

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  PATH PATTERN DUPLICATION ANALYSIS                                           ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Hardcoded paths (should be in paths/ module) ==="
grep -rn '"/\|Path("' src/edison --include="*.py" | grep -v "test_\|paths/" | head -30

echo ""
echo "=== .edison references (should use centralized path resolution) ==="
grep -rn "\.edison\|edison\.yaml\|edison\.yml" src/edison --include="*.py" | head -20
```

---

## 📊 CREATE ANALYSIS SUMMARY

After running all phases, document findings:

```markdown
# Audit 1: DRY & Duplication Analysis Summary

## Function Duplication
| Function Name | Occurrences | Locations | Action |
|---------------|-------------|-----------|--------|
| [name] | [count] | [files] | CONSOLIDATE/KEEP |

## Class Duplication  
| Class Name | Occurrences | Locations | Action |
|------------|-------------|-----------|--------|
| [name] | [count] | [files] | CONSOLIDATE/KEEP |

## Pattern Duplication (store/manager/config/validation)
| Pattern | Files | Shared Logic | Action |
|---------|-------|--------------|--------|
| store.py | 3 | [describe] | EXTRACT BASE CLASS / OK |
| manager.py | 2 | [describe] | EXTRACT BASE CLASS / OK |
| config.py | 4 | [describe] | EXTRACT BASE CLASS / OK |
| validation.py | 2 | [describe] | EXTRACT BASE CLASS / OK |

## Utility Centralization Issues
| Utility Type | Should Be In | Found In | Action |
|--------------|--------------|----------|--------|
| YAML loading | file_io/utils.py | [locations] | CENTRALIZE |
| JSON loading | utils/json_io.py | [locations] | CENTRALIZE |
| File I/O | file_io/ | [locations] | CENTRALIZE |
| Subprocess | utils/subprocess.py | [locations] | CENTRALIZE |

## String/Constant Duplication
| String/Constant | Occurrences | Action |
|-----------------|-------------|--------|
| [value] | [count] | EXTRACT TO CONSTANTS |

## Verdict
- Total DRY violations found: [count]
- Critical (must fix): [list]
- Medium (should fix): [list]
- Low (nice to have): [list]
```

---

## 🔨 REMEDIATION PATTERNS

### If Store/Manager/Config Patterns Are Duplicated:

```python
# Create base class in utils/ or appropriate location
# Example: src/edison/core/utils/base_store.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar, Generic, Optional

T = TypeVar('T')

class BaseYAMLStore(ABC, Generic[T]):
    """Base class for YAML-backed stores."""
    
    def __init__(self, store_path: Path):
        self.store_path = store_path
    
    def _load_yaml(self) -> dict:
        from edison.core.file_io.utils import read_yaml_safe
        return read_yaml_safe(self.store_path)
    
    def _save_yaml(self, data: dict) -> None:
        from edison.core.file_io.utils import write_yaml_safe
        write_yaml_safe(self.store_path, data)
    
    @abstractmethod
    def save(self, item: T) -> None:
        """Save item to store."""
        pass
    
    @abstractmethod
    def load(self) -> Optional[T]:
        """Load item from store."""
        pass
```

### If Functions Are Duplicated:

```python
# Move to appropriate utils module
# Update all imports to use the centralized version
# Delete duplicates
```

---

## ✅ SUCCESS CRITERIA

- [ ] No function appears in 3+ files with similar logic
- [ ] No class appears in 2+ files with similar logic
- [ ] All YAML operations use file_io/utils.py
- [ ] All JSON operations use utils/json_io.py
- [ ] All file operations use file_io/ utilities
- [ ] All subprocess calls use utils/subprocess.py
- [ ] No hardcoded paths outside of paths/ module
- [ ] String constants are extracted to appropriate modules

---

## START HERE

```bash
cd /Users/leeroy/Documents/Development/edison

# Run Phase 1 first - function/class duplication
# This is the highest-impact analysis

# Then proceed through other phases systematically
# Document all findings before making any changes
```

**ANALYZE FIRST. FIX AFTER UNDERSTANDING THE FULL SCOPE.**
