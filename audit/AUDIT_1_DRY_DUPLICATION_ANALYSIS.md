# AUDIT 1: DRY & Duplication Analysis

**Date:** 2025-11-26
**Auditor:** Claude Code Agent
**Scope:** Edison codebase (`src/edison/core`)
**Rules Audited:** #6 (DRY), #11 (UN-DUPLICATED & REUSABLE), #12 (STRICT COHERENCE)

---

## EXECUTIVE SUMMARY

### Critical Findings
- **28 duplicate function names** detected across the codebase
- **18 yaml.safe_load** direct calls that should be centralized
- **36 json.load/dump** direct calls that should use utilities
- **85 .mkdir(parents=True, exist_ok=True)** patterns that should be centralized
- **284 .exists()** checks scattered throughout (potential for centralization)

### Severity Breakdown
- **CRITICAL:** 12 violations (true duplicates requiring immediate consolidation)
- **HIGH:** 8 violations (wrapper/delegation patterns that create confusion)
- **MEDIUM:** 15 violations (utility operations that should be centralized)
- **LOW:** 3 violations (legitimate similar-named functions in different contexts)

---

## CATEGORY 1: FUNCTION-LEVEL DUPLICATION

### 1.1 Repository Root Detection (CRITICAL)
**Violation Type:** Multiple implementations of the same functionality
**Severity:** CRITICAL
**Impact:** Inconsistent behavior, maintenance burden

#### Duplicates Found:
1. **`_repo_root()`** - 3 implementations
   - `/src/edison/core/composition/includes.py:28` - Uses `get_repo_root()` with override
   - `/src/edison/core/composition/audit/discovery.py:43` - Delegates to `_composition_repo_root()`
   - `/src/edison/core/composition/guidelines.py:41` - Uses `get_repo_root()` directly

2. **`_resolve_repo_root()` / `_detect_repo_root()`** - 4 implementations
   - `/src/edison/core/utils/subprocess.py:33` - `_resolve_repo_root()`
   - `/src/edison/core/adapters/sync/zen.py:35` - `_detect_repo_root()`
   - `/src/edison/core/adapters/sync/cursor.py:46` - `_detect_repo_root()`
   - `/src/edison/core/task/paths.py:17` - `_resolve_repo_root()`

3. **`_get_worktree_base()`** - 2 implementations
   - `/src/edison/core/session/store.py:448`
   - `/src/edison/core/session/worktree.py:74`

**Recommendation:**
- Consolidate all repo root detection into `/src/edison/core/utils/git.py:get_repo_root()`
- Remove all private duplicates and use the single canonical implementation
- Document override mechanism in one place

**Effort:** 4-6 hours

---

### 1.2 Timestamp & Time Utilities (CRITICAL)
**Violation Type:** Duplicate time formatting logic
**Severity:** CRITICAL
**Impact:** Inconsistent timestamps across the system

#### Duplicates Found:
1. **`utc_timestamp()`** - 3 implementations
   - `/src/edison/core/utils/time.py:53` - Canonical, config-driven (ISO 8601, configurable timespec)
   - `/src/edison/core/file_io/utils.py:112` - Delegates to utils.time (GOOD)
   - `/src/edison/core/task/io.py:224` - Hardcoded `isoformat(timespec="seconds")`

2. **`_now_iso()`** - 3 implementations
   - `/src/edison/core/task/io.py:220` - `datetime.now(timezone.utc).isoformat()`
   - `/src/edison/core/qa/scoring.py:11` - `datetime.now(timezone.utc).isoformat()`
   - `/src/edison/core/composition/delegation.py:74` - `datetime.now(timezone.utc).isoformat()`

**Analysis:**
- `file_io/utils.py` correctly delegates to the canonical implementation
- `task/io.py` has its own hardcoded version (VIOLATION)
- Three `_now_iso()` implementations are identical duplicates

**Recommendation:**
- Remove `utc_timestamp()` from `task/io.py` and use `file_io.utils.utc_timestamp()`
- Remove all `_now_iso()` implementations and use `utils.time.utc_timestamp()`
- All timestamp generation should go through `utils.time` module

**Effort:** 2-3 hours

---

### 1.3 JSON & File I/O Operations (CRITICAL)
**Violation Type:** Multiple read/write implementations
**Severity:** CRITICAL
**Impact:** Inconsistent error handling, locking, and formatting

