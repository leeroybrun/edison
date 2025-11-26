# Edison Framework - Comprehensive Implementation Plan

## Document Purpose

This document provides a **complete, dependency-aware task breakdown** for remediating all audit findings. Each task includes:
- Unique Task ID
- Priority (P0-P3)
- Dependencies
- Effort estimate
- Validation criteria
- Parallelization guidance

---

## Section 1: Executive Summary

### Total Tasks: 68
### Estimated Effort: 180-250 hours (6-8 weeks with parallelization)

| Priority | Tasks | Hours | Can Parallelize |
|----------|-------|-------|-----------------|
| P0 (Critical) | 12 | 25-35 | 8 parallel |
| P1 (High) | 18 | 50-70 | 12 parallel |
| P2 (Medium) | 24 | 60-85 | 16 parallel |
| P3 (Low) | 14 | 45-60 | 10 parallel |

---

## Section 2: Dependency Graph Overview

```
WAVE 1 (P0 - No Dependencies)
├── T-001: Remove mocks from test_compose_all_paths.py
├── T-002: Remove mocks from test_cli_output.py
├── T-003: Remove mocks from test_cli_workflow.py
├── T-004: Remove mocks from test_session_config_paths.py
├── T-005: Delete session dual layout code
├── T-006: Delete compatibility shim modules
├── T-007: Add config section for file locking
├── T-008: Add config section for session limits
└── T-009: Create QA manager.py

WAVE 2 (P1 - Depends on Wave 1)
├── T-010: Consolidate JSON I/O utilities ──────────┐
├── T-011: Consolidate YAML I/O utilities ──────────┤
├── T-012: Consolidate timestamp utilities ─────────┤──► T-030
├── T-013: Consolidate repo root detection ─────────┤
├── T-014: Create ensure_dir utility ───────────────┘
├── T-015: Remove deprecated SessionNamingStrategy
├── T-016: Delete legacy fallback code
├── T-017: Fix retry logic to use config
├── T-018: Fix DRY detection constants
└── T-019: Remove 4 remaining mock files

WAVE 3 (P2 - Depends on Wave 2)
├── T-020: Update all JSON I/O call sites ─────┐
├── T-021: Update all YAML I/O call sites ─────┤──► T-040
├── T-022: Update all mkdir call sites ────────┤
├── T-023: Update all timestamp call sites ────┘
├── T-024: Rename conflicting discovery.py files
├── T-025: Rename conflicting metadata.py files
├── T-026: Add config for include depth
├── T-027: Add config for text processing
├── T-028: Fix environment variable bypass
└── T-029: Remove duplicate function implementations

WAVE 4 (P2 - God File Splitting)
├── T-030: Split qa/evidence.py (720 LOC)
├── T-031: Split composition/packs.py (604 LOC)
├── T-032: Split session/store.py (585 LOC)
├── T-033: Split adapters/sync/zen.py (581 LOC)
├── T-034: Split session/worktree.py (538 LOC)
└── T-035: Split composition/composers.py (532 LOC)

WAVE 5 (P2 - More God Files)
├── T-036: Split qa/validator.py (525 LOC)
├── T-037: Split paths/resolver.py (518 LOC)
├── T-038: Split setup/questionnaire.py (512 LOC)
├── T-039: Split config.py (507 LOC)
└── T-040: Split session/next/compute.py (490 LOC)

WAVE 6 (P3 - Dependency Injection)
├── T-041: Create IConfigProvider interface
├── T-042: Create ConfigFactory
├── T-043: Update 28 ConfigManager sites
├── T-044: Remove 16 global variables
└── T-045: Add context objects for state

WAVE 7 (P3 - Remaining God Files)
├── T-046: Split rules/engine.py (474 LOC)
├── T-047: Split adapters/sync/claude.py (473 LOC)
├── T-048: Split adapters/sync/cursor.py (469 LOC)
├── T-049: Split session/recovery.py (419 LOC)
├── T-050: Split composition/guidelines.py (393 LOC)
└── T-051: Split composition/orchestrator.py (393 LOC)

WAVE 8 (P3 - Final Cleanup)
├── T-052 to T-068: Remaining small tasks
└── Final validation and documentation
```

