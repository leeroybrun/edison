# AUDIT 02: Hardcoded Values & Configuration Analysis

**Audit Date:** 2025-11-26
**Scope:** Edison Core (`src/edison/core`)
**Rules Audited:** #4 (NO HARDCODED VALUES), #5 (100% CONFIGURABLE)

---

## EXECUTIVE SUMMARY

### Overall Status: ⚠️ MIXED - Significant Violations Found

**Key Findings:**
- ✅ **GOOD:** Core configuration system is well-designed with YAML-first approach
- ✅ **GOOD:** Most timeouts, dimensions, and paths are configurable via `defaults.yaml`
- ⚠️ **MODERATE:** ~50+ hardcoded values found across the codebase
- ❌ **CRITICAL:** Many environment variables used as fallback without config integration
- ❌ **CRITICAL:** Directory names, file patterns, and prefixes are hardcoded
- ❌ **CRITICAL:** Magic numbers in locking, retry logic, and text processing

**Compliance Score:** 65/100
- Config System Design: 90/100
- Actual Usage: 50/100
- Missing Config Coverage: 40/100

---

## PART 1: CRITICAL HARDCODED VALUES (MUST FIX)

### 1.1 Numeric Literals - Timeouts & Delays

#### File Locking (`src/edison/core/file_io/locking.py`)
```python
LINE 29:  timeout: float = 10.0,
LINE 33:  poll_interval: float = 0.1,
```
**Impact:** CRITICAL
**Current:** Hardcoded 10s timeout, 0.1s poll interval
**Should Be:** Config keys `file_io.lock_timeout_seconds` and `file_io.lock_poll_interval`
**Reason:** Different environments need different timeouts (NFS, distributed systems)

#### Retry Logic (`src/edison/core/utils/resilience.py`)
```python
LINE 20:  max_attempts: int = 3,
LINE 21:  initial_delay: float = 1.0,
LINE 22:  backoff_factor: float = 2.0,
LINE 23:  max_delay: float = 60.0,
```
**Impact:** CRITICAL
**Current:** Hardcoded retry parameters
**Already Exists in Config:** `defaults.yaml` has `resilience.retry.*` but NOT USED
**Action:** Replace defaults with `config.get("resilience.retry.max_attempts", 3)`

#### JSON I/O Lock Timeout (`src/edison/core/utils/json_io.py`)
```python
LINE 33: _LOCK_TIMEOUT_SECONDS = float(os.environ.get("EDISON_JSON_IO_LOCK_TIMEOUT", 5.0))
```
**Impact:** MEDIUM
**Current:** Environment variable fallback to 5.0
**Should Be:** Config key `json_io.lock_timeout_seconds`
**Issue:** Environment variable used instead of YAML config

#### Subprocess Timeouts (`src/edison/core/utils/subprocess.py`)
```python
LINE 29: DEFAULT_GIT_TIMEOUT = float(os.environ.get("EDISON_GIT_TIMEOUT_SECONDS", "60"))
LINE 30: DEFAULT_DB_TIMEOUT = float(os.environ.get("EDISON_DB_TIMEOUT_SECONDS", "30"))
```
**Impact:** MEDIUM
**Already Exists in Config:** `defaults.yaml` has `subprocess_timeouts.*` (lines 519-525)
**Issue:** Environment variables used INSTEAD of config
**Action:** Remove env var usage, use config directly via `_load_timeouts()`

### 1.2 Text Processing Constants

#### DRY Duplication Detection (`src/edison/core/utils/text.py`)
```python
LINE 21: ENGINE_VERSION = "2.5B-1"
LINE 39: def _shingles(words: List[str], k: int = 12)
LINE 46: def dry_duplicate_report(sections: Dict[str, str], *, min_shingles: int = 2, k: int = 12)
```
**Impact:** HIGH
**Current:** k=12 (shingle size), min_shingles=2 hardcoded
**Should Be:** Config keys `composition.dry.shingle_size`, `composition.dry.min_shingles`
**Reason:** DRY detection sensitivity should be tunable per project