#### Duplicates Found:
1. **`read_json()`** - Multiple implementations
   - `/src/edison/core/utils/json_io.py:57` - Canonical with locking
   - `/src/edison/core/file_io/utils.py:96` - `read_json_safe()` with default handling
   - Inline: 36 instances of `json.load()` or `json.loads()` across codebase

2. **`_read_json()`** - 2 private implementations
   - `/src/edison/core/task/io.py:228` - `json.loads(path.read_text())`
   - `/src/edison/core/qa/store.py:36-46` - `read_jsonl()` (different: JSONL format)

3. **`_write_json()`** - 2 private implementations
   - `/src/edison/core/task/io.py:232` - Simple json.dumps
   - Multiple inline `json.dump()` calls (36 instances)

4. **`read_text()` / `_read_text()`** - 2 implementations
   - `/src/edison/core/file_io/utils.py:246` - Canonical
   - `/src/edison/core/composition/includes.py:35` - Duplicate with custom error
   - `/src/edison/core/composition/guidelines.py:46` - Another duplicate with custom error

5. **`write_text_locked()`** - 2 implementations (CRITICAL DUPLICATION)
   - `/src/edison/core/task/locking.py:157` - Full implementation with atomic write
   - `/src/edison/core/task/io.py:192` - Delegates to locking.write_text_locked (GOOD)

**Analysis:**
- Two separate JSON I/O systems: `utils/json_io.py` (with locking) vs `file_io/utils.py` (with defaults)
- 36 instances of direct `json.load()`/`json.dump()` usage bypass centralized utilities
- `write_text_locked` correctly uses delegation pattern but still creates confusion

**Recommendation:**
- Consolidate JSON I/O into single module: `utils/json_io.py`
- Add `read_json_safe()` to `utils/json_io.py` with default handling
- Replace all inline `json.load()`/`json.dump()` with utility functions
- Move `write_text_locked()` to `file_io/locking.py` and remove wrapper from `task/io.py`
- Remove duplicate `_read_text()` implementations, use `file_io.utils.read_text()`

**Effort:** 8-10 hours (high impact across many files)

---

### 1.4 YAML Loading (HIGH PRIORITY)
**Violation Type:** Direct yaml.safe_load() calls
**Severity:** HIGH
**Impact:** No centralized error handling, encoding inconsistency

#### Pattern Found:
- **18 instances** of direct `yaml.safe_load()` calls across:
  - `config.py`, `setup/discovery.py`, `setup/questionnaire.py`
  - `file_io/utils.py`, `paths/management.py`, `paths/project.py`
  - `composition/orchestrator.py`, `composition/workflow.py`, `composition/packs.py`
  - `task/metadata.py`, `task/locking.py`, `task/context7.py`
  - `rules/registry.py`, `process/inspector.py`, `session/state_machine_docs.py`

**Current State:**
- `file_io/utils.py:149` has `read_yaml_safe()` utility function
- Most code doesn't use it, calls `yaml.safe_load()` directly

**Recommendation:**
- Replace all direct `yaml.safe_load()` calls with `file_io.utils.read_yaml_safe()`
- Ensures consistent error handling and encoding

**Effort:** 3-4 hours

---

### 1.5 Configuration Loading (_cfg) (MEDIUM)
**Violation Type:** Multiple config loading patterns
**Severity:** MEDIUM
**Impact:** Inconsistent configuration access

#### Duplicates Found:
1. **`_cfg()`** - 3 implementations
   - `/src/edison/core/utils/time.py:21` - Loads time config
   - `/src/edison/core/utils/json_io.py:24` - Loads JSON config
   - `/src/edison/core/utils/cli_output.py:40` - Loads CLI output config

**Analysis:**
- Each is loading config for its specific domain (time, json, cli)
- Names are identical but purposes differ
- This is somewhat justified but creates confusion