---

## Section 3: Wave 1 Tasks (P0 - Critical, No Dependencies)

### T-001: Remove mocks from test_compose_all_paths.py
- **Priority:** P0 (CRITICAL)
- **Rule:** #2 (NO MOCKS)
- **Audit:** Audit 3
- **Dependencies:** None
- **Effort:** 2-3 hours
- **File:** `tests/cli/test_compose_all_paths.py`

**Description:**
Remove CompositionEngine mocking and test with real engine using tmp_path isolation.

**Validation Criteria:**
- [ ] No `Mock`, `MagicMock`, `@patch`, or `mocker` in file
- [ ] Tests pass with real CompositionEngine
- [ ] Uses tmp_path for file isolation
- [ ] `pytest tests/cli/test_compose_all_paths.py -v` passes

**Implementation Steps:**
1. Read current test file
2. Identify what's being mocked
3. Create real test fixtures using tmp_path
4. Remove mock imports and decorators
5. Update test to use real CompositionEngine
6. Run tests and verify

---

### T-002: Remove mocks from test_cli_output.py
- **Priority:** P0 (CRITICAL)
- **Rule:** #2 (NO MOCKS)
- **Audit:** Audit 3
- **Dependencies:** None
- **Effort:** 3-4 hours
- **File:** `tests/unit/utils/test_cli_output.py`

**Description:**
Replace stdin/stderr mocking with real StringIO objects.

**Validation Criteria:**
- [ ] No mock imports in file
- [ ] Uses StringIO for stdin/stderr testing
- [ ] All tests pass
- [ ] `grep -c "Mock\|patch" tests/unit/utils/test_cli_output.py` returns 0

---

### T-003: Remove mocks from test_cli_workflow.py
- **Priority:** P0 (CRITICAL)
- **Rule:** #2 (NO MOCKS)
- **Audit:** Audit 3
- **Dependencies:** None
- **Effort:** 2-3 hours
- **File:** `tests/e2e/framework/test_cli_workflow.py`

**Description:**
Replace process detection mocking with dependency injection pattern.

**Validation Criteria:**
- [ ] No mock imports in file
- [ ] Process detection uses DI or real implementation
- [ ] All tests pass

---

### T-004: Remove mocks from test_session_config_paths.py
- **Priority:** P0 (CRITICAL)
- **Rule:** #2 (NO MOCKS)
- **Audit:** Audit 3
- **Dependencies:** None
- **Effort:** 1-2 hours
- **File:** `tests/session/test_session_config_paths.py`

**Description:**
Replace path resolution mocking with real environment setup.

**Validation Criteria:**
- [ ] No mock imports in file
- [ ] Uses real environment/tmp_path
- [ ] All tests pass

---

### T-005: Delete session dual layout code
- **Priority:** P0 (CRITICAL)
- **Rule:** #3 (NO LEGACY)
- **Audit:** Audit 5
- **Dependencies:** None
- **Effort:** 4-6 hours
- **Files:** `session/store.py`, `session/manager.py`, `session/transaction.py`

**Description:**
Remove the legacy flat file session layout that causes 2x I/O overhead. Keep only hierarchical layout.

**Validation Criteria:**
- [ ] No `_write_legacy_layout` or similar functions
- [ ] No dual write paths
- [ ] Session I/O reduced by ~50%
- [ ] All session tests pass
- [ ] `grep -rn "legacy.*layout\|flat.*layout\|dual.*write" src/edison/core/session` returns nothing

**Implementation Steps:**
1. Identify all dual layout code in session module
2. Write characterization tests for current behavior
3. Remove legacy layout functions
4. Update any code that reads legacy format
5. Run all session tests

---