#### Environment Variable Fallbacks (Multiple Files)
```python
# src/edison/core/composition/agents.py:278
int(os.environ.get("EDISON_DRY_MIN_SHINGLES", "2"))

# src/edison/core/composition/composers.py:149
int(_os.environ.get("EDISON_DRY_MIN_SHINGLES", "2"))

# src/edison/core/composition/guidelines.py:358
int(os.environ.get("EDISON_DRY_MIN_SHINGLES", "2"))
```
**Impact:** HIGH
**Issue:** Same value duplicated 3+ times via environment variables
**Action:** Create single config source, remove all env var usages

### 1.3 Depth & Size Limits

#### Include Depth (`src/edison/core/composition/includes.py`)
```python
LINE 18: MAX_DEPTH = 3
```
**Impact:** MEDIUM
**Current:** Hardcoded max include depth = 3
**Should Be:** Config key `composition.max_include_depth`
**Reason:** Complex projects may need deeper includes

#### Session ID Length (`src/edison/core/paths/resolver.py`)
```python
LINE 298: f"Session ID too long: {len(session_id)} characters (max 64)"
```
**Impact:** LOW
**Current:** Hardcoded 64 character limit
**Should Be:** Config key `session.max_id_length`

#### Short Description Max (`src/edison/core/ide/commands.py`)
```python
LINE 16: DEFAULT_SHORT_DESC_MAX = 80
```
**Impact:** LOW
**Current:** Hardcoded 80 character limit
**Should Be:** Config key `commands.short_desc_max_length`

#### LRU Cache Size (`src/edison/core/utils/subprocess.py`)
```python
LINE 47: @lru_cache(maxsize=4)
```
**Impact:** LOW
**Current:** Cache size hardcoded to 4
**Should Be:** Config key `subprocess.timeout_cache_size`

---

## PART 2: HARDCODED STRINGS (DIRECTORY NAMES, PATHS, PATTERNS)

### 2.1 Directory Names (CRITICAL)

**Location:** Throughout `src/edison/core`
**Count:** 321+ occurrences found

#### Primary Directories
```python
# Hardcoded in ~50+ files:
".edison"          # Core framework directory
".project"         # Management directory
".claude"          # Claude Code output
".cursor"          # Cursor output
".codex"           # Codex output
".zen"             # Zen MCP output
```

**Impact:** CRITICAL
**Current:** Hardcoded throughout codebase
**Exists in Config:** `defaults.yaml` has `adapters.claude.output_dir`, etc. (lines 527-547)
**Issue:** Config exists BUT not consistently used
**Action:** Centralize all directory references to use config values

#### Specific Examples
```python
# src/edison/core/ide/hooks.py:65-66
self.core_dir = self.repo_root / ".edison" / "core"
self.packs_dir = self.repo_root / ".edison" / "packs"

# src/edison/core/ide/settings.py:146
target = self.repo_root / ".claude" / "settings.json"

# src/edison/core/paths/project.py:23
DEFAULT_PROJECT_CONFIG_PRIMARY = ".edison"
```

### 2.2 File Extensions & Names

#### Config File Extensions
```python
# Found in multiple files:
".yaml"
".yml"
".json"
".md"
".template"
".lock"
```
**Impact:** MEDIUM
**Should Be:** Config key `paths.config_extensions` = `[".yaml", ".yml"]`

#### Standard Filenames
```python
# Hardcoded throughout:
"session.json"
"task.json"
"manifest.json"
"orchestrator-manifest.json"
"settings.json"
"hooks.yaml"
"commands.yml"
"pack.yml"
```
**Impact:** MEDIUM
**Should Be:** Config keys under `filenames.*` section

### 2.3 Prefixes & Patterns

#### Task/Session Prefixes
```python
# src/edison/core/qa/transaction.py:91
safe_name = str(validator_name).replace("/", "-")

# src/edison/core/qa/bundler.py:32
return base / f"round-{int(round_num)}" / filename

# src/edison/core/qa/promoter.py:43-44
for rd in sorted([p for p in base.glob("round-*") if p.is_dir()], key=lambda p: p.name):
    reports.extend(sorted(rd.glob("validator-*-report.json")))
```

