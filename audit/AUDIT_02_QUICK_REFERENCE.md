# AUDIT 02: Quick Reference - Hardcoded Values

**Date:** 2025-11-26
**Status:** ⚠️ 48% Compliant - Needs Immediate Action

---

## TOP 10 VIOLATIONS (Fix These First)

### 1. Retry Logic Not Using Config ❌
**File:** `src/edison/core/utils/resilience.py:20-23`
**Issue:** Hardcoded max_attempts=3, delays
**Config Exists:** YES - `defaults.yaml:resilience.retry.*`
**Fix:** 2 hours - Use config values

### 2. Environment Vars Instead of Config ❌
**Files:** `subprocess.py:29-30`, `json_io.py:33`
**Issue:** EDISON_GIT_TIMEOUT_SECONDS, etc.
**Config Exists:** YES - `defaults.yaml:subprocess_timeouts.*`
**Fix:** 2 hours - Remove env vars

### 3. DRY Detection Duplicated 3x ❌
**Files:** `agents.py:278`, `composers.py:149`, `guidelines.py:358`
**Issue:** Same EDISON_DRY_MIN_SHINGLES env var
**Config Exists:** NO
**Fix:** 4 hours - Add to config, update all

### 4. File Locking Hardcoded ❌
**File:** `file_io/locking.py:29,33`
**Issue:** timeout=10.0, poll_interval=0.1
**Config Exists:** NO
**Fix:** 2 hours - Add to config

### 5. Directory Names Everywhere ❌
**Files:** 50+ files
**Issue:** ".edison", ".claude", etc. hardcoded
**Config Exists:** PARTIAL - adapters section
**Fix:** 8 hours - Create PathConfig class

### 6. Text Processing Magic Numbers ❌
**File:** `utils/text.py:39,46`
**Issue:** k=12, min_shingles=2
**Config Exists:** NO
**Fix:** 2 hours - Add composition.dry config

### 7. Include Depth Hardcoded ❌
**File:** `composition/includes.py:18`
**Issue:** MAX_DEPTH = 3
**Config Exists:** NO
**Fix:** 1 hour - Add to config

### 8. Session ID Limit Hardcoded ❌
**File:** `paths/resolver.py:298`
**Issue:** max 64 characters
**Config Exists:** NO
**Fix:** 30 min - Add to config

### 9. Short Desc Limit Hardcoded ❌
**File:** `ide/commands.py:16`
**Issue:** DEFAULT_SHORT_DESC_MAX = 80
**Config Exists:** NO
**Fix:** 30 min - Add to config

### 10. QA Regression Threshold Hardcoded ❌
**File:** `qa/scoring.py:86`
**Issue:** threshold=0.5
**Config Exists:** NO
**Fix:** 1 hour - Add to config

---

## QUICK WINS (< 1 hour each)

1. ✅ Add missing config sections to defaults.yaml (30 min)
2. ✅ Fix session ID limit (30 min)
3. ✅ Fix short desc max (30 min)
4. ✅ Fix QA regression threshold (30 min)
5. ✅ Fix include depth (30 min)

**Total Quick Wins:** 2.5 hours

---

## CONFIG ADDITIONS NEEDED

Add to `src/edison/data/config/defaults.yaml` after line 577:

```yaml
file_io:
  locking:
    timeout_seconds: 10.0
    poll_interval: 0.1

composition:
  dry:
    shingle_size: 12
    min_shingles: 2
  max_include_depth: 3

filenames:
  session: "session.json"
  task: "task.json"
  orchestrator_manifest: "orchestrator-manifest.json"

patterns:
  round_directory: "round-{round}"
  validator_report: "validator-{name}-report.json"

extensions:
  config_primary: ".yaml"
  config_secondary: ".yml"

commands:
  short_desc_max_length: 80

session:
  max_id_length: 64

qa:
  scoring:
    regression_threshold: 0.5
```

---

## ENVIRONMENT VARIABLES TO REMOVE

### Delete (use config instead):
- ❌ `EDISON_GIT_TIMEOUT_SECONDS`
- ❌ `EDISON_DB_TIMEOUT_SECONDS`
- ❌ `EDISON_JSON_IO_LOCK_TIMEOUT`
- ❌ `EDISON_DRY_MIN_SHINGLES`
- ❌ `DEBUG_CONTEXT7`
- ❌ `EDISON_paths__project_config_dir`

### Keep:
- ✅ `AGENTS_PROJECT_ROOT` (test isolation)
- ✅ `EDISON_FORCE_*` (testing flags)
- ✅ `EDISON_*` override pattern (via ConfigManager)

---

## FILES WITH MOST VIOLATIONS

| File | Violations | Priority |
|------|-----------|----------|
| `paths/resolver.py` | 10+ | P1 |
| `utils/subprocess.py` | 8+ | P1 |
| `utils/resilience.py` | 4 | P1 |
| `utils/text.py` | 4 | P1 |
| `file_io/locking.py` | 3 | P1 |
| `composition/includes.py` | 2 | P2 |
| `qa/scoring.py` | 3 | P2 |
| `ide/commands.py` | 3 | P2 |

---

## TYPICAL CODE PATTERNS

### ❌ BEFORE (Wrong):
```python
def my_function(timeout: float = 10.0):
    # Hardcoded default
    pass

retry_count = int(os.environ.get("EDISON_RETRY", "3"))
```

### ✅ AFTER (Correct):
```python
def my_function(
    timeout: Optional[float] = None,
    config: Optional[Dict] = None
):
    if config is None:
        from ..config import ConfigManager
        config = ConfigManager().load_config(validate=False)

    timeout = timeout or config.get("my_module.timeout", 10.0)
```

---

## TESTING CHECKLIST

After making changes:

```bash
# 1. Validate YAML
python -c "import yaml; yaml.safe_load(open('src/edison/data/config/defaults.yaml'))"

# 2. Run tests
pytest tests/unit/config/
pytest tests/composition/

# 3. Check for remaining hardcoded values
grep -rn "timeout.*[0-9]" src/edison/core --include="*.py" | wc -l

# 4. Check for env var usage
grep -r "os.environ.get" src/edison/core --include="*.py" | grep -v AGENTS_PROJECT_ROOT | wc -l

# 5. Check for magic numbers
grep -rn "= [0-9]\+\." src/edison/core --include="*.py" | grep -v "0.0\|1.0" | wc -l
```

---

## EFFORT SUMMARY

| Phase | Tasks | Hours | Days |
|-------|-------|-------|------|
| P1 Critical | 6 tasks | 16h | 2d |
| P2 High | 4 tasks | 13h | 1.5d |
| P3 Medium | 6 tasks | 7h | 1d |
| **TOTAL** | **16 tasks** | **36h** | **4.5d** |

---

## NEXT STEPS

1. **Review this audit** with team
2. **Prioritize P1 items** - block all new features
3. **Start with quick wins** - build momentum
4. **Create feature branch** - `fix/hardcoded-values-audit-02`
5. **Work through action plan** - one task at a time
6. **Run tests after each change** - ensure no regressions
7. **Update documentation** - config guide
8. **Add enforcement** - pre-commit hooks

---

## CONTACTS & REFERENCES

- **Full Report:** `audit/AUDIT_02_HARDCODED_VALUES_REPORT.md`
- **Action Plan:** `audit/AUDIT_02_ACTION_PLAN.md`
- **Config File:** `src/edison/data/config/defaults.yaml`
- **Config Manager:** `src/edison/core/config.py`

---

**End of Quick Reference**