### T-006: Delete compatibility shim modules
- **Priority:** P0 (CRITICAL)
- **Rule:** #3 (NO LEGACY)
- **Audit:** Audit 5
- **Dependencies:** None
- **Effort:** 2-3 hours
- **Files:** `core/__init__.py`, `utils/__init__.py`, `composition/__init__.py`

**Description:**
Remove backward-compatible import re-exports that maintain legacy paths.

**Validation Criteria:**
- [ ] No `# backward compat` or `# legacy` comments
- [ ] No re-exports for old import paths
- [ ] All imports updated to use new paths
- [ ] All tests pass

---

### T-007: Add config section for file locking
- **Priority:** P0 (CRITICAL)
- **Rule:** #4 (NO HARDCODED)
- **Audit:** Audit 2
- **Dependencies:** None
- **Effort:** 1 hour
- **Files:** `src/edison/data/config/defaults.yaml`, `src/edison/core/file_io/locking.py`

**Description:**
Move hardcoded timeout=10.0, poll_interval=0.1 to YAML config.

**Validation Criteria:**
- [ ] `defaults.yaml` has `file_locking:` section
- [ ] `locking.py` reads from config
- [ ] No hardcoded timeout/poll values in locking.py
- [ ] Tests pass with config values

**Config Addition:**
```yaml
file_locking:
  timeout_seconds: 10.0
  poll_interval_seconds: 0.1
  fail_open: false
```

---

### T-008: Add config section for session limits
- **Priority:** P0 (CRITICAL)
- **Rule:** #4 (NO HARDCODED)
- **Audit:** Audit 2
- **Dependencies:** None
- **Effort:** 30 minutes
- **Files:** `src/edison/data/config/defaults.yaml`, `src/edison/core/session/store.py`

**Description:**
Move hardcoded session ID limit (64 chars) to config.

**Validation Criteria:**
- [ ] Config has `session.id_max_length: 64`
- [ ] store.py reads from config
- [ ] Tests pass

---

### T-009: Create QA manager.py
- **Priority:** P0 (CRITICAL)
- **Rule:** #12 (COHERENCE)
- **Audit:** Audit 5
- **Dependencies:** None
- **Effort:** 2 hours
- **File:** `src/edison/core/qa/manager.py` (NEW)

**Description:**
Create QAManager class following same pattern as SessionManager and TaskManager for module coherence.

**Validation Criteria:**
- [ ] `qa/manager.py` exists
- [ ] QAManager class follows same interface as SessionManager/TaskManager
- [ ] Basic CRUD operations implemented
- [ ] Tests created in `tests/qa/test_qa_manager.py`
- [ ] Module structure matches session/task modules

---

## Section 4: Wave 2 Tasks (P1 - High, Depends on Wave 1)

### T-010: Consolidate JSON I/O utilities
- **Priority:** P1 (HIGH)
- **Rule:** #6 (DRY)
- **Audit:** Audit 1
- **Dependencies:** T-005 (session dual layout must be removed first)
- **Effort:** 4-5 hours
- **Files:** `utils/json_io.py`, `file_io/utils.py`

**Description:**
Consolidate all JSON read/write into single utility module. Currently 36 direct json.load/dump calls bypass centralized utilities.

**Validation Criteria:**
- [ ] Single canonical location for JSON I/O: `file_io/utils.py`
- [ ] `read_json_safe()` and `write_json_safe()` are the only JSON I/O functions
- [ ] No direct `json.load()`/`json.dump()` in production code
- [ ] `grep -rn "json\.load\|json\.dump" src/edison/core --include="*.py" | grep -v file_io` returns nothing

---

### T-011: Consolidate YAML I/O utilities
- **Priority:** P1 (HIGH)
- **Rule:** #6 (DRY)
- **Audit:** Audit 1
- **Dependencies:** T-007 (config must be in place)
- **Effort:** 3-4 hours
- **File:** `file_io/utils.py`

**Description:**
Ensure all YAML reads use `read_yaml_safe()`. Currently 18 direct `yaml.safe_load()` calls.