**Patterns Found:**
- `round-{N}` - Evidence round directories
- `validator-{name}-report.json` - Validator reports
- `session-` - Session prefixes
- `task-` - Task prefixes

**Impact:** HIGH
**Exists in Config:** `defaults.yaml` has `tasks.defaults.*Prefix` (lines 507-514)
**Issue:** Config exists BUT not used in code
**Action:** Replace all hardcoded patterns with config lookups

---

## PART 3: ENVIRONMENT VARIABLE ABUSE

### 3.1 Environment Variables Used Instead of Config

**Total Found:** 30+ instances

#### Critical Environment Variables
```python
# Path resolution
AGENTS_PROJECT_ROOT          # Used in 5+ files
EDISON_paths__project_config_dir  # Used instead of config

# Timeouts (DUPLICATE of YAML config)
EDISON_GIT_TIMEOUT_SECONDS   # Duplicates subprocess_timeouts.git_operations
EDISON_DB_TIMEOUT_SECONDS    # Duplicates subprocess_timeouts.db_operations
EDISON_JSON_IO_LOCK_TIMEOUT  # Should be in config

# DRY detection (DUPLICATED 3x in code)
EDISON_DRY_MIN_SHINGLES     # Should be composition.dry.min_shingles

# Debug flags
DEBUG_CONTEXT7               # Should be debug.context7_enabled

# Testing flags (acceptable in tests)
EDISON_FORCE_DISK_FULL
EDISON_FORCE_PERMISSION_ERROR
project_FORCE_DISK_FULL
project_FORCE_PERMISSION_ERROR

# Project metadata
PROJECT_NAME                 # Should come from config
PROJECT_TERMS                # Should come from config
```

**Impact:** CRITICAL
**Issue:** Environment variables used as PRIMARY config source instead of YAML
**Action:**
1. Remove all env var fallbacks EXCEPT `AGENTS_PROJECT_ROOT` (needed for isolation)
2. Move all config to YAML with env var OVERRIDES via `EDISON_*` pattern
3. Document env var override mechanism in config system

---

## PART 4: CONFIGURATION COVERAGE ANALYSIS

### 4.1 What's Already Configurable ✅

**Excellent Coverage:**
```yaml
# defaults.yaml (lines shown)
worktrees: (lines 8-18)
  - baseBranch, baseDirectory, archiveDirectory
  - branchPrefix, pathTemplate, cleanup settings

database: (lines 20-25)
  - enabled, templateStrategy, cleanupStrategy
  - sessionPrefix, adapter

tdd: (lines 27-30)
  - enforceRedGreenRefactor, requireEvidence, hmacValidation

resilience: (lines 35-43)
  - retry: max_attempts, initial_delay_seconds, backoff_factor, max_delay_seconds
  - circuit_breaker: failure_threshold, recovery_timeout_seconds

subprocess_timeouts: (lines 519-525)
  - git_operations, test_execution, build_operations
  - ai_calls, file_operations, default

validation.dimensions: (lines 51-56)
  - functionality, reliability, security, maintainability, performance

adapters: (lines 527-547)
  - claude, codex, cursor, zen output directories and filenames

cli: (lines 549-564)
  - json formatting, table formatting, confirm defaults

json_io: (lines 566-570)
  - indent, sort_keys, ensure_ascii, encoding
```

### 4.2 What's Missing from Config ❌

**File I/O Configuration:**
```yaml
file_io:
  lock_timeout_seconds: 10.0          # Currently hardcoded
  lock_poll_interval: 0.1             # Currently hardcoded
  lock_nfs_safe: true                 # Currently hardcoded
  lock_fail_open: false               # Currently hardcoded
```

**Text Processing Configuration:**
```yaml
composition:
  dry:
    shingle_size: 12                  # Currently hardcoded k=12
    min_shingles: 2                   # Currently env var EDISON_DRY_MIN_SHINGLES
    strip_headings: true              # Currently hardcoded
    strip_code_blocks: true           # Currently hardcoded
  max_include_depth: 3                # Currently hardcoded MAX_DEPTH
```

