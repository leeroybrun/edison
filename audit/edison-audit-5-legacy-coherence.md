# Edison Framework - Audit 5: Legacy Code & Coherence Analysis

## 🎯 AUDIT FOCUS

This audit targets violations of:
- **Rule #3: NO LEGACY** - Delete old code completely, NO backward compatibility
- **Rule #12: STRICT COHERENCE** - Consistent patterns throughout entire codebase

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

## 🔬 PHASE 1: LEGACY CODE DETECTION (Rule #3)

### 1.1 Find Legacy Markers

```bash
cd /Users/leeroy/Documents/Development/edison

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  LEGACY MARKER DETECTION                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== 'legacy' in filenames ==="
find src tests -name "*legacy*" -type f

echo ""
echo "=== 'legacy' in code ==="
grep -rn "legacy\|Legacy\|LEGACY" src/ --include="*.py" | head -30

echo ""
echo "=== 'deprecated' markers ==="
grep -rn "deprecated\|Deprecated\|DEPRECATED\|@deprecated" src/ --include="*.py"

echo ""
echo "=== 'old' / 'old_' prefixes ==="
grep -rn "old_\|_old\|OLD_" src/ --include="*.py" | head -20

echo ""
echo "=== 'compat' / 'compatibility' markers ==="
grep -rn "compat\|compatibility\|backward" src/ --include="*.py"
```

### 1.2 Find Backward Compatibility Code

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  BACKWARD COMPATIBILITY CODE DETECTION                                       ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Version checks ==="
grep -rn "version\|Version\|__version__" src/ --include="*.py" | grep -E "if|>|<|==" | head -20

echo ""
echo "=== Fallback patterns ==="
grep -rn "fallback\|fall_back\|FALLBACK" src/ --include="*.py"

echo ""
echo "=== try/except ImportError (compatibility shims) ==="
grep -rn "except ImportError\|except ModuleNotFoundError" src/ --include="*.py"

echo ""
echo "=== Alternative import patterns ==="
grep -rn "try:.*import\|except.*import" src/ --include="*.py" -A 2 | head -30
```

### 1.3 Find Shim/Wrapper Modules

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  SHIM/WRAPPER MODULE DETECTION                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Files that only re-export ==="
for f in $(find src/edison -name "*.py" -type f ! -name "__init__.py"); do
    lines=$(grep -v "^#\|^$\|^from \|^import " "$f" | wc -l)
    if [ "$lines" -lt 5 ]; then
        echo "⚠️  Mostly imports: $f"
        cat "$f" | head -10
        echo "---"
    fi
done | head -60

echo ""
echo "=== __init__.py re-exports (check for legacy shims) ==="
for f in $(find src/edison -name "__init__.py" -type f); do
    exports=$(grep -c "from .* import\|__all__" "$f" 2>/dev/null || echo 0)
    if [ "$exports" -gt 10 ]; then
        echo "⚠️  Many re-exports ($exports): $f"
    fi
done
```

### 1.4 Find TODO/FIXME Legacy Comments

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  LEGACY TODO/FIXME COMMENTS                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Legacy-related TODO comments ==="
grep -rn "TODO.*legacy\|FIXME.*legacy\|TODO.*remove\|TODO.*delete\|TODO.*deprecat" src/ --include="*.py"

echo ""
echo "=== 'temporary' / 'temp' markers ==="
grep -rn "temporary\|TEMPORARY\|temp_\|_temp\|TEMP_" src/ --include="*.py" | grep -v "template"

echo ""
echo "=== 'hack' / 'workaround' markers ==="
grep -rn "HACK\|hack\|workaround\|WORKAROUND" src/ --include="*.py"
```

---

## 🔬 PHASE 2: DEAD CODE DETECTION (Rule #3)

### 2.1 Find Unreferenced Files

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  UNREFERENCED FILE DETECTION                                                 ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Core modules with zero imports ==="
for f in $(find src/edison/core -name "*.py" -type f ! -name "__init__.py"); do
    module=$(basename "$f" .py)
    # Search for imports of this module
    imports=$(grep -rn "from.*$module import\|import.*$module\|from.*${module}\." src/ tests/ --include="*.py" 2>/dev/null | grep -v "^$f:" | grep -v __pycache__ | wc -l)
    if [ "$imports" -eq 0 ]; then
        echo "❌ DEAD CODE: $f (0 imports)"
    fi
done

echo ""
echo "=== CLI modules with zero usage ==="
for f in $(find src/edison/cli -name "*.py" -type f ! -name "__init__.py"); do
    module=$(basename "$f" .py)
    imports=$(grep -rn "$module" src/ tests/ --include="*.py" 2>/dev/null | grep -v "^$f:" | grep -v __pycache__ | wc -l)
    if [ "$imports" -eq 0 ]; then
        echo "⚠️  No internal imports (may be CLI entry point): $f"
    fi
done
```

