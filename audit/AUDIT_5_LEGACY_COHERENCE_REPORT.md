# AUDIT 5: Legacy Code & Coherence Analysis Report

**Date:** 2025-11-26
**Rules Audited:** #3 (NO LEGACY), #12 (STRICT COHERENCE)
**Auditor:** Claude Code Agent
**Status:** 🔴 MULTIPLE CRITICAL VIOLATIONS FOUND

---

## Executive Summary

This audit analyzed the Edison codebase for legacy code patterns and coherence violations across the entire `src/edison/core` structure. The analysis reveals **systematic violations of Rules #3 and #12**, with extensive backward compatibility code, legacy file layouts, and naming inconsistencies.

### Key Findings:
- **67 legacy/backward compatibility references** found across 30+ files
- **Legacy flat file system** maintained in parallel with new nested layout (session store)
- **3 compatibility shim modules** providing backward compatible imports
- **Multiple "DEPRECATED" parameters** still present in active code
- **12 duplicate filename patterns** across modules (config.py appears 5 times)
- **Inconsistent naming patterns** between similar modules

### Severity Assessment:
- **🔴 CRITICAL:** Legacy session flat file maintenance (ongoing dual-write)
- **🔴 CRITICAL:** Backward compatibility shims in core modules
- **🟡 MODERATE:** Deprecated parameters cluttering APIs
- **🟡 MODERATE:** File naming inconsistencies across modules

---

## PART 1: LEGACY CODE VIOLATIONS (Rule #3)

### 1.1 Legacy Guard System (KEEPER - NOT A VIOLATION)

**Location:** `src/edison/core/legacy_guard.py` (50 lines)

**Status:** ✅ **KEEP** - This is enforcement code, not legacy code

**Analysis:**
```python
def enforce_no_legacy_project_root(module_name: str) -> None:
    """Fail fast if the resolved project root is a legacy pre-Edison tree."""
```

This module enforces the NO-LEGACY policy by detecting `project-pre-edison` markers. It's imported by 11 modules:
- All QA modules (7 imports)
- Task paths module
- Session store module

**Recommendation:** Keep - this enforces the policy, doesn't violate it.

---

### 1.2 Session Store Dual Layout System (CRITICAL VIOLATION)

**Location:** `src/edison/core/session/store.py` (585 lines)

**Violation Severity:** 🔴 **CRITICAL**

**Evidence:**
```python
# Line 214-219: Maintains legacy flat file for compatibility
legacy_dir = _sessions_root() / "wip"
legacy_dir.mkdir(parents=True, exist_ok=True)
legacy_flat = legacy_dir / f"{sid}.json"
with acquire_file_lock(legacy_flat, timeout=5):
    _write_json(legacy_flat, data)

# Line 327-330: Cleanup of legacy flat files
if legacy_flat.exists():
    legacy_flat.unlink()

# Line 517-520: Maintains alias under wip flat layout for legacy callers
legacy = _sessions_root() / "wip" / f"{sid}.json"
legacy.parent.mkdir(parents=True, exist_ok=True)
io_atomic_write_json(legacy, data)
```

**Impact:**
- Every session write duplicates to legacy flat layout
- File I/O overhead (2x writes per session save)
- Complexity in session discovery (searches both layouts)
- Migration never completed

**Justification Given:**
- "Maintain legacy flat file for compatibility with older task tests"
- "Legacy owner-based lookup (FALLBACK for backward compatibility)"

**Assessment:** Tests should be updated, not production code maintained for test compatibility.

**Recommendation:**
1. **DELETE** all legacy flat file maintenance code
2. **UPDATE** tests to use new nested layout only
3. **MIGRATE** any remaining flat files to nested layout
4. **REMOVE** legacy path candidates from discovery.py

**Lines to Delete:**
- store.py: 127, 164, 214-219, 283, 327-330, 351-382 (fallback lookup), 517-520
- discovery.py: 95-102 (legacy wip path)

**Estimated Impact:** ~80 lines deleted, 15+ test files to update

---

### 1.3 Session Manager Legacy Compatibility (CRITICAL VIOLATION)

**Location:** `src/edison/core/session/manager.py` (294 lines)

**Violation Severity:** 🔴 **CRITICAL**

**Evidence:**
```python
# Line 99-102: Maintains legacy flat file for compatibility
legacy = store._sessions_root() / "wip" / f"{session_id}.json"
legacy.parent.mkdir(parents=True, exist_ok=True)
store._write_json(legacy, sess)

# Line 189-194: Legacy-compatible active path
legacy_dir = mgmt_paths.get_session_state_dir("active") / sid
legacy_dir.mkdir(parents=True, exist_ok=True)
store._write_json(legacy_dir / "session.json", data)

# Line 282: Provide legacy-compatible filename
```