**Validation Criteria:**
- [ ] All YAML reads use `read_yaml_safe()`
- [ ] Consistent error handling
- [ ] `grep -rn "yaml\.safe_load" src/edison/core | grep -v file_io/utils.py` shows only legitimate exceptions

---

### T-012: Consolidate timestamp utilities
- **Priority:** P1 (HIGH)
- **Rule:** #6 (DRY)
- **Audit:** Audit 1
- **Dependencies:** None
- **Effort:** 2 hours
- **Files:** Multiple files with `utc_timestamp()`, `_now_iso()`

**Description:**
Consolidate 3 duplicate timestamp functions into single utility.

**Validation Criteria:**
- [ ] Single `utc_timestamp()` in `file_io/utils.py`
- [ ] All other implementations removed
- [ ] All call sites updated
- [ ] `grep -rn "def utc_timestamp\|def _now_iso" src/edison/core` shows only 1 result

---

### T-013: Consolidate repo root detection
- **Priority:** P1 (HIGH)
- **Rule:** #6 (DRY)
- **Audit:** Audit 1
- **Dependencies:** None
- **Effort:** 3-4 hours
- **Files:** Multiple files with `_repo_root()`, `_resolve_repo_root()`, `_detect_repo_root()`

**Description:**
7 different implementations of repo root detection must be consolidated.

**Validation Criteria:**
- [ ] Single `resolve_repo_root()` in `paths/resolver.py`
- [ ] All 7 implementations removed/redirected
- [ ] Consistent behavior across all usages
- [ ] `grep -rn "def.*repo_root\|def.*detect_repo" src/edison/core` shows only canonical location

---

### T-014: Create ensure_dir utility
- **Priority:** P1 (HIGH)
- **Rule:** #6 (DRY)
- **Audit:** Audit 1
- **Dependencies:** None
- **Effort:** 2 hours
- **File:** `file_io/utils.py`

**Description:**
Create `ensure_dir()` utility to replace 85 instances of `.mkdir(parents=True, exist_ok=True)`.

**Validation Criteria:**
- [ ] `ensure_dir(path)` function exists in `file_io/utils.py`
- [ ] Provides consistent error handling
- [ ] At least 50% of mkdir calls updated to use it

---

### T-015: Remove deprecated SessionNamingStrategy
- **Priority:** P1 (HIGH)
- **Rule:** #3 (NO LEGACY)
- **Audit:** Audit 5
- **Dependencies:** T-005 (session cleanup first)
- **Effort:** 2 hours
- **File:** `session/naming.py` or similar

**Description:**
Delete SessionNamingStrategy class that exists solely for backward compatibility.

**Validation Criteria:**
- [ ] Class removed
- [ ] No deprecated parameters remain
- [ ] All usages updated or removed
- [ ] Tests pass

---

### T-016: Delete legacy fallback code
- **Priority:** P1 (HIGH)
- **Rule:** #3 (NO LEGACY)
- **Audit:** Audit 5
- **Dependencies:** T-005, T-006
- **Effort:** 3-4 hours
- **Files:** Various files with fallback patterns

**Description:**
Remove all `try: new_way() except: old_way()` fallback patterns.

**Validation Criteria:**
- [ ] No fallback patterns in production code
- [ ] `grep -rn "fallback\|fall back" src/edison/core` returns nothing relevant
- [ ] Tests pass

---

### T-017: Fix retry logic to use config
- **Priority:** P1 (HIGH)
- **Rule:** #4 (NO HARDCODED)
- **Audit:** Audit 2
- **Dependencies:** None
- **Effort:** 2 hours
- **File:** `utils/resilience.py`

**Description:**
Config has retry settings but resilience.py uses hardcoded values. Wire them together.

**Validation Criteria:**
- [ ] `resilience.py` reads from `config.resilience.retry.*`
- [ ] No hardcoded retry values in code
- [ ] Tests verify config values are used

---

### T-018: Fix DRY detection constants
- **Priority:** P1 (HIGH)
- **Rule:** #4 (NO HARDCODED)
- **Audit:** Audit 2
- **Dependencies:** None
- **Effort:** 1 hour
- **Files:** 3 files with `EDISON_DRY_MIN_SHINGLES`