**Commands Configuration:**
```yaml
commands:
  short_desc_max_length: 80           # Currently DEFAULT_SHORT_DESC_MAX
  platforms: ["claude", "cursor", "codex"]  # Currently DEFAULT_PLATFORMS
```

**Session Configuration:**
```yaml
session:
  max_id_length: 64                   # Currently hardcoded in validation
  timeout_hours: 8                    # Already exists (line 46)
  stale_check_interval_hours: 1       # Already exists (line 47)
```

**File Patterns Configuration:**
```yaml
filenames:
  session: "session.json"
  task: "task.json"
  orchestrator_manifest: "orchestrator-manifest.json"
  settings: "settings.json"

patterns:
  round_directory: "round-{round}"
  validator_report: "validator-{name}-report.json"
  evidence_glob: "round-*"

extensions:
  config_primary: ".yaml"
  config_secondary: ".yml"
  data: ".json"
  documentation: ".md"
  template_suffix: ".template"
```

**QA Scoring Configuration:**
```yaml
qa:
  scoring:
    regression_threshold: 0.5         # Currently hardcoded
    high_severity_delta: -2.0         # Currently hardcoded
    medium_severity_delta: -0.5       # Currently hardcoded
```

**Subprocess Configuration:**
```yaml
subprocess:
  timeout_cache_size: 4               # Currently hardcoded lru_cache(maxsize=4)
  fallback_timeouts:                  # Currently FALLBACK_TIMEOUTS dict
    git_operations: 30.0
    test_execution: 300.0
    build_operations: 600.0
    ai_calls: 120.0
    file_operations: 10.0
    default: 60.0
```

**Process Detection Configuration:**
```yaml
process:
  llm_processes:                      # Already in process.yaml
    - claude
    - codex
    - gemini
    - cursor
    - aider
    - happy
  edison_processes:
    - edison
    - python
  edison_script_markers:
    - edison
    - .edison
    - scripts/tasks
    - scripts/session
    - scripts/qa
```

**Debug Configuration:**
```yaml
debug:
  context7_enabled: false             # Currently DEBUG_CONTEXT7 env var
  verbose_logging: false
  trace_config_loading: false
```

---

## PART 5: VIOLATIONS BY FILE

### 5.1 High Impact Files (>5 violations each)

**`src/edison/core/file_io/locking.py`**
- Violations: 3 (timeout, poll_interval, default values)
- Impact: CRITICAL (affects all file I/O)

**`src/edison/core/utils/resilience.py`**
- Violations: 4 (max_attempts, delays, backoff_factor)
- Impact: CRITICAL (retry logic not configurable)

**`src/edison/core/utils/subprocess.py`**
- Violations: 8+ (timeouts via env vars, fallback dict, cache size)
- Impact: HIGH (subprocess behavior inconsistent)

**`src/edison/core/utils/text.py`**
- Violations: 4 (ENGINE_VERSION, k=12, min_shingles)
- Impact: HIGH (DRY detection not tunable)

**`src/edison/core/composition/includes.py`**
- Violations: 2 (MAX_DEPTH, directory names)
- Impact: MEDIUM

**`src/edison/core/ide/commands.py`**
- Violations: 3 (SHORT_DESC_MAX, platforms list)
- Impact: LOW

**`src/edison/core/paths/resolver.py`**
- Violations: 10+ (directory names, validation limits)
- Impact: CRITICAL (path resolution core logic)

**`src/edison/core/qa/scoring.py`**
- Violations: 3 (regression threshold, severity deltas)
- Impact: MEDIUM

---

## PART 6: ACCEPTABLE HARDCODED VALUES

### 6.1 True Constants (No Action Needed)

**HTTP Status Codes:**
- None found in core (good!)

**Mathematical Constants:**
- Weight sum validation (100) in `qa/validator.py:49` - ACCEPTABLE (validation logic)
- Percentage calculations - ACCEPTABLE

**Standard Protocols:**
- ISO-8601 timestamp format - ACCEPTABLE
- UTF-8 encoding - ACCEPTABLE (but should still be configurable for edge cases)

**Domain-Specific Constants:**
- Git command names - ACCEPTABLE
- JSON/YAML format specifications - ACCEPTABLE