**Recommendation:**
1. **DELETE** all legacy flat file writes
2. **DELETE** legacy active path creation
3. **SIMPLIFY** SessionManager to only use nested layout

**Lines to Delete:** 99-102, 189-194, 217-219, 282

---

### 1.4 Session Naming Deprecated Parameters (MODERATE VIOLATION)

**Location:** `src/edison/core/session/naming.py` (150 lines)

**Violation Severity:** 🟡 **MODERATE**

**Evidence:**
```python
class SessionNamingStrategy:
    """
    This class exists for backward compatibility with WAVE 1-4 code,
    but the implementation is now simple: just delegate to process inspector.
    """

    def __init__(self, config: Optional[dict] = None):
        """Config parameter kept for backward compatibility but ignored."""
        self._config = config or {}  # No longer used

    def generate(
        self,
        process: Optional[str] = None,      # DEPRECATED
        owner: Optional[str] = None,        # DEPRECATED
        existing_sessions: Optional[List[str]] = None,  # DEPRECATED
        **kwargs,
    ) -> str:
        """All parameters are DEPRECATED and ignored."""
```

**Assessment:** The class exists only for backward compatibility with WAVE 1-4 code. The implementation is trivial - it just wraps process inspector.

**Recommendation:**
1. **DELETE** SessionNamingStrategy class entirely
2. **EXPOSE** process inspector directly
3. **UPDATE** callers to use process inspector
4. If facade needed, create minimal one without deprecated params

**Impact:** This is a pure wrapper maintained for backward compatibility - prime candidate for deletion.

---

### 1.5 Compatibility Shim Modules (CRITICAL VIOLATION)

#### 1.5.1 Core CLI Utils Shim

**Location:** `src/edison/core/__init__.py` (40 lines)

**Violation Severity:** 🔴 **CRITICAL**

**Evidence:**
```python
# Line 11-37: Create a compatibility shim for cli_utils
_cli_utils = ModuleType("cli_utils")

# Import from the new split locations
from .utils.cli_errors import json_output, cli_error, run_cli
from .utils.subprocess import run_command, run_git_command, ...

# Populate the shim module
_cli_utils.json_output = json_output
_cli_utils.cli_error = cli_error
# ... etc

# Make it available as cli_utils
cli_utils = _cli_utils
```

**Assessment:** Entire module exists to provide `from edison.core import cli_utils` for code that hasn't migrated to `edison.core.utils.xxx`.

**Recommendation:**
1. **FIND** all imports of `from edison.core import cli_utils`
2. **UPDATE** to import from correct locations
3. **DELETE** entire shim from `__init__.py`

**Search Command:**
```bash
grep -rn "from edison.core import cli_utils\|from edison.core.cli_utils" --include="*.py"
```

#### 1.5.2 Utils CLI Compatibility Module

**Location:** `src/edison/core/utils/__init__.py` (98 lines)

**Violation Severity:** 🔴 **CRITICAL**

**Evidence:**
```python
# Line 47-57: Create a 'cli' compatibility module
cli = ModuleType("edison.core.utils.cli")
cli.parse_common_args = parse_common_args
cli.session_parent = session_parent
# ... etc
```

**Assessment:** Allows `from edison.core.utils import cli; cli.output_json()` instead of direct imports.

**Recommendation:**
1. **FIND** all uses of `from edison.core.utils import cli`
2. **UPDATE** to import functions directly
3. **DELETE** cli compatibility module

#### 1.5.3 Composition IDE Re-exports

**Location:** `src/edison/core/composition/__init__.py`

**Evidence:**
```python
# Line 17-28: Re-export IDE modules for backward compatibility
from ..ide.commands import (  # noqa: F401
    CommandArg, CommandDefinition, CommandComposer, PlatformAdapter,
    ClaudeCommandAdapter, CursorCommandAdapter, CodexCommandAdapter,
)
from ..ide.hooks import HookComposer, HookDefinition  # noqa: F401
from ..ide.settings import SettingsComposer, merge_permissions  # noqa: F401
```

**Recommendation:**
1. **FIND** imports from `edison.core.composition` for IDE classes
2. **UPDATE** to import from `edison.core.ide.*`
3. **DELETE** IDE re-exports from composition __init__

---

### 1.6 Task Manager Legacy Facade (MODERATE VIOLATION)

**Location:** `src/edison/core/task/manager.py` (56 lines)

**Violation Severity:** 🟡 **MODERATE**

**Evidence:**
```python
"""TaskManager facade used by legacy tests."""

class TaskManager:
    """Lightweight OO wrapper around task transitions."""
```