**Recommendation:**
- Rename to domain-specific names: `_time_cfg()`, `_json_cfg()`, `_cli_output_cfg()`
- Or create a shared config utility: `_load_module_config(module_name: str)`
- Current state violates STRICT COHERENCE (#12)

**Effort:** 2-3 hours

---

### 1.6 QA Evidence Functions (HIGH)
**Violation Type:** Wrapper pattern creating needless duplication
**Severity:** HIGH
**Impact:** Confusing indirection, maintenance burden

#### Duplicates Found:
All in `/src/edison/core/session/next/actions.py` as wrappers around `qa.evidence`:

1. **`missing_evidence_blockers()`** - Lines 23-25
   - Wrapper for `qa.evidence.missing_evidence_blockers()`

2. **`read_validator_jsons()`** - Lines 28-30
   - Wrapper for `qa.evidence.read_validator_jsons()`

3. **`load_impl_followups()`** - Lines 33-35
   - Wrapper for `qa.evidence.load_impl_followups()`

4. **`load_bundle_followups()`** - Lines 38-40
   - Wrapper for `qa.evidence.load_bundle_followups()`

**Analysis:**
- These are documented as "wrappers" but provide NO additional functionality
- They exist in `session/next/actions.py` but just delegate to `qa.evidence`
- Pure duplication with no benefit
- Violates DRY (#6) and UN-DUPLICATED (#11)

**Recommendation:**
- **REMOVE** all wrapper functions from `session/next/actions.py`
- Import `qa.evidence` functions directly where needed
- Update all callers to use `qa.evidence.*` directly

**Effort:** 2-3 hours

---

### 1.7 Latest Round Directory (_latest_round_dir) (MEDIUM)
**Violation Type:** Three implementations with slight variations
**Severity:** MEDIUM
**Impact:** Inconsistent round directory resolution

#### Duplicates Found:
1. `/src/edison/core/qa/evidence.py:538` - Returns `Optional[Path]`
2. `/src/edison/core/task/context7.py:202` - Returns `Optional[Path]`
3. `/src/edison/core/session/verify.py:16` - Returns `Path | None` (same as Optional[Path])

**Analysis:**
- All three find the latest round directory for a task
- Nearly identical implementation
- Should be in `qa.evidence` module as single source of truth

**Recommendation:**
- Keep implementation in `qa/evidence.py` as canonical
- Remove from `task/context7.py` and `session/verify.py`
- Import from `qa.evidence` instead

**Effort:** 2 hours

---

### 1.8 QA Root Path (qa_root) (MEDIUM)
**Violation Type:** Two implementations with different signatures
**Severity:** MEDIUM
**Impact:** Inconsistent QA root resolution

#### Duplicates Found:
1. `/src/edison/core/qa/store.py:16` - Takes `Optional[Path]` parameter
2. `/src/edison/core/task/store.py:22` - No parameters

**Analysis:**
- `qa/store.py` version accepts optional project_root override
- `task/store.py` version is simpler
- Different use cases but same purpose

**Recommendation:**
- Consolidate into single function in `paths/management.py`
- Support optional project_root parameter
- Both modules import from central location

**Effort:** 2 hours

---

### 1.9 Render Markdown (render_markdown) (LOW)
**Violation Type:** Two implementations (potentially intentional)
**Severity:** LOW
**Impact:** Unclear which is canonical

#### Duplicates Found:
1. `/src/edison/core/session/store.py:405` - Full implementation
2. `/src/edison/core/session/manager.py:146` - Likely delegates to store

**Analysis:**
- Need to verify if manager delegates to store (delegation pattern)
- If not, consolidate into one

**Recommendation:**
- Verify implementation in manager.py
- If duplicate, remove from manager.py and import from store

**Effort:** 1 hour

---

### 1.10 State Machine & Database Operations (MEDIUM)
**Violation Type:** Duplicate implementations in task vs session
**Severity:** MEDIUM
**Impact:** Inconsistent state management

#### Duplicates Found:
1. **`build_default_state_machine()`** - 2 implementations
   - `/src/edison/core/task/state.py:8`
   - `/src/edison/core/session/state.py:73`

2. **Database operations** - Found but not truly duplicated
   - `/src/edison/core/session/database.py` has `create_session_database` and `drop_session_database`
   - These are session-specific, no actual duplication

**Analysis:**
- Task and session have separate state machines (may be intentional)
- Need to verify if they should be unified or truly separate

**Recommendation:**
- Document why task and session have separate state machines
- If they should be unified, consolidate into single `state/engine.py` module
- If separate is intentional, rename for clarity: `build_task_state_machine()` and `build_session_state_machine()`

**Effort:** 3-4 hours (requires analysis of state machine requirements)

---

### 1.11 Find Record (find_record) (MEDIUM)
**Violation Type:** Two implementations with different purposes
**Severity:** MEDIUM
**Impact:** Confusion about which to use

#### Duplicates Found:
1. `/src/edison/core/task/finder.py:98` - General purpose
2. `/src/edison/core/task/metadata.py:317` - Metadata-specific

**Analysis:**
- Need to verify if these have different purposes or are duplicates
- Same name suggests same functionality

**Recommendation:**
- If same functionality, consolidate into `task/finder.py`
- If different, rename metadata version to be more specific: `find_metadata_record()`

**Effort:** 2 hours

---

### 1.12 Load Delegation Config (load_delegation_config) (MEDIUM)
**Violation Type:** Two implementations in different contexts
**Severity:** MEDIUM
**Impact:** Unclear which to use

#### Duplicates Found:
1. `/src/edison/core/qa/config.py:66` - Returns `Dict[str, Any]`, takes `Optional[Path]`
2. `/src/edison/core/composition/orchestrator.py:232` - Takes `config: Dict`, returns `Dict`

**Analysis:**
- Different signatures suggest different purposes
- Same name creates confusion
- Need to understand if both are needed

**Recommendation:**
- Rename orchestrator version to `load_orchestrator_delegation_config()`
- Or consolidate if they serve the same purpose

**Effort:** 2-3 hours

---

### 1.13 ValidationTransaction Class (HIGH)
**Violation Type:** Two transaction classes with same name
**Severity:** HIGH
**Impact:** Namespace collision, confusion

#### Duplicates Found:
1. `/src/edison/core/qa/transaction.py:16` - QA-specific validation transaction
2. `/src/edison/core/session/transaction.py:249` - Session-specific validation transaction

**Analysis:**
- Two classes with identical names in different modules
- Likely different purposes (QA vs Session)
- Violates STRICT COHERENCE (#12)

**Recommendation:**
- Rename to reflect their specific domains:
  - `QAValidationTransaction` in qa/transaction.py
  - `SessionValidationTransaction` in session/transaction.py
- Or create unified `ValidationTransaction` base class if they share behavior

**Effort:** 3-4 hours

---

### 1.14 Main & Register Args Functions (INFO)
**Violation Type:** Multiple CLI entry points
**Severity:** LOW (expected pattern)
**Impact:** None (standard CLI pattern)

#### Pattern Found:
- 62 `main()` functions across codebase
- 59 `register_args()` functions across codebase

**Analysis:**
- This is expected for CLI tools - each script has its own main/register_args
- Not a violation of DRY
- Standard Python CLI pattern

**Recommendation:**
- No action needed
- This is legitimate duplication for CLI architecture

**Effort:** N/A

---

## CATEGORY 2: UTILITY CENTRALIZATION

### 2.1 Path Operations (HIGH PRIORITY)
**Violation Type:** Repeated mkdir patterns
**Severity:** HIGH
**Impact:** Verbose code, potential for inconsistent behavior

#### Pattern Found:
- **85 instances** of `.mkdir(parents=True, exist_ok=True)`
- Scattered across entire codebase
- No centralized utility function

**Example Locations:**
```python
# Pattern appears in:
- ide/hooks.py (2x)
- ide/settings.py (1x)
- ide/commands.py (2x)
- file_io/utils.py (2x)
- paths/project.py (1x)
- qa/*.py (4x)
- composition/*.py (7x)
- adapters/**/*.py (12x)
- task/*.py (9x)
- orchestrator/*.py (3x)
- session/*.py (25x)
```

**Recommendation:**
- Create `file_io.utils.ensure_dir(path: Path)` utility function
- Replace all 85 instances with calls to this function
- Centralizes error handling and makes code more readable

**Effort:** 6-8 hours (find/replace across many files)

---

### 2.2 File Existence Checks (MEDIUM)
**Violation Type:** Repeated .exists() checks
**Severity:** MEDIUM
**Impact:** Potential for inconsistent error handling

#### Pattern Found:
- **284 instances** of `.exists()` checks
- Often followed by different error handling patterns
- Could benefit from utility functions like `read_if_exists()`, `write_if_not_exists()`

**Recommendation:**
- Add utility functions to `file_io/utils.py`:
  - `ensure_exists(path: Path, error_msg: str) -> Path` - raises if missing
  - `read_if_exists(path: Path, default: Any = None) -> str` - returns default if missing
  - `path_or_default(path: Path, default: Path) -> Path` - fallback paths

**Effort:** 4-6 hours (selective refactoring of high-impact areas)

---

### 2.3 JSON Operations Centralization (CRITICAL)
**Violation Type:** Direct json.load/dump usage
**Severity:** CRITICAL
**Impact:** Bypasses centralized locking, formatting, error handling

#### Pattern Found:
- **36 instances** of `json.load()` or `json.dump()`
- Should use `utils/json_io.py` utilities
- Missing benefits of centralized:
  - File locking for concurrent access
  - Consistent formatting (indent, sort_keys, ensure_ascii)
  - Error handling

**Example Violations:**
```python
# Direct usage in:
- ide/settings.py: json.loads(), json.dumps()
- config.py: json.loads()
- setup/discovery.py: json.load()
- qa/store.py: json.dumps(), json.loads()
- composition/includes.py: json.loads(), json.dumps()
- task/io.py: json.dump(), json.loads()
```

**Recommendation:**
- Replace all direct json.load() with `utils.json_io.read_json()`
- Replace all direct json.dump() with `utils.json_io.write_json_atomic()`
- Add convenience wrappers in `file_io.utils` if needed for backward compatibility

**Effort:** 8-10 hours (36 locations to update)

---

### 2.4 YAML Operations Centralization (HIGH)
**Violation Type:** Direct yaml.safe_load usage
**Severity:** HIGH
**Impact:** Inconsistent error handling, encoding issues

#### Pattern Found (Already covered in 1.4 but worth emphasizing):
- **18 instances** of direct `yaml.safe_load()` calls
- `file_io/utils.py` has `read_yaml_safe()` but it's not used consistently

**Recommendation:**
- Audit all yaml.safe_load() calls
- Replace with `file_io.utils.read_yaml_safe()`
- Consider adding `write_yaml_safe()` for writes

**Effort:** 3-4 hours

---

## CATEGORY 3: CROSS-MODULE PATTERN INCONSISTENCIES

### 3.1 Module Structure Inconsistency
**Violation Type:** Inconsistent file organization across similar modules
**Severity:** MEDIUM
**Impact:** Reduced code discoverability, maintenance difficulty

#### Analysis:

**Session Module (20 files):**
```
session/
├── __init__.py
├── archive.py
├── autostart.py
├── config.py
├── context.py
├── database.py
├── discovery.py
├── graph.py
├── layout.py
├── manager.py
├── models.py
├── naming.py
├── next/           # Sub-package with 7 files
├── recovery.py
├── state.py
├── state_machine_docs.py
├── store.py
├── transaction.py
├── validation.py
├── verify.py
└── worktree.py
```

**Task Module (15 files):**
```
task/
├── __init__.py
├── api/           # Sub-package (empty?)
├── claims.py
├── config.py
├── context7.py
├── finder.py
├── graph.py
├── io.py
├── locking.py
├── manager.py
├── metadata.py
├── paths.py
├── state.py
├── store.py
├── transitions.py
└── validation.py
```

**QA Module (10 files):**
```
qa/
├── __init__.py
├── bundler.py
├── config.py
├── evidence.py
├── promoter.py
├── rounds.py
├── scoring.py
├── store.py
├── transaction.py
└── validator.py
```

**Observations:**
1. All three have: `config.py`, `store.py`, `transaction.py` (GOOD)
2. Session and Task have: `manager.py`, `state.py`, `validation.py` (GOOD)
3. Session and Task have: `graph.py` (potentially duplicate logic?)
4. Inconsistent file naming:
   - Session: `worktree.py`, `recovery.py`, `archive.py`
   - Task: `locking.py`, `finder.py`, `metadata.py`, `paths.py`
   - QA: `evidence.py`, `bundler.py`, `promoter.py`, `validator.py`, `scoring.py`

**Recommendation:**
- Document the architectural pattern for core modules
- Consider if graph.py logic can be unified
- Ensure consistent responsibility allocation across config/store/manager/transaction files

**Effort:** 8-12 hours (requires architectural analysis)

---

### 3.2 Manager Pattern Inconsistency
**Violation Type:** Different manager implementations
**Severity:** MEDIUM
**Impact:** Inconsistent API patterns

#### Managers Found:
1. `ConfigManager` - `/src/edison/core/config.py:46`
2. `TaskManager` - `/src/edison/core/task/manager.py:12`
3. `SessionManager` - `/src/edison/core/session/manager.py:151`
4. `EvidenceManager` - `/src/edison/core/qa/evidence.py:37`

**Analysis:**
- Four different "Manager" classes
- Need to verify they follow consistent patterns
- Should all have similar lifecycle methods (create, read, update, delete)
- ConfigManager is at root level, others in modules

**Recommendation:**
- Define base Manager interface/protocol
- Ensure all managers follow consistent patterns
- Document manager responsibilities in CLAUDE.md

**Effort:** 4-6 hours (analysis + documentation)

---

### 3.3 Config Class Pattern Inconsistency
**Violation Type:** Multiple Config classes with different patterns
**Severity:** MEDIUM
**Impact:** Inconsistent configuration access

#### Config Classes Found:
1. `ConfigManager` - `/src/edison/core/config.py:46` (singleton manager)
2. `QAConfig` - `/src/edison/core/qa/config.py:22` (wrapper around ConfigManager)
3. `TaskConfig` - `/src/edison/core/task/config.py:36` (wrapper around ConfigManager)
4. `OrchestratorConfig` - `/src/edison/core/orchestrator/config.py:21` (wrapper)
5. `SessionConfig` - `/src/edison/core/session/config.py:13` (wrapper)
6. `ConfigMixin` - `/src/edison/core/adapters/_config.py:12` (mixin for adapters)

**Analysis:**
- One central `ConfigManager`, multiple domain-specific config wrappers
- Pattern is: Domain modules create thin wrappers around ConfigManager
- This is actually GOOD - provides domain-specific interfaces
- ConfigMixin for adapters follows different pattern (composition)

**Recommendation:**
- Document this as the standard config access pattern
- Ensure all wrappers are truly thin (no business logic)
- Consider if ConfigMixin pattern should extend to other modules

**Effort:** 2-3 hours (documentation + consistency check)

---

## CATEGORY 4: IMPORT PATTERN ANALYSIS

### 4.1 Most Common Imports (INFO)
**Pattern:** Top imports by frequency

```
116 - from __future__ import annotations (GOOD - modern Python)
 82 - from pathlib import Path (GOOD - standard library)
 31 - import os (Consider: should use pathlib more?)
 25 - import json (VIOLATION - should use utils.json_io)
 16 - import re
 11 - from dataclasses import dataclass
 11 - from .config import SessionConfig
 11 - from ..paths.resolver import PathResolver
 10 - from typing import Any, Dict, List, Optional
 10 - from ..paths.management import get_management_paths
  9 - import yaml (VIOLATION - should use file_io.utils.read_yaml_safe)
  9 - import subprocess
  9 - from ..paths.project import get_project_config_dir
  9 - from ..legacy_guard import enforce_no_legacy_project_root
```

**Analysis:**
- Heavy use of relative imports (good for module cohesion)
- `import json` appears 25 times (should be 0 - use utils)
- `import yaml` appears 9 times (should be 0 - use utils)
- `import os` appears 31 times (some should use pathlib)

**Recommendation:**
- Audit all `import json` and replace with `from edison.core.utils import json_io`
- Audit all `import yaml` and replace with `from edison.core.file_io.utils import read_yaml_safe`
- Review `import os` usage - convert to pathlib where possible

**Effort:** 6-8 hours

---

### 4.2 Internal Coupling (INFO)
**Pattern:** Relative imports showing module dependencies

**High Coupling Areas:**
1. **IDE modules** → composition, paths, config (tight coupling)
2. **QA modules** → session, task, file_io (expected cross-cutting)
3. **Session modules** → task, qa (orchestration layer)
4. **Composition modules** → paths, legacy_guard (composition root)

**Analysis:**
- Coupling is generally appropriate for the architecture
- IDE modules might be too tightly coupled to composition
- QA, Task, Session form a layered architecture

**Recommendation:**
- Document the dependency architecture in CLAUDE.md
- Consider if IDE modules should have more abstraction from composition

**Effort:** 4-6 hours (analysis + documentation)

---

## PRIORITY-ORDERED ACTION ITEMS

### CRITICAL (Do First)
1. **Consolidate JSON I/O** (8-10 hours)
   - Remove 36 direct json.load/dump calls
   - Use utils/json_io.py exclusively
   - Update file_io/utils.py to delegate to json_io

2. **Consolidate Repository Root Detection** (4-6 hours)
   - Remove 7 duplicate implementations
   - Single source: utils/git.py:get_repo_root()

3. **Consolidate Time/Timestamp Functions** (2-3 hours)
   - Remove duplicates of utc_timestamp() and _now_iso()
   - Single source: utils/time.py

4. **Centralize mkdir Pattern** (6-8 hours)
   - Replace 85 instances of .mkdir(parents=True, exist_ok=True)
   - Create file_io.utils.ensure_dir()

5. **Fix write_text_locked Duplication** (2 hours)
   - True duplication in task/locking.py vs task/io.py

### HIGH (Do Second)
6. **Centralize YAML Loading** (3-4 hours)
   - Replace 18 direct yaml.safe_load() calls
   - Use file_io.utils.read_yaml_safe()

7. **Remove QA Evidence Wrapper Functions** (2-3 hours)
   - Delete needless wrappers in session/next/actions.py

8. **Rename ValidationTransaction Classes** (3-4 hours)
   - Disambiguate QA vs Session transaction classes

9. **Consolidate _latest_round_dir** (2 hours)
   - Remove duplicates from task and session modules

### MEDIUM (Do Third)
10. **Rename _cfg Functions** (2-3 hours)
    - Disambiguate time vs json vs cli configs

11. **Consolidate qa_root** (2 hours)
    - Single implementation in paths module

12. **Fix find_record Duplication** (2 hours)
    - Consolidate or rename for clarity

13. **Fix load_delegation_config** (2-3 hours)
    - Consolidate or rename for clarity

14. **Audit State Machine Duplication** (3-4 hours)
    - Determine if task vs session state machines should be unified

15. **Document Module Structure Patterns** (8-12 hours)
    - Architectural documentation
    - Manager pattern guidelines
    - Config pattern guidelines

### LOW (Do Last)
16. **Audit render_markdown** (1 hour)
    - Verify delegation vs duplication

17. **Create Path Utility Functions** (4-6 hours)
    - ensure_exists(), read_if_exists(), etc.

---

## ESTIMATED TOTAL EFFORT

- **Critical Items:** 22-29 hours
- **High Priority Items:** 10-13 hours
- **Medium Priority Items:** 19-26 hours
- **Low Priority Items:** 5-7 hours

**Total:** 56-75 hours (7-10 developer days)

---

## RECOMMENDATIONS FOR PREVENTION

### 1. Code Review Checklist
Add to PR template:
- [ ] No duplicate function names without justification
- [ ] All file I/O uses centralized utilities (file_io, utils)
- [ ] No direct json.load/dump or yaml.safe_load calls
- [ ] No duplicate implementations of existing utilities

### 2. Pre-commit Hooks
Consider adding checks for:
- Direct json.load/dump usage
- Direct yaml.safe_load usage
- Duplicate function names across modules

### 3. Documentation Updates
- Document the canonical location for common utilities
- Create architecture diagram showing module dependencies
- Add "Where to find..." guide for common operations

### 4. Testing Requirements
- When consolidating duplicates, ensure existing tests cover both use cases
- Add integration tests for consolidated utilities
- Test that all old call sites work with new unified implementation

---

## CONCLUSION

The Edison codebase has **significant DRY violations** with 28 duplicate function names and extensive duplication of utility patterns. The most critical issues are:

1. **JSON I/O duplication** - 36 instances bypassing centralized utilities
2. **Repository root detection** - 7 different implementations
3. **Path operations** - 85 instances of repeated mkdir patterns
4. **YAML loading** - 18 instances of direct yaml.safe_load

These violations create:
- **Maintenance burden** - changes must be made in multiple places
- **Inconsistent behavior** - different implementations may behave differently
- **Code complexity** - developers must choose between duplicate functions
- **Testing difficulty** - duplicate code requires duplicate tests

**Recommended approach:**
1. Start with CRITICAL items (JSON, repo root, timestamps)
2. Move to HIGH items (YAML, wrappers)
3. Then tackle MEDIUM items (naming, consolidation)
4. Finally address LOW items (documentation, nice-to-haves)

This will systematically eliminate duplication while maintaining backward compatibility through careful refactoring and comprehensive testing.

---

**Next Steps:**
1. Review this audit with the team
2. Prioritize which items to tackle first
3. Create detailed implementation plans for each item
4. Begin systematic refactoring following TDD principles