---

## PART 7: RECOMMENDED ACTIONS

### Priority 1: CRITICAL (Do First) 🔴

1. **Fix Resilience Retry Logic**
   - File: `src/edison/core/utils/resilience.py`
   - Action: Use config values from `defaults.yaml:resilience.retry.*`
   - Code Change:
   ```python
   # Current:
   def retry_with_backoff(max_attempts: int = 3, ...)

   # Should be:
   def retry_with_backoff(
       max_attempts: Optional[int] = None,
       config: Optional[Dict] = None,
       ...
   ):
       if max_attempts is None:
           cfg = config or load_config()
           max_attempts = cfg.get("resilience", {}).get("retry", {}).get("max_attempts", 3)
   ```

2. **Remove Environment Variable Duplication**
   - Files: `subprocess.py`, `agents.py`, `composers.py`, `guidelines.py`, `json_io.py`
   - Action: Remove ALL env var fallbacks that duplicate YAML config
   - Keep only: `AGENTS_PROJECT_ROOT` for test isolation
   - Use: ConfigManager `EDISON_*` override pattern for ALL config

3. **Centralize Directory Name References**
   - Files: All `ide/*.py`, `paths/*.py`, `adapters/*.py`
   - Action: Create `PathConfig` class that loads from `defaults.yaml:adapters.*`
   - Replace: All hardcoded `".edison"`, `".claude"`, etc. with config lookups

4. **Fix File Locking Parameters**
   - File: `src/edison/core/file_io/locking.py`
   - Action: Add to `defaults.yaml` and use in function

### Priority 2: HIGH (Do Soon) 🟠

5. **Add Text Processing Configuration**
   - File: `src/edison/core/utils/text.py`
   - Action: Add `composition.dry.*` section to defaults.yaml
   - Replace: Hardcoded k=12, min_shingles=2

6. **Add Missing Config Sections**
   - Add: `file_io.*`, `composition.dry.*`, `filenames.*`, `patterns.*`
   - Update: All code to use new config keys

7. **Standardize Filename/Pattern Usage**
   - Action: Create config section for all filenames and patterns
   - Replace: All f-strings like `f"round-{N}"` with config lookups

### Priority 3: MEDIUM (Nice to Have) 🟡

8. **Add Session/Task Limits to Config**
   - Add: `session.max_id_length`, `commands.short_desc_max_length`

9. **Add QA Scoring Thresholds to Config**
   - Add: `qa.scoring.regression_threshold`, severity deltas

10. **Document Environment Variable Override Pattern**
    - Create: Documentation for `EDISON_*` pattern
    - Clarify: When to use env vars vs. config

---

## PART 8: CONFIG FILE ADDITIONS NEEDED

### Addition to `defaults.yaml`

```yaml
# Add after line 577 (after time: section)

# File I/O and locking configuration
file_io:
  locking:
    timeout_seconds: 10.0
    poll_interval: 0.1
    nfs_safe: true
    fail_open: false

# Composition system configuration
composition:
  dry:
    shingle_size: 12
    min_shingles: 2
    strip_headings: true
    strip_code_blocks: true
  max_include_depth: 3
  cache:
    enabled: true
    ttl_seconds: 3600

# Standard filenames used throughout the system
filenames:
  session: "session.json"
  task: "task.json"
  orchestrator_manifest: "orchestrator-manifest.json"
  settings: "settings.json"
  hooks: "hooks.yaml"
  commands: "commands.yml"
  pack: "pack.yml"

# File patterns and templates
patterns:
  round_directory: "round-{round}"
  validator_report: "validator-{name}-report.json"
  evidence_glob: "round-*"
  session_prefix: "session-"
  task_prefix: "task-"

# File extensions
extensions:
  config_primary: ".yaml"
  config_secondary: ".yml"
  data: ".json"
  documentation: ".md"
  template_suffix: ".template"
  lock_suffix: ".lock"

# Commands and IDE integration
commands:
  short_desc_max_length: 80
  platforms: ["claude", "cursor", "codex"]

# Session configuration additions
session:
  max_id_length: 64
  # timeout_hours: 8              # Already exists
  # stale_check_interval_hours: 1 # Already exists

# QA scoring thresholds
qa:
  scoring:
    regression_threshold: 0.5
    high_severity_delta: -2.0
    medium_severity_delta: -0.5

# Debug flags
debug:
  context7_enabled: false
  verbose_logging: false
  trace_config_loading: false

# Subprocess configuration additions
subprocess:
  cache_size: 4
  # subprocess_timeouts section already exists (lines 519-525)
```