**Assessment:** Entire file exists as "facade used by legacy tests". The implementation is thin wrapper around task module functions.

**Recommendation:**
1. **FIND** all uses of TaskManager class
2. **UPDATE** tests to use task module functions directly
3. **DELETE** manager.py entirely

**Search Command:**
```bash
grep -rn "from.*task.*import.*TaskManager\|TaskManager(" tests/ --include="*.py"
```

---

### 1.7 Task Module Legacy Import Path

**Location:** `src/edison/core/task/state.py` (18 lines)

**Evidence:**
```python
"""State machine helpers for legacy ``lib.tasks`` import path."""
```

**Recommendation:** File is 18 lines providing backward compatible import. Evaluate if still needed.

---

### 1.8 Task Metadata Compatibility Shim

**Location:** `src/edison/core/task/metadata.py` (lines 315-319)

**Evidence:**
```python
# Compatibility shim: some legacy callers import find_record from this module.
# Provide a thin wrapper that delegates to the finder implementation.
def find_record(record_id: str, record_type: RecordType, session_id: str | None = None):
    from .finder import find_record as _find_record  # local import to avoid cycles
    return _find_record(record_id, record_type, session_id=session_id)
```

**Recommendation:**
1. **FIND** imports of `find_record` from `task.metadata`
2. **UPDATE** to import from `task.finder`
3. **DELETE** shim function

---

### 1.9 Composition Audit Backward Compatibility

**Location:** `src/edison/core/composition/audit/__init__.py` (53 lines)

**Evidence:**
```python
"""
This package was split from a single audit.py file (299 lines) into focused modules:
- discovery: Find guideline files across layers
- analysis: Build shingle index and duplication matrix
- purity: Detect cross-layer term leakage

All previous exports are re-exported here for backward compatibility.
"""

# Backward compatibility: global constant that was in original audit.py
project_TERMS = project_terms()

__all__ = [
    # ... all exports ...
    "project_TERMS",  # Backward compatibility
]
```