### 2.2 Find Unreferenced Functions

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  UNREFERENCED FUNCTION DETECTION                                             ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Public functions - check if called ==="
echo "Analyzing public functions (this may take a moment)..."

# Get all public function definitions
grep -rh "^def [a-z]" src/edison/core --include="*.py" | \
    sed 's/def \([a-z_]*\).*/\1/' | \
    sort -u | while read func; do
    # Skip common names that are likely used
    if [[ "$func" == "__"* ]] || [[ "$func" == "main" ]]; then
        continue
    fi
    # Count usages (excluding definition)
    usages=$(grep -rn "$func(" src/ tests/ --include="*.py" 2>/dev/null | grep -v "^def $func\|def $func(" | wc -l)
    if [ "$usages" -eq 0 ]; then
        echo "⚠️  No usages found: $func"
    fi
done | head -30
```

### 2.3 Find Unreferenced Classes

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  UNREFERENCED CLASS DETECTION                                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Classes - check if instantiated or inherited ==="
grep -rh "^class [A-Z]" src/edison/core --include="*.py" | \
    sed 's/class \([A-Za-z_]*\).*/\1/' | \
    sort -u | while read cls; do
    # Count usages (instantiation or inheritance)
    usages=$(grep -rn "$cls(\|: $cls\|($cls)" src/ tests/ --include="*.py" 2>/dev/null | grep -v "^class $cls" | wc -l)
    if [ "$usages" -eq 0 ]; then
        echo "⚠️  No usages found: class $cls"
    fi
done | head -30
```

---

## 🔬 PHASE 3: PATTERN COHERENCE ANALYSIS (Rule #12)

### 3.1 Naming Convention Consistency

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  NAMING CONVENTION CONSISTENCY                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== File naming patterns ==="
echo "Checking for consistent patterns..."

echo ""
echo "--- store.py vs *_store.py vs stores.py ---"
find src/edison -name "*store*.py" -type f

echo ""
echo "--- manager.py vs *_manager.py vs managers.py ---"
find src/edison -name "*manager*.py" -type f

echo ""
echo "--- config.py vs *_config.py vs configs.py ---"
find src/edison -name "*config*.py" -type f

echo ""
echo "--- handler.py vs *_handler.py vs handlers.py ---"
find src/edison -name "*handler*.py" -type f

echo ""
echo "=== Function naming patterns ==="
echo "--- get_ vs fetch_ vs retrieve_ ---"
grep -rh "def get_\|def fetch_\|def retrieve_" src/edison --include="*.py" | wc -l
echo "get_ functions"
grep -rh "def fetch_" src/edison --include="*.py" | wc -l
echo "fetch_ functions"
grep -rh "def retrieve_" src/edison --include="*.py" | wc -l
echo "retrieve_ functions"
echo "Expected: Use ONE consistent prefix"

echo ""
echo "--- create_ vs make_ vs build_ ---"
grep -rh "def create_" src/edison --include="*.py" | wc -l
echo "create_ functions"
grep -rh "def make_" src/edison --include="*.py" | wc -l
echo "make_ functions"
grep -rh "def build_" src/edison --include="*.py" | wc -l
echo "build_ functions"
```

### 3.2 Module Structure Consistency

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  MODULE STRUCTURE CONSISTENCY                                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Compare module structures ==="

echo ""
echo "--- session/ module structure ---"
ls -la src/edison/core/session/*.py 2>/dev/null | head -20

echo ""
echo "--- task/ module structure ---"
ls -la src/edison/core/task/*.py 2>/dev/null | head -20

echo ""
echo "--- qa/ module structure ---"
ls -la src/edison/core/qa/*.py 2>/dev/null | head -20

echo ""
echo "=== Do they follow the same pattern? ==="
echo "Expected files in each domain module:"
echo "- __init__.py"
echo "- store.py (data persistence)"
echo "- manager.py (business logic)"
echo "- config.py (configuration)"
echo "- models.py (data models)"
echo "- validation.py (validators)"
```