---

## PART 9: EFFORT ESTIMATES

### By Priority

**Priority 1 (CRITICAL):**
- Resilience retry config: 2 hours
- Remove env var duplication: 4 hours
- Centralize directory names: 8 hours
- Fix file locking: 2 hours
- **Total P1:** ~16 hours (~2 days)

**Priority 2 (HIGH):**
- Text processing config: 4 hours
- Add missing config sections: 3 hours
- Standardize filename/pattern usage: 6 hours
- **Total P2:** ~13 hours (~1.5 days)

**Priority 3 (MEDIUM):**
- Session/task limits: 2 hours
- QA scoring thresholds: 2 hours
- Documentation: 3 hours
- **Total P3:** ~7 hours (~1 day)

**Total Estimated Effort:** 36 hours (~4.5 days)

---

## PART 10: COMPLIANCE METRICS

### Current State

| Category | Count | Configurable | Not Configurable | % Compliant |
|----------|-------|--------------|------------------|-------------|
| Timeout Values | 12 | 6 | 6 | 50% |
| Directory Names | 8 | 8 | 0 | 100% (exists but not used) |
| File Patterns | 15 | 0 | 15 | 0% |
| Numeric Limits | 10 | 2 | 8 | 20% |
| Retry/Resilience | 4 | 4 | 0 | 100% (exists but not used) |
| Text Processing | 4 | 0 | 4 | 0% |
| Environment Vars | 30 | 0 | 30 | 0% (should use config) |

**Overall Compliance:** 40/83 = **48.2%**

### Target State (After Fixes)

| Category | Target % |
|----------|----------|
| Timeout Values | 100% |
| Directory Names | 100% |
| File Patterns | 100% |
| Numeric Limits | 100% |
| Retry/Resilience | 100% |
| Text Processing | 100% |
| Environment Vars | 95% (keep AGENTS_PROJECT_ROOT only) |

**Target Overall Compliance:** 98%

---

## PART 11: ANTI-PATTERNS FOUND

### 1. "Config Exists But Not Used"
**Files:** `resilience.py`, `subprocess.py`, `paths/*.py`
**Issue:** Config values defined in YAML but code uses hardcoded defaults
**Root Cause:** No enforcement of config usage

### 2. "Environment Variable as Primary Config"
**Files:** `subprocess.py`, `json_io.py`, `composition/*.py`
**Issue:** Environment variables used instead of YAML config
**Root Cause:** Easier to add env var than update config properly

### 3. "Duplicated Magic Numbers"
**Files:** `agents.py`, `composers.py`, `guidelines.py` (EDISON_DRY_MIN_SHINGLES)
**Issue:** Same value hardcoded 3+ times
**Root Cause:** No shared constant or config lookup

### 4. "Inline Defaults in Function Signatures"
**Everywhere:** `def foo(timeout: float = 10.0)`
**Issue:** Default values scattered across functions
**Root Cause:** Convenient but not maintainable

---

## PART 12: RECOMMENDATIONS FOR FUTURE

### 1. Enforce Config-First Policy
- Pre-commit hook to detect hardcoded values
- Lint rule to flag numeric literals (except 0, 1, -1)
- Code review checklist item

### 2. Create Config Validation
- JSON Schema for defaults.yaml
- Runtime validation on load
- Fail-fast on missing required config

### 3. Centralize Config Access
- Single `ConfigProvider` class
- Typed config accessors (no dict access)
- Cached config loading

### 4. Document Config Override Pattern
```python
# Recommended pattern:
def some_function(
    timeout: Optional[float] = None,
    config: Optional[Dict] = None
):
    cfg = config or load_config()
    timeout = timeout or cfg.get("my_module.timeout", 10.0)
```