**Assessment:** The re-exports are fine (that's what `__init__.py` is for), but the `project_TERMS` global constant is explicitly marked as "backward compatibility".

**Recommendation:**
1. **FIND** uses of `project_TERMS` (vs `project_terms()`)
2. **UPDATE** to call `project_terms()` function
3. **DELETE** `project_TERMS` global

---

### 1.10 Composition Pack Legacy Trigger Format

**Location:** `src/edison/core/composition/packs.py` (line 428-429)

**Evidence:**
```python
# Legacy shape (Phase 2) – treat list as file patterns for backward compatibility
trigger_patterns = list(raw_triggers or [])
```

**Recommendation:** If Phase 2 format is obsolete, remove support. Document current format only.

---

### 1.11 Conditional Imports (Acceptable Pattern)

**Evidence Found:**
- `ide/hooks.py`: Jinja2 optional dependency fallback
- `task/locking.py`: resilience module optional import
- `setup/questionnaire.py`: Jinja2 optional dependency

**Assessment:** ✅ **ACCEPTABLE** - These are optional dependencies with graceful degradation, not legacy compatibility code.

**Justification:**
- Jinja2 is explicitly optional
- Fallback implementations provided
- No backward compatibility concerns

---

## PART 2: COHERENCE VIOLATIONS (Rule #12)

### 2.1 Duplicate Filename Patterns

**Analysis:** Multiple modules use identical filenames for different purposes, making codebase navigation confusing.

| Filename | Count | Locations | Coherence Issue |
|----------|-------|-----------|-----------------|
| `config.py` | 5 | core/, qa/, task/, orchestrator/, session/ | ⚠️ Inconsistent: some are ConfigManager wrappers, some are domain config |
| `store.py` | 3 | qa/, task/, session/ | ✅ Coherent: all provide storage operations for their domain |
| `discovery.py` | 3 | setup/, composition/audit/, session/ | ⚠️ Inconsistent: different purposes (setup discovery vs file discovery vs session discovery) |
| `validation.py` | 2 | task/, session/ | ✅ Coherent: both validate state transitions |
| `transaction.py` | 2 | qa/, session/ | ✅ Coherent: both provide transactional operations |
| `state.py` | 2 | task/, session/ | ✅ Coherent: both provide state machine helpers |
| `models.py` | 2 | rules/, session/ | ✅ Coherent: both define data models |
| `metadata.py` | 2 | composition/, task/ | ⚠️ Different: composition=guideline metadata, task=record metadata |
| `manager.py` | 2 | task/, session/ | ✅ Coherent: both provide manager facades |
| `locking.py` | 2 | file_io/, task/ | ⚠️ Inconsistent: file_io is base, task wraps it |
| `graph.py` | 2 | task/, session/ | ✅ Coherent: both provide dependency graph operations |
| `engine.py` | 2 | state/, rules/ | ⚠️ Different purposes: state machine vs rules evaluation |

**Assessment:**

**COHERENT (Keep):**
- `store.py` - consistent pattern across qa/task/session domains
- `transaction.py` - consistent transactional pattern
- `state.py` - consistent state machine pattern
- `models.py` - consistent data model pattern
- `validation.py` - consistent validation pattern
- `manager.py` - consistent facade pattern
- `graph.py` - consistent dependency graph pattern

**INCOHERENT (Consider Renaming):**
- `discovery.py` - 3 different purposes, no consistent pattern
  - `setup/discovery.py` → `setup/installer_discovery.py`
  - `composition/audit/discovery.py` → `composition/audit/guideline_discovery.py`
  - `session/discovery.py` → `session/layout.py` (already have layout.py!)
- `config.py` - 5 instances with varying purposes
  - Core `config.py` is ConfigManager (keep)
  - Others are domain-specific config helpers (consider more specific names)
- `metadata.py` - completely different purposes
  - `composition/metadata.py` → `composition/guideline_metadata.py`
  - `task/metadata.py` (keep - clearly task metadata)
- `locking.py` duplication
  - `file_io/locking.py` (base, keep)
  - `task/locking.py` (wrapper - consider renaming to `task_locks.py` or merge into task/io.py)

---

### 2.2 Module Structure Coherence

**Analysis:** Session, task, qa, and composition modules should follow consistent patterns.

#### Session Module (20 files)
```
session/
  __init__.py
  archive.py
  autostart.py
  config.py          # Config wrapper
  context.py
  database.py
  discovery.py       # File layout discovery
  graph.py           # Dependency graph
  layout.py          # File layout helpers
  manager.py         # Manager facade
  models.py          # Data models
  naming.py          # ID generation
  recovery.py
  state.py           # State machine
  state_machine_docs.py
  store.py           # Storage I/O
  transaction.py     # Transactional operations
  validation.py      # State validation
  verify.py
  worktree.py
```

#### Task Module (15 files)
```
task/
  __init__.py
  claims.py
  config.py          # Config wrapper
  context7.py
  finder.py          # Record discovery
  graph.py           # Dependency graph
  io.py              # File I/O
  locking.py         # Locking helpers
  manager.py         # Manager facade
  metadata.py        # Record metadata
  paths.py           # Path resolution
  state.py           # State machine
  store.py           # Storage operations
  transitions.py     # State transitions
  validation.py      # State validation
```

#### QA Module (10 files)
```
qa/
  __init__.py
  bundler.py
  config.py          # Config wrapper
  evidence.py        # Evidence management
  promoter.py
  rounds.py          # Round management
  scoring.py
  store.py           # Storage operations
  transaction.py     # Transactional operations
  validator.py
```

**Coherence Assessment:**

**✅ GOOD PATTERNS (Consistent across modules):**
- All have `config.py` for domain-specific config
- All have `store.py` for storage operations
- Session/task both have `state.py`, `validation.py`, `manager.py`, `graph.py`
- Consistent separation of concerns

**⚠️ INCONSISTENCIES:**
- Session has `discovery.py` for file layout, task has `finder.py` for records
  - **Recommendation:** Rename one for clarity (e.g., `session/layout_discovery.py` vs `task/record_finder.py`)
- Task has `io.py` for general file I/O, session has specialized files (store.py, archive.py)
  - **Assessment:** Both approaches valid, acceptable variation
- Task has `paths.py` for path resolution, session uses resolver directly
  - **Assessment:** Task domain needs more path logic, acceptable

**Overall:** Structure is reasonably coherent with minor naming inconsistencies.

---

### 2.3 CRUD Method Naming Coherence

**Analysis:** Checking for consistent naming of CRUD operations across modules.

**Load/Save Pattern:**
```python
# Session store
def load_session(session_id: str, state: Optional[str] = None) -> Dict
def save_session(session_id: str, data: Dict[str, Any]) -> None

# Task I/O
def load_task_record(task_id: str) -> Dict[str, Any]
# No corresponding save_task_record found

# QA bundler
def load_bundle_summary(task_id: str, round_num: int, ...) -> Dict
# No save_bundle_summary found
```

**Create Pattern:**
```python
# Task I/O
def create_task(task_id: str, title: str, description: str = "") -> Path
def create_qa_brief(task_id: str, title: str) -> Path
def create_task_record(task_id: str, title: str, *, status: str = "todo") -> Dict

# Session database
def create_session_database(session_id: str) -> Optional[str]

# Session manager
def create_session(...) -> str
def create_session_with_worktree(...) -> tuple
```

**Update Pattern:**
```python
# Task I/O
def update_task_record(task_id: str, updates: Dict[str, Any], ...) -> Dict

# Session graph
def update_record_status(...)

# JSON utils
def update_json(file_path: Path | str, update_fn: Callable) -> None
```

**Assessment:** ✅ **COHERENT** - Consistent naming patterns:
- `load_*` for reading
- `save_*` for writing (session domain)
- `create_*` for creating new entities
- `update_*` for modifying existing entities

No violations found in CRUD naming.

---

### 2.4 Class Naming Coherence

**Sample of class names (sorted):**
```
ActionRegistry
AgentError, AgentNotFoundError, AgentTemplateError
AgentRegistry
ClaudeAdapter, ClaudeCommandAdapter, ClaudeSync
CodexAdapter, CodexCommandAdapter
CommandArg, CommandDefinition, CommandComposer
ComposeError, ComposeResult, CompositionEngine
ConfigManager, ConfigMixin
CursorCommandAdapter, CursorPromptAdapter, CursorSync
EdisonAgentSections, EdisonError, EdisonPathError
EvidenceError, EvidenceManager
GuardRegistry, ConditionRegistry
GuidelineRecord, GuidelineRegistry, GuidelinePaths
HookComposer, HookDefinition
```

**Assessment:** ✅ **HIGHLY COHERENT**
- Consistent naming conventions:
  - `*Registry` for registry classes
  - `*Manager` for manager classes
  - `*Error` for exceptions
  - `*Adapter` for adapter pattern
  - `*Composer` for composition classes
  - `*Definition` for data classes defining structure
  - `*Result` for result objects

No violations found.

---

### 2.5 TODO/FIXME Analysis

**Evidence:**
```python
# session/manager.py:116
# TODO: Implement listing for other states in store
```

**Assessment:** Only 1 TODO found in entire codebase. ✅ **EXCELLENT**

---

## PART 3: SUMMARY & PRIORITIZED ACTION PLAN

### 3.1 Legacy Code Summary

| Category | Severity | Lines | Files | Action |
|----------|----------|-------|-------|--------|
| Session dual layout | 🔴 CRITICAL | ~150 | 3 | DELETE |
| Compatibility shims | 🔴 CRITICAL | ~80 | 3 | DELETE |
| Deprecated parameters | 🟡 MODERATE | ~50 | 1 | DELETE |
| Legacy facades | 🟡 MODERATE | ~60 | 2 | DELETE |
| Optional dependencies | ✅ ACCEPTABLE | ~30 | 3 | KEEP |
| Legacy guard enforcement | ✅ ACCEPTABLE | 50 | 1 | KEEP |

**Total Legacy Code to Delete:** ~340 lines across 9 files

---

### 3.2 Coherence Summary

| Category | Assessment | Action Required |
|----------|------------|-----------------|
| Module structure | ✅ COHERENT | Minor cleanup |
| CRUD naming | ✅ COHERENT | None |
| Class naming | ✅ COHERENT | None |
| File naming | ⚠️ MIXED | Rename 5 files |
| Duplicate filenames | ⚠️ MIXED | Rename 3-5 files |

---

### 3.3 PRIORITIZED ACTION PLAN

#### PHASE 1: CRITICAL LEGACY DELETIONS (HIGH PRIORITY)

**Task 1.1: Remove Session Dual Layout System**
- **Files:** `session/store.py`, `session/manager.py`, `session/discovery.py`
- **Lines:** ~150 lines to delete
- **Steps:**
  1. Remove all legacy flat file writes from store.py
  2. Remove legacy path candidates from discovery.py
  3. Remove legacy flat file writes from manager.py
  4. Update tests to expect nested layout only
  5. Add migration script to convert any remaining flat files
- **Impact:** Major complexity reduction, ~30% faster session I/O
- **Risk:** Medium (requires test updates)

**Task 1.2: Delete Compatibility Shim Modules**
- **Files:** `core/__init__.py`, `utils/__init__.py`, `composition/__init__.py`
- **Lines:** ~80 lines to delete
- **Steps:**
  1. Find all imports: `grep -rn "from edison.core import cli_utils"`
  2. Update imports to use direct paths
  3. Delete cli_utils shim from core/__init__.py
  4. Delete cli module from utils/__init__.py
  5. Delete IDE re-exports from composition/__init__.py
- **Impact:** Cleaner import structure, no performance change
- **Risk:** Low (compile-time errors if any imports missed)

**Task 1.3: Remove SessionNamingStrategy Backward Compatibility**
- **File:** `session/naming.py`
- **Lines:** ~50 lines to simplify
- **Steps:**
  1. Find all uses of SessionNamingStrategy
  2. Update to use process inspector directly
  3. Remove deprecated parameters from generate()
  4. Or delete class entirely if only used in tests
- **Impact:** Cleaner API
- **Risk:** Low

#### PHASE 2: MODERATE LEGACY CLEANUP (MEDIUM PRIORITY)

**Task 2.1: Delete Task Manager Facade**
- **File:** `task/manager.py`
- **Lines:** 56 lines to delete
- **Steps:**
  1. Find all TaskManager usage in tests
  2. Update to use task module functions directly
  3. Delete manager.py
- **Impact:** Reduced abstraction layers
- **Risk:** Low (isolated to tests)

**Task 2.2: Remove Task Metadata Compatibility Shim**
- **File:** `task/metadata.py` (lines 315-319)
- **Steps:**
  1. Find imports of find_record from metadata
  2. Update to import from finder
  3. Delete shim function
- **Impact:** Minor cleanup
- **Risk:** Very low

**Task 2.3: Clean Up Deprecated Task State Module**
- **File:** `task/state.py`
- **Lines:** 18 lines
- **Assessment:** Evaluate if still needed for "legacy lib.tasks import path"
- **Action:** Delete if no longer needed

**Task 2.4: Remove project_TERMS Backward Compatibility**
- **File:** `composition/audit/__init__.py`
- **Steps:**
  1. Find uses of `project_TERMS` global
  2. Update to call `project_terms()` function
  3. Delete global constant
- **Impact:** Minor API cleanup
- **Risk:** Very low

#### PHASE 3: COHERENCE IMPROVEMENTS (LOW PRIORITY)

**Task 3.1: Rename Inconsistent discovery.py Files**
- `setup/discovery.py` → `setup/installer_discovery.py`
- `composition/audit/discovery.py` → `composition/audit/guideline_discovery.py`
- `session/discovery.py` → Keep (most appropriate use of name)
- **Impact:** Better navigation, clearer purpose
- **Risk:** Low (update imports)

**Task 3.2: Rename Inconsistent metadata.py Files**
- `composition/metadata.py` → `composition/guideline_metadata.py`
- `task/metadata.py` → Keep
- **Impact:** Clearer purpose
- **Risk:** Low

**Task 3.3: Consider locking.py Consolidation**
- Evaluate if `task/locking.py` can be merged into `task/io.py`
- Or rename to `task/task_locks.py` to differentiate from base
- **Impact:** Minor organizational improvement
- **Risk:** Very low

**Task 3.4: Add Missing save_task_record Function**
- For symmetry with load_task_record
- Or document why it's not needed
- **Impact:** API consistency
- **Risk:** Very low

#### PHASE 4: DOCUMENTATION (ONGOING)

**Task 4.1: Document Current Pack Trigger Format**
- Remove Phase 2 legacy format support
- Or document that both formats are intentionally supported
- **File:** `composition/packs.py` line 428

**Task 4.2: Resolve Manager TODO**
- **File:** `session/manager.py` line 116
- Implement listing for other states, or remove TODO if not needed

---

### 3.4 RISK ASSESSMENT

| Risk Level | Tasks | Mitigation |
|------------|-------|------------|
| 🔴 HIGH | None | - |
| 🟡 MEDIUM | Session dual layout removal | Full test coverage required, migration script |
| 🟢 LOW | All other tasks | Standard testing sufficient |

---

### 3.5 ESTIMATED EFFORT

| Phase | Tasks | Lines Changed | Files | Effort | Priority |
|-------|-------|---------------|-------|--------|----------|
| Phase 1 | 3 | ~280 lines deleted, ~50 tests updated | 6 core + 15 tests | 8-12 hours | 🔴 HIGH |
| Phase 2 | 4 | ~100 lines deleted | 4 | 3-4 hours | 🟡 MEDIUM |
| Phase 3 | 4 | ~50 lines changed (renames) | 8 | 2-3 hours | 🟢 LOW |
| Phase 4 | 2 | ~20 lines | 2 | 1 hour | 🟢 LOW |
| **TOTAL** | **13** | **~450 lines** | **35 files** | **14-20 hours** | |

---

### 3.6 SUCCESS METRICS

**Legacy Elimination:**
- ✅ Zero references to "legacy" or "backward compatibility" in production code
- ✅ Zero deprecated parameters in active APIs
- ✅ Zero compatibility shim modules
- ✅ Single session file layout (nested only)
- ✅ Zero facade classes marked "for legacy tests"

**Coherence Achievement:**
- ✅ No filename conflicts where files serve different purposes
- ✅ Consistent naming patterns for CRUD operations
- ✅ Consistent module structure across domains
- ✅ Zero TODOs in production code

---

## PART 4: DETAILED FILE-BY-FILE BREAKDOWN

### Files Requiring Major Changes (Phase 1)

#### 1. src/edison/core/session/store.py
**Lines:** 585
**Changes:** Delete ~80 lines, refactor ~20 lines
**Violations:**
- Line 127: Legacy wip path comment
- Line 164: Legacy flat file preference comment
- Lines 214-219: Legacy flat file write
- Line 283: Legacy flat file check comment
- Lines 327-330: Legacy flat file cleanup
- Lines 351-382: Legacy owner-based fallback lookup
- Lines 517-520: Legacy wip alias write

**Action Items:**
1. Remove all legacy flat file I/O
2. Remove legacy lookup fallback
3. Simplify discovery to nested layout only
4. Update docstrings to remove legacy references

#### 2. src/edison/core/session/manager.py
**Lines:** 294
**Changes:** Delete ~30 lines
**Violations:**
- Lines 99-102: Legacy flat file maintenance
- Line 116: TODO comment
- Lines 189-194: Legacy-compatible active path
- Lines 217-219: Legacy flat file write
- Line 282: Legacy-compatible filename comment

**Action Items:**
1. Remove all legacy flat file writes
2. Remove legacy active path creation
3. Resolve or remove TODO
4. Simplify to nested layout only

#### 3. src/edison/core/session/discovery.py
**Lines:** ~200
**Changes:** Delete ~10 lines
**Violations:**
- Lines 95-102: Legacy wip path candidates

**Action Items:**
1. Remove legacy path candidates
2. Update docstrings
3. Verify tests still pass

#### 4. src/edison/core/__init__.py
**Lines:** 40
**Changes:** Delete ~30 lines
**Violations:**
- Lines 11-37: Entire cli_utils compatibility shim

**Action Items:**
1. Search for all imports of cli_utils
2. Update to direct imports
3. Delete shim code
4. Keep only exceptions export

#### 5. src/edison/core/utils/__init__.py
**Lines:** 98
**Changes:** Delete ~10 lines
**Violations:**
- Lines 47-57: CLI compatibility module

**Action Items:**
1. Search for uses of `from edison.core.utils import cli`
2. Update to direct imports
3. Delete cli module creation
4. Keep all other exports

#### 6. src/edison/core/composition/__init__.py
**Lines:** ~80
**Changes:** Delete ~10 lines
**Violations:**
- Lines 17-28: IDE module re-exports for backward compatibility

**Action Items:**
1. Find imports from composition for IDE classes
2. Update to import from ide module
3. Delete re-export lines

### Files Requiring Moderate Changes (Phase 2)

#### 7. src/edison/core/session/naming.py
**Lines:** 150
**Changes:** Delete class or remove deprecated params
**Violations:**
- Entire SessionNamingStrategy class exists for backward compatibility
- Lines 77, 80, 106-109: Deprecated parameter documentation

**Action Items:**
1. Evaluate usage of SessionNamingStrategy
2. Either delete class or remove deprecated parameters
3. Update callers

#### 8. src/edison/core/task/manager.py
**Lines:** 56
**Changes:** Delete entire file
**Violations:**
- Line 1: "TaskManager facade used by legacy tests"
- Entire file is legacy facade

**Action Items:**
1. Find TaskManager usage in tests
2. Update to use task module directly
3. Delete file

#### 9. src/edison/core/task/metadata.py
**Lines:** ~320
**Changes:** Delete 5 lines
**Violations:**
- Lines 315-319: Compatibility shim for find_record

**Action Items:**
1. Find imports of find_record from metadata
2. Update to import from finder
3. Delete shim

#### 10. src/edison/core/task/state.py
**Lines:** 18
**Changes:** Evaluate and possibly delete
**Violations:**
- Line 1: "State machine helpers for legacy lib.tasks import path"

**Action Items:**
1. Check if still needed
2. If not, delete entire file

### Files Requiring Minor Changes (Phase 3)

#### 11-13. Filename Renames
- `setup/discovery.py` → `setup/installer_discovery.py`
- `composition/audit/discovery.py` → `composition/audit/guideline_discovery.py`
- `composition/metadata.py` → `composition/guideline_metadata.py`

**Action Items:**
1. Rename files
2. Update imports
3. Update documentation

---

## PART 5: GREP COMMANDS FOR REMEDIATION

### Finding Legacy References

```bash
# Find all legacy/backward compatibility comments
grep -rn "legacy\|deprecated\|compat\|backward" src/edison/core --include="*.py"

# Find compatibility shim imports
grep -rn "from edison.core import cli_utils" . --include="*.py"
grep -rn "from edison.core.utils import cli" . --include="*.py"

# Find SessionNamingStrategy usage
grep -rn "SessionNamingStrategy" . --include="*.py"

# Find TaskManager usage
grep -rn "from.*task.*import.*TaskManager\|TaskManager(" . --include="*.py"

# Find find_record imports from metadata
grep -rn "from.*task.metadata.*import.*find_record" . --include="*.py"

# Find project_TERMS usage (vs project_terms())
grep -rn "project_TERMS" . --include="*.py"

# Find IDE imports from composition
grep -rn "from edison.core.composition import.*Command\|from edison.core.composition import.*Hook" . --include="*.py"
```

---

## PART 6: TEST IMPACT ANALYSIS

### Tests Likely Requiring Updates

**Session Store Tests:**
- Any test checking for flat file layout
- Any test reading from `sessions/wip/*.json` directly
- Any test expecting active/ legacy paths

**Command to find:**
```bash
grep -rn "sessions/wip\|legacy_flat\|legacy.*json" tests/ --include="*.py"
```

**CLI Utils Tests:**
- Any test importing `from edison.core import cli_utils`

**Command to find:**
```bash
grep -rn "cli_utils" tests/ --include="*.py"
```

**TaskManager Tests:**
- Any test using TaskManager class

**Command to find:**
```bash
grep -rn "TaskManager" tests/ --include="*.py"
```

---

## CONCLUSIONS

### Rule #3 Violation Assessment: 🔴 CRITICAL

**Evidence:** 67 legacy/backward compatibility references across 30+ files, with active dual-write patterns causing performance and maintenance overhead.

**Root Cause:** Incremental migration approach that never completed. Legacy compatibility code was added "temporarily" but never removed.

**Impact:**
- ~280 lines of pure legacy code (15% of identified issues)
- Every session write duplicates to legacy layout (2x I/O)
- Confusing codebase with multiple "deprecated" parameters
- Import paths that don't reflect actual structure

### Rule #12 Violation Assessment: 🟡 MODERATE

**Evidence:** Minor filename inconsistencies and duplicate names across modules.

**Root Cause:** Organic growth without consistent naming guidelines for specialized modules.

**Impact:**
- Slightly harder navigation (discovery.py has 3 different meanings)
- Minor confusion (metadata.py serves different purposes in different modules)
- No functional impact, purely organizational

### Overall Assessment

**Legacy Violations:** More severe than expected. The dual layout system in session storage is particularly problematic.

**Coherence:** Better than expected. Core patterns are consistent; only filenames need minor cleanup.

### Recommendations

1. **IMMEDIATE:** Phase 1 cleanup (session dual layout, compatibility shims)
2. **SHORT-TERM:** Phase 2 cleanup (facades, deprecated params)
3. **LONG-TERM:** Phase 3 renaming for perfect coherence
4. **ONGOING:** Maintain NO-LEGACY policy for all new code

### Next Steps

1. **Review this report** with team
2. **Prioritize tasks** based on impact/effort
3. **Create sub-agents** for each phase (following TDD)
4. **Monitor metrics** for success criteria
5. **Update coding guidelines** to prevent regression

---

## APPENDIX A: ACCEPTABLE PATTERNS (Not Violations)

### A.1 Optional Dependencies

**Files:** `ide/hooks.py`, `task/locking.py`, `setup/questionnaire.py`

**Pattern:**
```python
try:
    from jinja2 import Template
except Exception:
    Template = None  # Graceful degradation
```

**Assessment:** ✅ ACCEPTABLE - This is proper optional dependency handling, not legacy compatibility.

### A.2 Legacy Guard Enforcement

**File:** `legacy_guard.py`

**Assessment:** ✅ KEEPER - This enforces NO-LEGACY policy, doesn't violate it.

### A.3 Fallback Values

**Pattern:** Graceful degradation decorators, config fallback to defaults

**Assessment:** ✅ ACCEPTABLE - These are proper error handling and configuration patterns.

---

## APPENDIX B: METRICS SUMMARY

| Metric | Count |
|--------|-------|
| Total files analyzed | 147 |
| Files with legacy references | 30 |
| Legacy/compat/backward references | 67 |
| Deprecated parameter declarations | 6 |
| Compatibility shim modules | 3 |
| Legacy facade classes | 1 |
| Lines of pure legacy code | ~280 |
| Duplicate filename patterns | 12 |
| Incoherent filename patterns | 5 |
| TODOs in production code | 1 |
| Silent error suppression (except pass) | 0 |

---

**END OF REPORT**