### 3.3 Import Style Consistency

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  IMPORT STYLE CONSISTENCY                                                    ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Absolute vs relative imports ==="
echo "Absolute imports (from edison...):"
grep -rh "^from edison\." src/edison --include="*.py" | wc -l

echo "Relative imports (from .xxx):"
grep -rh "^from \.\|^from \.\." src/edison --include="*.py" | wc -l

echo ""
echo "Expected: Consistent style throughout"

echo ""
echo "=== Import grouping ==="
echo "Check a few files for consistent grouping:"
echo "1. stdlib, 2. third-party, 3. local"
head -20 src/edison/core/session/store.py 2>/dev/null
echo "---"
head -20 src/edison/core/task/store.py 2>/dev/null
```

### 3.4 Error Handling Consistency

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  ERROR HANDLING CONSISTENCY                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Exception types used ==="
grep -rh "raise [A-Z]" src/edison --include="*.py" | \
    sed 's/.*raise \([A-Za-z]*\).*/\1/' | \
    sort | uniq -c | sort -rn

echo ""
echo "=== Custom exceptions defined ==="
grep -rn "class.*Exception\|class.*Error" src/edison --include="*.py" | grep -v "except"

echo ""
echo "=== Are all custom exceptions in exceptions.py? ==="
grep -rn "class.*Exception\|class.*Error" src/edison --include="*.py" | grep -v "exceptions.py\|except"
```

### 3.5 Return Value Consistency

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  RETURN VALUE CONSISTENCY                                                    ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Optional vs None returns ==="
grep -rh "-> Optional\[" src/edison --include="*.py" | wc -l
echo "functions return Optional[T]"

grep -rh "return None" src/edison --include="*.py" | wc -l
echo "functions return None"

echo ""
echo "=== Result/Either patterns vs exceptions ==="
echo "Check: Is error handling consistent (exceptions vs result types)?"

echo ""
echo "=== Boolean returns naming ==="
grep -rh "def is_\|def has_\|def can_\|def should_" src/edison --include="*.py" | head -20
echo "Expected: These should return bool"
```

---

## 🔬 PHASE 4: CODE STYLE CONSISTENCY

### 4.1 Docstring Style

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  DOCSTRING STYLE CONSISTENCY                                                 ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Docstring formats used ==="
echo "Google style (Args:, Returns:):"
grep -rh "Args:\|Returns:\|Raises:" src/edison --include="*.py" | wc -l

echo "NumPy style (Parameters, Returns):"
grep -rh "Parameters\|----------" src/edison --include="*.py" | wc -l

echo "Sphinx style (:param, :return:):"
grep -rh ":param\|:return:\|:raises:" src/edison --include="*.py" | wc -l

echo ""
echo "Expected: ONE consistent docstring format"
```

### 4.2 String Formatting Style

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  STRING FORMATTING CONSISTENCY                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== String formatting styles used ==="
echo "f-strings:"
grep -rh 'f".*{' src/edison --include="*.py" | wc -l

echo ".format():"
grep -rh '\.format(' src/edison --include="*.py" | wc -l

echo "% formatting:"
grep -rh '% (' src/edison --include="*.py" | wc -l

echo ""
echo "Expected: Use f-strings consistently (Python 3.6+)"
```

### 4.3 Type Hint Consistency

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  TYPE HINT CONSISTENCY                                                       ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Functions with type hints vs without ==="
total_funcs=$(grep -rh "^def \|^    def " src/edison --include="*.py" | wc -l)
typed_funcs=$(grep -rh "^def .*->\|^    def .*->" src/edison --include="*.py" | wc -l)
echo "Total functions: $total_funcs"
echo "With return type hints: $typed_funcs"
echo "Percentage: $(echo "scale=1; $typed_funcs * 100 / $total_funcs" | bc 2>/dev/null || echo "N/A")%"

echo ""
echo "=== typing module usage ==="
grep -rh "from typing import\|import typing" src/edison --include="*.py" | head -10

echo ""
echo "=== Union vs | syntax ==="
grep -rh "Union\[" src/edison --include="*.py" | wc -l
echo "Union[X, Y] usages"
grep -rh " | None\| | " src/edison --include="*.py" | grep -v "#" | wc -l
echo "X | Y usages (Python 3.10+)"
```

---

## 🔬 PHASE 5: STRUCTURAL COHERENCE

