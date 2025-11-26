# Edison Framework - Audit 2: Configuration & Hardcoded Values Analysis

## 🎯 AUDIT FOCUS

This audit targets violations of:
- **Rule #4: NO HARDCODED VALUES** - All config from YAML
- **Rule #5: 100% CONFIGURABLE** - Every behavior must be configurable via YAML

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

## 🔬 PHASE 1: MAGIC NUMBER DETECTION

### 1.1 Find Hardcoded Numeric Values

```bash
cd /Users/leeroy/Documents/Development/edison

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  MAGIC NUMBER DETECTION                                                       ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Hardcoded timeout values ==="
grep -rn "timeout.*=.*[0-9]\|TIMEOUT.*=.*[0-9]" src/edison --include="*.py" | grep -v "test_\|\.yaml"

echo ""
echo "=== Hardcoded retry/attempt values ==="
grep -rn "retry.*=.*[0-9]\|retries.*=.*[0-9]\|attempts.*=.*[0-9]\|max_.*=.*[0-9]" src/edison --include="*.py" | grep -v "test_\|\.yaml"

echo ""
echo "=== Hardcoded limit values ==="
grep -rn "limit.*=.*[0-9]\|LIMIT.*=.*[0-9]\|max.*=.*[0-9]\|MAX.*=.*[0-9]" src/edison --include="*.py" | grep -v "test_\|\.yaml" | head -30

echo ""
echo "=== Hardcoded delay/sleep values ==="
grep -rn "sleep(\|delay.*=.*[0-9]\|wait.*=.*[0-9]" src/edison --include="*.py" | grep -v "test_"

echo ""
echo "=== Hardcoded size values ==="
grep -rn "size.*=.*[0-9]\|SIZE.*=.*[0-9]\|bytes.*=.*[0-9]\|BYTES.*=.*[0-9]" src/edison --include="*.py" | grep -v "test_"

echo ""
echo "=== Large numeric literals (likely config values) ==="
grep -rn "= [0-9][0-9][0-9]\|= [0-9]\.[0-9]" src/edison --include="*.py" | grep -v "test_\|\.yaml\|version\|__version__" | head -30
```

### 1.2 Categorize by Severity

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  CATEGORIZE MAGIC NUMBERS BY TYPE                                            ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== CRITICAL: Business logic numbers ==="
echo "These MUST be in YAML config:"
grep -rn "= [0-9]" src/edison/core --include="*.py" | \
    grep -E "price|cost|rate|percent|threshold|score|weight|priority" | \
    grep -v "test_\|\.yaml"

echo ""
echo "=== HIGH: Operational parameters ==="
echo "These SHOULD be in YAML config:"
grep -rn "= [0-9]" src/edison/core --include="*.py" | \
    grep -E "timeout|retry|limit|max|min|count|interval|duration|period" | \
    grep -v "test_\|\.yaml" | head -30

echo ""
echo "=== MEDIUM: Constants that rarely change ==="
echo "These COULD be in YAML but may be OK as code constants:"
grep -rn "= [0-9]" src/edison/core --include="*.py" | \
    grep -E "version|buffer|chunk|batch" | \
    grep -v "test_\|\.yaml"
```

---

## 🔬 PHASE 2: HARDCODED STRING DETECTION

### 2.1 Find Hardcoded Path Strings

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  HARDCODED PATH DETECTION                                                     ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Absolute paths ==="
grep -rn '"/[a-z]\|"/Users\|"/home\|"/tmp\|"/var' src/edison --include="*.py" | grep -v "test_"

echo ""
echo "=== Relative paths that should be configurable ==="
grep -rn '"\./\|"\.\./' src/edison --include="*.py" | grep -v "test_"

echo ""
echo "=== .edison directory references ==="
grep -rn '\.edison\|"\.edison"\|".edison"' src/edison --include="*.py"

echo ""
echo "=== Filename patterns ==="
grep -rn '\.yaml"\|\.yml"\|\.json"\|\.txt"\|\.log"' src/edison --include="*.py" | grep -v "test_\|schema" | head -30

echo ""
echo "=== Expected: All paths should come from paths/ module or YAML config ==="
```

### 2.2 Find Hardcoded Command Strings

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  HARDCODED COMMAND DETECTION                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Shell commands ==="
grep -rn '"git \|"npm \|"yarn \|"pip \|"python \|"pytest \|"uv ' src/edison --include="*.py" | grep -v "test_"

echo ""
echo "=== subprocess.run with hardcoded commands ==="
grep -rn "subprocess\.\|run(\[" src/edison --include="*.py" | grep -v "utils/subprocess.py\|test_" | head -20