**Description:**
Consolidate duplicate constant definitions.

**Validation Criteria:**
- [ ] Single definition of constant
- [ ] All files import from one location
- [ ] `grep -rn "DRY_MIN_SHINGLES" src/edison` shows only 1 definition

---

### T-019: Remove 4 remaining mock files
- **Priority:** P1 (HIGH)
- **Rule:** #2 (NO MOCKS)
- **Audit:** Audit 3
- **Dependencies:** T-001 to T-004
- **Effort:** 2-3 hours
- **Files:** 4 LOW severity test files

**Description:**
Remove remaining mock usage from 4 edge case test files.

**Validation Criteria:**
- [ ] `grep -rn "Mock\|MagicMock\|@patch" tests/` returns 0 results
- [ ] All tests pass
- [ ] 100% mock-free compliance

---

## Section 5: Wave 3 Tasks (P2 - Medium)

### T-020: Update all JSON I/O call sites
- **Priority:** P2
- **Rule:** #6 (DRY)
- **Dependencies:** T-010
- **Effort:** 4-6 hours

**Description:**
Update all 36 direct json.load/dump calls to use centralized utilities.

**Validation Criteria:**
- [ ] No direct JSON I/O in production code
- [ ] All tests pass

---

### T-021: Update all YAML I/O call sites
- **Priority:** P2
- **Rule:** #6 (DRY)
- **Dependencies:** T-011
- **Effort:** 3-4 hours

**Description:**
Update remaining yaml.safe_load calls to use read_yaml_safe().

---

### T-022: Update all mkdir call sites
- **Priority:** P2
- **Rule:** #6 (DRY)
- **Dependencies:** T-014
- **Effort:** 4-5 hours

**Description:**
Update 85 mkdir patterns to use ensure_dir().

---

### T-023: Update all timestamp call sites
- **Priority:** P2
- **Rule:** #6 (DRY)
- **Dependencies:** T-012
- **Effort:** 2 hours

**Description:**
Update all timestamp usages to use centralized utility.

---

### T-024: Rename conflicting discovery.py files
- **Priority:** P2
- **Rule:** #12 (COHERENCE)
- **Dependencies:** None
- **Effort:** 1 hour

**Description:**
3 files named discovery.py serve different purposes. Rename for clarity.

---

### T-025: Rename conflicting metadata.py files
- **Priority:** P2
- **Rule:** #12 (COHERENCE)
- **Dependencies:** None
- **Effort:** 1 hour

**Description:**
2 files named metadata.py serve different purposes. Rename for clarity.

---

### T-026: Add config for include depth
- **Priority:** P2
- **Rule:** #4 (NO HARDCODED)
- **Dependencies:** None
- **Effort:** 30 minutes

**Description:**
Move hardcoded MAX_DEPTH=3 to config.

---

### T-027: Add config for text processing
- **Priority:** P2
- **Rule:** #4 (NO HARDCODED)
- **Dependencies:** None
- **Effort:** 30 minutes

**Description:**
Move magic numbers k=12, min_shingles=2 to config.

---

### T-028: Fix environment variable bypass
- **Priority:** P2
- **Rule:** #5 (100% CONFIGURABLE)
- **Dependencies:** None
- **Effort:** 4-6 hours

**Description:**
30+ environment variables bypass YAML config. Route through config system.

---

### T-029: Remove duplicate function implementations
- **Priority:** P2
- **Rule:** #6 (DRY)
- **Dependencies:** T-010 to T-014
- **Effort:** 3-4 hours

**Description:**
After utilities consolidated, remove remaining duplicate function bodies.

---

## Section 6: Wave 4-5 Tasks (P2 - God File Splitting)

### T-030: Split qa/evidence.py (720 LOC)
- **Priority:** P2
- **Rule:** #7 (SOLID - SRP)
- **Dependencies:** T-010, T-011 (utility consolidation)
- **Effort:** 6-8 hours
- **Target:** Split into 4 files of ~180 LOC each