### 5.1 Layer Architecture Consistency

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  LAYER ARCHITECTURE CONSISTENCY                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== CLI → Core dependency (should be one-way) ==="
grep -rn "from edison.cli\|import edison.cli" src/edison/core --include="*.py"
echo "(Should be empty - core should not import from cli)"

echo ""
echo "=== Core → Data dependency ==="
grep -rn "from edison.data\|import edison.data" src/edison/core --include="*.py" | head -10

echo ""
echo "=== Expected architecture ==="
echo "CLI → Core → Data (one-way dependencies)"
echo "Utils should be leaf nodes (no internal dependencies)"
```

### 5.2 Package __init__.py Consistency

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  PACKAGE __init__.py CONSISTENCY                                             ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== __init__.py sizes (should be minimal) ==="
for f in $(find src/edison -name "__init__.py" -type f); do
    lines=$(wc -l < "$f")
    if [ "$lines" -gt 20 ]; then
        echo "⚠️  Large __init__.py ($lines lines): $f"
    fi
done

echo ""
echo "=== __all__ definitions ==="
grep -rn "__all__" src/edison --include="__init__.py" | head -20

echo ""
echo "=== Check for consistent export patterns ==="
```

---

## 📊 CREATE ANALYSIS SUMMARY

```markdown
# Audit 5: Legacy Code & Coherence Summary

## Legacy Code Found (Rule #3 Violations)
| Type | Count | Locations |
|------|-------|-----------|
| 'legacy' markers | [count] | [files] |
| 'deprecated' markers | [count] | [files] |
| Backward compat code | [count] | [files] |
| Shim/wrapper modules | [count] | [files] |

## Dead Code Found
| Type | Count | Locations |
|------|-------|-----------|
| Unreferenced files | [count] | [files] |
| Unreferenced functions | [count] | [list] |
| Unreferenced classes | [count] | [list] |

## Coherence Issues (Rule #12 Violations)

### Naming Inconsistencies
| Pattern | Variants Found | Should Be |
|---------|----------------|-----------|
| Data retrieval | get_, fetch_, retrieve_ | get_ |
| Object creation | create_, make_, build_ | create_ |

### Structure Inconsistencies
| Module | Has store.py | Has manager.py | Has config.py | Has models.py |
|--------|--------------|----------------|---------------|---------------|
| session | YES/NO | YES/NO | YES/NO | YES/NO |
| task | YES/NO | YES/NO | YES/NO | YES/NO |
| qa | YES/NO | YES/NO | YES/NO | YES/NO |

### Style Inconsistencies
| Aspect | Style A | Style B | Recommended |
|--------|---------|---------|-------------|
| Imports | absolute | relative | [choice] |
| Docstrings | Google | Sphinx | [choice] |
| Formatting | f-strings | .format() | f-strings |

## Recommendations
1. [CRITICAL] Delete all legacy/deprecated code
2. [HIGH] Remove dead code
3. [MEDIUM] Standardize naming conventions
4. [MEDIUM] Align module structures
5. [LOW] Unify code style
```

---

## 🔨 REMEDIATION PATTERNS

### Removing Legacy Code:

```bash
# 1. Find all legacy markers
grep -rln "legacy\|deprecated\|compat" src/

# 2. For each file, determine if it can be deleted
# 3. Update all imports to use canonical modules
# 4. Delete legacy files
# 5. Run tests
```

### Standardizing Names:

```bash
# Choose ONE prefix and rename all others
# Example: standardize on get_ instead of fetch_/retrieve_

# 1. Find all fetch_ functions
grep -rn "def fetch_" src/

# 2. Rename to get_
# 3. Update all call sites
# 4. Run tests
```

---

## ✅ SUCCESS CRITERIA

- [ ] No files containing 'legacy' or 'deprecated'
- [ ] No backward compatibility code
- [ ] No dead/unreferenced code
- [ ] Consistent naming conventions
- [ ] Consistent module structure
- [ ] Consistent import style
- [ ] Consistent error handling
- [ ] Consistent docstring format
- [ ] Consistent type hints

---

## START HERE

```bash
cd /Users/leeroy/Documents/Development/edison

# Start with Phase 1 - Find legacy code
grep -rn "legacy\|deprecated\|compat" src/ --include="*.py" | wc -l

# Then Phase 2 - Find dead code
# Then Phase 3-5 - Coherence analysis
```

**LEGACY CODE IS TECHNICAL DEBT. DELETE IT.**