echo ""
echo "=== Expected: Commands should be configurable via commands.yaml ==="
```

### 2.3 Find Hardcoded URL/Endpoint Strings

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  HARDCODED URL/ENDPOINT DETECTION                                            ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== URLs ==="
grep -rn 'http://\|https://\|ftp://' src/edison --include="*.py" | grep -v "test_\|#"

echo ""
echo "=== API endpoints ==="
grep -rn '"/api/\|"/v[0-9]/\|endpoint.*=' src/edison --include="*.py" | grep -v "test_"

echo ""
echo "=== Expected: URLs should be in YAML config ==="
```

### 2.4 Find Hardcoded Error Messages

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  ERROR MESSAGE ANALYSIS                                                       ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Error messages (check for consistency) ==="
grep -rh 'raise.*Error\|raise.*Exception' src/edison --include="*.py" | \
    sed 's/.*raise \([A-Za-z]*\)(\(.*\))/\1: \2/' | \
    sort | head -40

echo ""
echo "=== Are error messages consistent? ==="
echo "Look for: Similar errors with different messages"
```

---

## 🔬 PHASE 3: CONFIGURATION FILE ANALYSIS

### 3.1 List All YAML Config Files

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  YAML CONFIGURATION FILE INVENTORY                                           ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== All YAML config files ==="
find src/edison/data/config -name "*.yaml" -o -name "*.yml" | sort

echo ""
echo "=== Config file sizes and content summary ==="
for f in $(find src/edison/data/config -name "*.yaml" -type f); do
    lines=$(wc -l < "$f")
    echo "$lines lines: $f"
done | sort -rn

echo ""
echo "=== What should each config file contain? ==="
echo "Review each file to ensure it covers all configurable aspects"
```

### 3.2 Analyze Config Coverage

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  CONFIG COVERAGE ANALYSIS                                                     ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== session.yaml - Does it cover all session params? ==="
cat src/edison/data/config/session.yaml 2>/dev/null | head -30
echo ""
echo "Hardcoded session values in code:"
grep -rn "session.*=\|SESSION.*=" src/edison/core/session --include="*.py" | grep "[0-9]\|\"" | head -10

echo ""
echo "=== tasks.yaml - Does it cover all task params? ==="
cat src/edison/data/config/tasks.yaml 2>/dev/null | head -30
echo ""
echo "Hardcoded task values in code:"
grep -rn "task.*=\|TASK.*=" src/edison/core/task --include="*.py" | grep "[0-9]\|\"" | head -10

echo ""
echo "=== process.yaml - Does it cover all process params? ==="
cat src/edison/data/config/process.yaml 2>/dev/null | head -30
echo ""
echo "Hardcoded process values in code:"
grep -rn "timeout\|retry\|max_\|interval" src/edison/core/process --include="*.py" | grep "=" | head -10
```

### 3.3 Check Config Loading Patterns

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  CONFIG LOADING PATTERN ANALYSIS                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== How is config loaded? ==="
grep -rn "ConfigManager\|get_config\|load_config" src/edison --include="*.py" | head -20

echo ""
echo "=== Are defaults properly defined in YAML, not code? ==="
grep -rn "default.*=\|DEFAULT.*=" src/edison/core --include="*.py" | grep -v "test_\|None\|True\|False" | head -30

echo ""
echo "=== Fallback values (should be in YAML defaults) ==="
grep -rn "\.get(\|getattr.*," src/edison/core --include="*.py" | grep -v "test_" | head -20
```

---

## 🔬 PHASE 4: BEHAVIOR CONFIGURABILITY AUDIT

### 4.1 Feature Flags and Toggles

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  FEATURE FLAG / TOGGLE ANALYSIS                                              ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Boolean flags that control behavior ==="
grep -rn "if.*enabled\|if.*disabled\|is_.*=\|has_.*=\|use_.*=\|allow_.*=" src/edison/core --include="*.py" | head -30

echo ""
echo "=== Are these configurable via YAML? ==="
echo "Check: Each flag should have a YAML config entry"

echo ""
echo "=== Environment variable usage (should prefer YAML) ==="
grep -rn "os.environ\|os.getenv\|environ.get" src/edison --include="*.py"
```

### 4.2 Behavioral Parameters

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  BEHAVIORAL PARAMETER ANALYSIS                                               ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Validation rules (should be configurable) ==="
grep -rn "validate\|is_valid\|check_" src/edison/core --include="*.py" | \
    grep -E "len\(|>|<|==|!=" | head -20

echo ""
echo "=== Formatting/output parameters ==="
grep -rn "format\|indent\|width\|color\|style" src/edison/core --include="*.py" | \
    grep "=" | grep -v "test_" | head -20

echo ""
echo "=== Logging levels (should be configurable) ==="
grep -rn "logging\.\|logger\.\|log\." src/edison/core --include="*.py" | \
    grep -E "DEBUG|INFO|WARNING|ERROR|CRITICAL" | head -20
```

---

## 🔬 PHASE 5: DEFAULT VALUE AUDIT