**New Structure:**
```
qa/
├── evidence/
│   ├── __init__.py      # Public API
│   ├── collector.py     # Evidence collection
│   ├── validator.py     # Evidence validation
│   ├── storage.py       # Evidence persistence
│   └── reporter.py      # Evidence reporting
```

---

### T-031 to T-040: Split remaining god files
(Similar structure for each, 4-8 hours each)

- T-031: composition/packs.py (604 LOC)
- T-032: session/store.py (585 LOC)
- T-033: adapters/sync/zen.py (581 LOC)
- T-034: session/worktree.py (538 LOC)
- T-035: composition/composers.py (532 LOC)
- T-036: qa/validator.py (525 LOC)
- T-037: paths/resolver.py (518 LOC)
- T-038: setup/questionnaire.py (512 LOC)
- T-039: config.py (507 LOC)
- T-040: session/next/compute.py (490 LOC)

---

## Section 7: Wave 6 Tasks (P3 - Dependency Injection)

### T-041: Create IConfigProvider interface
- **Priority:** P3
- **Rule:** #7 (SOLID - DIP)
- **Dependencies:** T-039 (config.py split)
- **Effort:** 2 hours

**Description:**
Create abstract interface for config provision to enable DI.

---

### T-042: Create ConfigFactory
- **Priority:** P3
- **Rule:** #7 (SOLID - DIP)
- **Dependencies:** T-041
- **Effort:** 2 hours

**Description:**
Factory for creating config instances with proper DI support.

---

### T-043: Update 28 ConfigManager sites
- **Priority:** P3
- **Rule:** #7 (SOLID - DIP)
- **Dependencies:** T-042
- **Effort:** 8-10 hours

**Description:**
Replace all direct ConfigManager instantiation with factory/DI.

---

### T-044: Remove 16 global variables
- **Priority:** P3
- **Rule:** #7 (SOLID)
- **Dependencies:** T-043
- **Effort:** 6-8 hours

**Description:**
Replace global state with context objects or DI.

---

### T-045: Add context objects for state
- **Priority:** P3
- **Rule:** #7 (SOLID)
- **Dependencies:** T-044
- **Effort:** 4-6 hours

**Description:**
Create proper context objects to replace global state.

---

## Section 8: Wave 7-8 Tasks (P3 - Remaining)

### T-046 to T-051: Remaining God Files
(4-6 hours each)

- T-046: rules/engine.py (474 LOC)
- T-047: adapters/sync/claude.py (473 LOC)
- T-048: adapters/sync/cursor.py (469 LOC)
- T-049: session/recovery.py (419 LOC)
- T-050: composition/guidelines.py (393 LOC)
- T-051: composition/orchestrator.py (393 LOC)

### T-052 to T-068: Final Cleanup Tasks
- T-052: Split composition/formatting.py (389 LOC)
- T-053: Split ide/commands.py (365 LOC)
- T-054: Split task/io.py (359 LOC)
- T-055: Split rules/registry.py (355 LOC)
- T-056: Split utils/subprocess.py (354 LOC)
- T-057: Split task/metadata.py (334 LOC)
- T-058: Split orchestrator/launcher.py (334 LOC)
- T-059: Split ide/hooks.py (308 LOC)
- T-060: Split composition/agents.py (304 LOC)
- T-061: Final mock removal verification
- T-062: Final legacy code verification
- T-063: Final config compliance verification
- T-064: Final DRY compliance verification
- T-065: Final SOLID compliance verification
- T-066: Update all documentation
- T-067: Run full test suite
- T-068: Generate final compliance report

---

## Section 9: Validation Gates

### Gate 1: After Wave 1 (P0 Complete)
```bash
# Must all pass before proceeding to Wave 2
grep -rn "Mock\|MagicMock\|@patch" tests/cli/test_compose_all_paths.py  # 0 results
grep -rn "legacy.*layout" src/edison/core/session  # 0 results
pytest tests/session/ -v  # All pass
pytest tests/qa/ -v  # All pass
```