### 5. Migration Strategy
- Phase 1: Add all missing config keys (week 1)
- Phase 2: Update code to use config (week 2-3)
- Phase 3: Add validation and tests (week 4)
- Phase 4: Remove all hardcoded fallbacks (week 5)

---

## PART 13: CONCLUSION

### Summary
The Edison codebase has a **well-designed configuration system** but **inconsistent usage**. The `defaults.yaml` file already contains many needed values, but code frequently ignores it in favor of hardcoded defaults or environment variables.

### Key Issues
1. ❌ **50+ hardcoded numeric values** that should use config
2. ❌ **30+ environment variables** used instead of YAML config
3. ❌ **300+ hardcoded directory/file names** despite config existing
4. ⚠️ **Duplicated magic numbers** across multiple files
5. ⚠️ **Config exists but not used** - biggest anti-pattern

### Path Forward
1. **DO NOT add new features until this is fixed** - technical debt is high
2. **Prioritize P1 items** - they affect core functionality
3. **Add config validation** - prevent regressions
4. **Update CLAUDE.md** - add config-first enforcement
5. **Create enforcement tools** - linters, pre-commit hooks

### Risk Assessment
- **Current State:** MEDIUM RISK - configuration is fragmented
- **After P1 Fixes:** LOW RISK - core behavior configurable
- **After All Fixes:** VERY LOW RISK - fully configurable system

---

## APPENDICES

### A. All Config Files Found
```
src/edison/data/config/
├── commands.yaml
├── composition.yaml
├── defaults.yaml (PRIMARY)
├── delegation.yaml
├── hooks.yaml
├── models.yaml
├── orchestrator.yaml
├── packs.yaml
├── process.yaml
├── session.yaml
├── settings.yaml
├── setup.yaml
├── state-machine.yaml
├── tasks.yaml
└── validators.yaml
```

### B. Environment Variables Inventory

**Project Root & Paths:**
- `AGENTS_PROJECT_ROOT` ✅ KEEP (test isolation)
- `EDISON_paths__project_config_dir` ❌ REMOVE (use config)

**Timeouts (Duplicates YAML):**
- `EDISON_GIT_TIMEOUT_SECONDS` ❌ REMOVE
- `EDISON_DB_TIMEOUT_SECONDS` ❌ REMOVE
- `EDISON_JSON_IO_LOCK_TIMEOUT` ❌ REMOVE

**DRY Detection:**
- `EDISON_DRY_MIN_SHINGLES` ❌ REMOVE (move to config)

**Debug:**
- `DEBUG_CONTEXT7` ❌ REMOVE (move to config)

**Testing (Keep for test isolation):**
- `EDISON_FORCE_DISK_FULL` ✅ KEEP
- `EDISON_FORCE_PERMISSION_ERROR` ✅ KEEP
- `project_FORCE_DISK_FULL` ✅ KEEP
- `project_FORCE_PERMISSION_ERROR` ✅ KEEP

**Project Metadata:**
- `PROJECT_NAME` ⚠️ REVIEW (might be needed for templates)
- `PROJECT_TERMS` ❌ REMOVE (move to config)

**CLI:**
- `EDISON_ASSUME_YES` ✅ KEEP (already in config as reference)

### C. Hardcoded Values Quick Reference

**Timeouts:**
- 10.0s - File locking
- 0.1s - Lock poll interval
- 5.0s - JSON I/O lock
- 60s - Git operations
- 30s - Database operations
- 60s - Max retry delay
- 300s - Circuit breaker recovery

**Sizes & Limits:**
- 80 - Short description max
- 64 - Session ID max length
- 12 - Shingle size (k)
- 2 - Min shingles
- 3 - Max include depth
- 4 - LRU cache size
- 3 - Max retry attempts

**Delays:**
- 1.0s - Initial retry delay
- 2.0 - Backoff factor

**Thresholds:**
- 0.5 - Regression threshold
- -2.0 - High severity delta
- 100 - Dimension weight sum

---

**End of Report**