### 5.1 Find All Default Values in Code

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  DEFAULT VALUE AUDIT                                                          ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== Function parameters with defaults ==="
grep -rn "def .*=.*[0-9]\|def .*=\"" src/edison/core --include="*.py" | \
    grep -v "test_\|None\|True\|False\|=\[\]\|={}" | head -40

echo ""
echo "=== Class attributes with defaults ==="
grep -rn "self\.[a-z_]* = [0-9]\|self\.[a-z_]* = \"" src/edison/core --include="*.py" | \
    grep -v "test_" | head -30

echo ""
echo "=== Module-level constants ==="
grep -rn "^[A-Z_]* = [0-9]\|^[A-Z_]* = \"" src/edison/core --include="*.py" | \
    grep -v "test_\|__version__" | head -30
```

### 5.2 Compare Code Defaults vs YAML Defaults

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  CODE vs YAML DEFAULTS COMPARISON                                            ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== defaults.yaml content ==="
cat src/edison/data/config/defaults.yaml 2>/dev/null

echo ""
echo "=== Are code defaults duplicating YAML defaults? ==="
echo "Goal: Code should READ from YAML, not define its own defaults"

echo ""
echo "=== Check for redundant defaults in code ==="
# Look for common default patterns
grep -rn "timeout.*30\|timeout.*60\|retry.*3\|max.*10" src/edison/core --include="*.py" | grep -v "test_"
```

---

## 🔬 PHASE 6: SCHEMA VALIDATION

### 6.1 Check Schema Files

```bash
echo ""
echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║  SCHEMA FILE ANALYSIS                                                         ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"

echo ""
echo "=== All schema files ==="
find src/edison/data/schemas -name "*.schema.json" -type f | sort

echo ""
echo "=== Do schemas define all configurable properties? ==="
for f in $(find src/edison/data/schemas -name "*.schema.json" -type f | head -5); do
    echo "--- $f ---"
    grep -o '"[a-z_]*":' "$f" | sort -u | head -10
done

echo ""
echo "=== Are schemas up-to-date with actual usage? ==="
echo "Compare schema properties with code usage"
```

---

## 📊 CREATE ANALYSIS SUMMARY

```markdown
# Audit 2: Configuration & Hardcoded Values Summary

## Magic Numbers Found
| Location | Value | Type | Should Be In |
|----------|-------|------|--------------|
| [file:line] | [number] | timeout/retry/limit | [config.yaml] |

## Hardcoded Strings Found
| Location | Value | Type | Should Be In |
|----------|-------|------|--------------|
| [file:line] | [string] | path/command/url | [config.yaml] |

## Config Coverage Gaps
| Module | Missing Config | Hardcoded In Code |
|--------|----------------|-------------------|
| session | [list] | [locations] |
| task | [list] | [locations] |
| qa | [list] | [locations] |

## Non-Configurable Behaviors
| Behavior | Location | Should Allow Config? |
|----------|----------|---------------------|
| [describe] | [file] | YES/NO |

## Recommendations
1. [HIGH] Move X to config
2. [MEDIUM] Add Y to schema
3. [LOW] Consider making Z configurable

## Verdict
- Total hardcoded values: [count]
- Critical (must fix): [list]
- Medium (should fix): [list]
- Low (nice to have): [list]
```

---

## 🔨 REMEDIATION PATTERN

### Moving Hardcoded Value to YAML Config:

**Step 1: Add to appropriate YAML file**
```yaml
# src/edison/data/config/session.yaml
session:
  timeout: 300  # Previously hardcoded as 300 in code
  max_retries: 3
```

**Step 2: Update code to read from config**
```python
# Before (BAD)
TIMEOUT = 300

# After (GOOD)
from edison.core.config import get_config
config = get_config()
TIMEOUT = config.session.timeout
```

**Step 3: Update schema if exists**
```json
{
  "properties": {
    "timeout": {
      "type": "integer",
      "default": 300,
      "description": "Session timeout in seconds"
    }
  }
}
```

---

## ✅ SUCCESS CRITERIA

- [ ] No magic numbers in business logic
- [ ] No hardcoded paths (use paths/ module)
- [ ] No hardcoded commands (use commands.yaml)
- [ ] No hardcoded URLs (use config)
- [ ] All timeouts/retries/limits from YAML
- [ ] All behavioral toggles configurable
- [ ] Defaults defined in YAML, not code
- [ ] Schemas match actual usage

---

## START HERE

```bash
cd /Users/leeroy/Documents/Development/edison

# Start with Phase 1 - Magic numbers are highest priority
# These directly affect runtime behavior

# Then Phase 2 - Hardcoded strings
# Phase 3 - Config coverage
# Phase 4 - Behavioral configurability
# Phase 5 - Default values
# Phase 6 - Schema validation
```

**DOCUMENT ALL FINDINGS. PRIORITIZE BY IMPACT.**