### Gate 2: After Wave 2 (P1 Complete)
```bash
# Must all pass before proceeding to Wave 3
grep -rn "Mock\|MagicMock\|@patch" tests/  # 0 results
grep -rn "json\.load\|json\.dump" src/edison/core | grep -v file_io  # 0 relevant
grep -rn "def utc_timestamp" src/edison/core  # Only 1 result
pytest tests/ -v  # All pass
```

### Gate 3: Final Validation
```bash
# Full compliance verification
find src/edison -name "*.py" -exec wc -l {} \; | awk '$1 > 300'  # <5 files
grep -rn "Mock\|MagicMock\|@patch" tests/  # 0 results
grep -rn "legacy\|deprecated" src/edison/core  # 0 results (except legacy_guard.py)
grep -rn "= [0-9][0-9][0-9]" src/edison/core  # Minimal hardcoded values
pytest tests/ -v --tb=short  # All pass
```

---

## Section 10: Parallelization Guide

### Maximum Parallelization by Wave

**Wave 1 (8 parallel streams):**
```
Stream A: T-001 (mocks)
Stream B: T-002 (mocks)
Stream C: T-003 (mocks)
Stream D: T-004 (mocks)
Stream E: T-005 (session legacy)
Stream F: T-006 (compat shims)
Stream G: T-007, T-008 (config)
Stream H: T-009 (QA manager)
```

**Wave 2 (6 parallel streams):**
```
Stream A: T-010 (JSON)
Stream B: T-011 (YAML)
Stream C: T-012, T-013 (timestamps, repo root)
Stream D: T-014 (ensure_dir)
Stream E: T-015, T-016 (legacy removal)
Stream F: T-017, T-018, T-019 (config/mocks)
```

**Wave 3 (5 parallel streams):**
```
Stream A: T-020, T-021 (I/O call sites)
Stream B: T-022, T-023 (mkdir, timestamps)
Stream C: T-024, T-025 (renames)
Stream D: T-026, T-027, T-028 (config)
Stream E: T-029 (duplicates)
```

**Wave 4-5 (5 parallel streams):**
```
Stream A: T-030, T-036 (qa/ files)
Stream B: T-031, T-035 (composition/ files)
Stream C: T-032, T-040 (session/ files)
Stream D: T-033, T-047, T-048 (adapters/)
Stream E: T-034, T-037, T-038, T-039 (misc)
```

---

## Section 11: Task Status Tracker

### 11.1 Wave 1 Status (P0 - Critical)

| ID | Task | Status | Deps Met | Assigned | Notes |
|----|------|--------|----------|----------|-------|
| T-001 | Remove mocks test_compose_all_paths.py | ⬜ TODO | ✅ | - | - |
| T-002 | Remove mocks test_cli_output.py | ⬜ TODO | ✅ | - | - |
| T-003 | Remove mocks test_cli_workflow.py | ⬜ TODO | ✅ | - | - |
| T-004 | Remove mocks test_session_config_paths.py | ⬜ TODO | ✅ | - | - |
| T-005 | Delete session dual layout | ⬜ TODO | ✅ | - | - |
| T-006 | Delete compatibility shims | ⬜ TODO | ✅ | - | - |
| T-007 | Add file locking config | ⬜ TODO | ✅ | - | - |
| T-008 | Add session limits config | ⬜ TODO | ✅ | - | - |
| T-009 | Create QA manager.py | ⬜ TODO | ✅ | - | - |

### 11.2 Wave 2 Status (P1 - High)

| ID | Task | Status | Deps Met | Assigned | Notes |
|----|------|--------|----------|----------|-------|
| T-010 | Consolidate JSON I/O | ⬜ TODO | ⏳ T-005 | - | - |
| T-011 | Consolidate YAML I/O | ⬜ TODO | ⏳ T-007 | - | - |
| T-012 | Consolidate timestamps | ⬜ TODO | ✅ | - | - |
| T-013 | Consolidate repo root | ⬜ TODO | ✅ | - | - |
| T-014 | Create ensure_dir | ⬜ TODO | ✅ | - | - |
| T-015 | Remove SessionNamingStrategy | ⬜ TODO | ⏳ T-005 | - | - |
| T-016 | Delete legacy fallback | ⬜ TODO | ⏳ T-005,T-006 | - | - |
| T-017 | Fix retry config | ⬜ TODO | ✅ | - | - |
| T-018 | Fix DRY constants | ⬜ TODO | ✅ | - | - |
| T-019 | Remove 4 remaining mocks | ⬜ TODO | ⏳ T-001-004 | - | - |

### 11.3 Wave 3 Status (P2 - Medium)

| ID | Task | Status | Deps Met | Assigned | Notes |
|----|------|--------|----------|----------|-------|
| T-020 | Update JSON call sites | ⬜ TODO | ⏳ T-010 | - | - |
| T-021 | Update YAML call sites | ⬜ TODO | ⏳ T-011 | - | - |
| T-022 | Update mkdir call sites | ⬜ TODO | ⏳ T-014 | - | - |
| T-023 | Update timestamp sites | ⬜ TODO | ⏳ T-012 | - | - |
| T-024 | Rename discovery.py files | ⬜ TODO | ✅ | - | - |
| T-025 | Rename metadata.py files | ⬜ TODO | ✅ | - | - |
| T-026 | Add include depth config | ⬜ TODO | ✅ | - | - |
| T-027 | Add text processing config | ⬜ TODO | ✅ | - | - |
| T-028 | Fix env var bypass | ⬜ TODO | ✅ | - | - |
| T-029 | Remove duplicate funcs | ⬜ TODO | ⏳ T-010-014 | - | - |

### 11.4-11.7 Wave 4-8 Status
(Same format, all ⬜ TODO, dependencies as shown in graph)

### 11.8 Summary Metrics

| Metric | Value |
|--------|-------|
| Total Tasks | 68 |
| Completed | 0 |
| In Progress | 0 |
| Blocked | 0 |
| Remaining | 68 |
| Progress | 0% |

---

## Section 12: Sub-Agent Delegation Template

When delegating a task to a sub-agent, use this format:

```
## TASK DELEGATION: [Task ID]

### Instructions for Sub-Agent

1. **Read your task** from `/audit/IMPLEMENTATION_PLAN.md` Section [X], Task [ID]
2. **Follow the 13 Critical Principles** (especially TDD, NO MOCKS, NO LEGACY)
3. **Execute the implementation steps** listed in the task
4. **Validate against ALL criteria** before reporting completion

### Your Task ID: [ID]
### Task Location: Section [X] of IMPLEMENTATION_PLAN.md

### Expected Output:
- [ ] Confirmation that all validation criteria pass
- [ ] List of files modified
- [ ] Any blockers or follow-up tasks discovered
- [ ] Test results summary

### Critical Reminders:
- TDD: Write test FIRST, then implement
- NO MOCKS: Use real implementations with tmp_path
- Run `pytest [relevant tests] -v` before reporting done
```

---

## Section 13: Quick Reference Commands

### Check Progress
```bash
# Count remaining mock usage
grep -rn "Mock\|MagicMock\|@patch" tests/ --include="*.py" | wc -l

# Count legacy markers
grep -rn "legacy\|deprecated" src/edison/core --include="*.py" | wc -l

# Count god files
find src/edison -name "*.py" -exec wc -l {} \; | awk '$1 > 300' | wc -l

# Run full test suite
pytest tests/ -v --tb=short
```

### Validation After Each Wave
```bash
# Wave 1 complete
pytest tests/session tests/qa tests/cli -v

# Wave 2 complete
pytest tests/ -v --ignore=tests/e2e/framework/e2e

# All waves complete
pytest tests/ -v
```

---

**Document Version:** 1.0
**Created:** 2025-11-26
**Last Updated:** 2025-11-26
**Total Tasks:** 68
**Estimated Effort:** 180-250 hours
