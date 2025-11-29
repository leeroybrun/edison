# Edison Core Directory Comprehensive Refactoring Plan

> **Last Updated**: 2025-11-29
> **Status**: ALL TASKS PENDING (Previous changes were lost - full restart required)

## Executive Summary

This document outlines a complete refactoring plan for `/src/edison/core/` and `/src/edison/cli/` based on comprehensive analysis passes covering **205 Python files** in core across **66 directories**, plus **62 CLI commands**. The plan addresses:

- **Critical violations** of CLAUDE.md principles
- **DRY violations** and code duplication (153 files with bare exceptions, 88 backward compat refs)
- **Structural improvements** (subdirectory organization for session/, qa/)
- **Hardcoded values** that should be YAML-configurable
- **Legacy/backward compatibility code** that must be removed
- **Long functions** that need decomposition
- **Error handling** standardization
- **Test anti-patterns** (79 test files using mocks - violates NO MOCKS principle)
- **CLI business logic migration** (4 files have deep logic that belongs in core/)

### Analysis Summary (2025-11-29)

| Category | Count | Status |
|----------|-------|--------|
| Core module files | 205 | Analyzed |
| CLI commands | 62 | Analyzed |
| Bare exception handlers | 153 files | TO FIX |
| Backward compat references | 88 | TO REMOVE |
| Test files using mocks | 79 | TO FIX |
| CLAUDE.md principles passing | 11/16 | TO IMPROVE |
| Critical issues found | 7 | TO FIX |

---

## Phase 1: Critical Fixes (MUST DO FIRST)

> **Status**: ✅ COMPLETED (Wave 1)

### Task 1.1: Delete Legacy Code
**Priority**: P0 - CRITICAL
**Status**: ✅ DONE
**Effort**: 4-6 hours
**Files affected**: 2 files to delete, ~20 files to update imports

#### Subtask 1.1.1: Delete task/compat.py
```
DELETE: /src/edison/core/task/compat.py (293 lines)
```
- This file creates dual storage (JSON + Markdown) violating Single Source of Truth
- Contains silent failures (`try/except pass`)
- **VIOLATES**: Principle #3 (NO LEGACY)

**Actions**:
1. Identify all imports of `edison.core.task.compat`
2. Migrate any necessary functionality to `task/repository.py`
3. Update all tests that use compat functions
4. Delete the file completely
5. Run full test suite to verify

#### Subtask 1.1.2: Delete empty session/store/ directory
```
DELETE: /src/edison/core/session/store/ (empty directory)
```

---

### Task 1.2: Fix Critical Test Import Errors
**Priority**: P0 - CRITICAL
**Status**: ✅ DONE (already correct)
**Effort**: 30 minutes
**Files affected**: 1 file

```
FIX: /tests/unit/cli/orchestrator/test_launcher.py
```

**Current (BROKEN)**:
```python
from edison.cli.orchestrator.launcher import (
    OrchestratorLauncher,
    OrchestratorNotFoundError,
)
```

**Should be**:
```python
from edison.core.orchestrator import (
    OrchestratorLauncher,
    OrchestratorNotFoundError,
)
```

---

### Task 1.3: Fix Runtime Error in Composition
**Priority**: P0 - CRITICAL
**Status**: ✅ DONE
**Effort**: 15 minutes
**Files affected**: 1 file

```
FIX: /src/edison/core/composition/packs/loader.py
Line 28: Change read_yaml() to read_yaml_file()
```

The file imports `read_yaml as read_yaml_file` but calls `read_yaml()` directly, causing runtime crash.

---

### Task 1.4: Fix LRU Cache with Path Objects
**Priority**: P0 - CRITICAL
**Status**: ✅ DONE (already correct)
**Effort**: 2 hours
**Files affected**: 2 files

Path objects are not reliably hashable for LRU cache. Must convert to strings.

```
FIX: /src/edison/core/utils/config.py
Lines 29-60, 62-110: Convert Path parameters to str before caching

FIX: /src/edison/core/utils/subprocess.py
Lines 34-41: Convert Path parameter to str
```

**Pattern to apply**:
```python
@lru_cache(maxsize=8)
def _cached_function(repo_root_str: str) -> Dict[str, Any]:
    repo_root = Path(repo_root_str) if repo_root_str else None
    # ... rest of function

def public_function(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    return _cached_function(str(repo_root) if repo_root else \"\")
```

---

## Phase 2: Remove All Backward Compatibility Code

> **Status**: ✅ COMPLETED (Wave 2)
> **Analysis Finding**: 88 backward compatibility references found across codebase

### Task 2.1: Remove Config Wrapper Functions
**Priority**: P1 - HIGH
**Status**: ✅ DONE
**Effort**: 3-4 hours
**Files affected**: 5 domain config files + all callers

Remove 19 deprecated module-level wrapper functions:

| File | Functions to Remove |
|------|---------------------|
| `config/domains/workflow.py` | `get_task_states()`, `get_qa_states()`, `load_workflow_config()` + 3 more |
| `config/domains/project.py` | `get_project_name()`, `get_project_owner()`, `get_project_settings()` + 1 more |
| `config/domains/context7.py` | `load_triggers()`, `load_aliases()`, `load_packages()` |
| `config/domains/qa.py` | `load_config()`, `load_delegation_config()`, `load_validation_config()` |
| `config/domains/timeouts.py` | `get_timeout_settings()`, `reset_timeout_cache()` + 1 more |

**Actions**:
1. Search all usages of each wrapper function
2. Replace with direct class instantiation: `WorkflowConfig().task_states`
3. Remove wrapper functions
4. Update tests

---

### Task 2.2: Remove Backward Compatibility in Session Module
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 2-3 hours
**Files affected**: 4 files

| File | Lines | Issue |
|------|-------|-------|
| `session/manager.py` | 290-292 | Remove unused `process` and `naming_strategy` parameters |
| `session/next/compute.py` | 115-121 | Remove filesystem fallback inference |
| `session/models.py` | 203-211 | Remove `_state_to_status()` legacy mapping |
| `session/next/output.py` | 35 | Remove legacy expanded rules format |

---

### Task 2.3: Remove Backward Compatibility in Composition Module
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 4-5 hours
**Files affected**: 12 files

| File | Lines | Issue |
|------|-------|-------|
| `composition/audit/__init__.py` | 11, 35, 51 | Remove \"backward compatibility\" re-exports |
| `composition/includes.py` | 102-105, 246-251 | Remove legacy safe_include() regex |
| `composition/packs/metadata.py` | 31-32 | Remove legacy list-based triggers |
| `composition/packs/validation.py` | 74-76 | Remove legacy trigger format handling |
| `composition/registries/agents.py` | 67, 79, 106, 141-146, 173-179, 366-380 | Remove 6 compatibility aliases |
| `composition/registries/rules.py` | 218-220 | Remove static method wrapper |
| `composition/registries/validators.py` | 159+ | Remove fallback parameters |
| `composition/registries/guidelines.py` | 77 | Remove compatibility alias |
| `composition/registries/file_patterns.py` | 45 | Remove compatibility alias |
| `composition/ide/commands.py` | 218-238 | Remove legacy schema support |
| `composition/ide/hooks.py` | 246 | Remove fallback plain script |
| `composition/output/headers.py` | 21-23 | Remove fallback configuration loading |

---

### Task 2.4: Remove Backward Compatibility in QA Module
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 1 hour
**Files affected**: 1 file

```
DELETE: /src/edison/core/qa/validator/roster.py lines 19-25
```

Remove `_primary_files_from_doc()` wrapper - it's explicitly labeled \"for backward compatibility\" and just calls `parse_primary_files()`.

---

### Task 2.5: Remove Legacy Code in Adapters
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 1 hour
**Files affected**: 1 file

```
FIX: /src/edison/core/adapters/sync/zen/client.py lines 54-65
```

Remove \"Supports both legacy list form\" comment and legacy handling.

---

## Phase 3: Eliminate Hardcoded Values

> **Status**: NOT STARTED
> **Analysis Finding**: Multiple DEFAULT_* constants and hardcoded paths found

### Task 3.1: Move Hardcoded Defaults to YAML Config
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 6-8 hours
**Files affected**: 15+ files

#### Subtask 3.1.1: QA Module Hardcoded Values
| File | Lines | Value | Move to YAML |
|------|-------|-------|--------------|
| `qa/context7.py` | 30-50 | `_DEFAULT_TRIGGERS` dict | `data/config/context7.yml` |
| `qa/context7.py` | 52-73 | `_DEFAULT_ALIASES` dict | `data/config/context7.yml` |
| `qa/context7.py` | 212 | Prisma pattern detection | Config-driven patterns |
| `qa/evidence/analysis.py` | 54-65 | Required evidence files | `data/config/qa.yml` |
| `qa/validator/base.py` | 130-138 | Report template fallback | `data/templates/` |
| `qa/transaction.py` | 35 | `\"validation-session\"` | `data/config/qa.yml` |

#### Subtask 3.1.2: Utils Module Hardcoded Values
| File | Lines | Value | Move to YAML |
|------|-------|-------|--------------|
| `utils/subprocess.py` | 24-31, 36-57 | `FALLBACK_TIMEOUTS` | Must require config |
| `utils/time.py` | 14-18 | `DEFAULT_TIME_CONFIG` | Must require config |
| `utils/cli/output.py` | 16-36 | `DEFAULT_CLI_CONFIG` | Must require config |
| `utils/io/json.py` | 14-28 | `DEFAULT_JSON_CONFIG` | Must require config |
| `utils/paths/project.py` | 25 | `\".edison\"` | Config or explicit |
| `utils/__init__.py` | 114 | `MCP_TOOL_NAME` | Config |
| `utils/mcp.py` | 14 | `TOOL_NAME` (duplicate!) | Remove, use single source |
| `utils/text/core.py` | 16 | `ENGINE_VERSION` | Config |
| `utils/process/inspector.py` | 25-33 | Process detection patterns | Config |

#### Subtask 3.1.3: Session Module Hardcoded Values
| File | Lines | Value | Move to YAML |
|------|-------|-------|--------------|
| `session/recovery.py` | 90-91 | `300` seconds, `8` hours | Config |
| `session/recovery.py` | 244 | `60` minutes default | Config |
| `session/worktree/manager.py` | 68 | UUID suffix length `6` | Config |
| `session/transaction.py` | 234 | `5MB` minimum headroom | Config |

#### Subtask 3.1.4: Adapters Module Hardcoded Paths
| File | Lines | Value | Move to YAML |
|------|-------|-------|--------------|
| `adapters/prompt/claude.py` | 24 | `\".claude\"` | Config |
| `adapters/prompt/cursor.py` | 29 | `\".cursor\"` | Config |
| `adapters/prompt/zen.py` | 35 | `\".zen\"` paths | Config |
| `adapters/sync/claude.py` | 51 | `\".claude\"` fallback | Config |
| `adapters/sync/cursor.py` | 84, 88 | `\".cursor/agents\"`, `\".cursor/rules\"` | Config |
| `adapters/sync/zen/sync.py` | 17, 52, 119 | Multiple `.zen` paths | Config |

---

## Phase 4: Extract Shared Utilities (DRY)

> **Status**: NOT STARTED
> **Analysis Finding**: _cfg() pattern duplicated in 3-4 files, multiple shared utilities needed

### Task 4.1: Create session/_utils.py
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 3-4 hours
**Files affected**: 8+ files

Create `/src/edison/core/session/_utils.py` with:

```python
\"\"\"Shared utilities for session module.\"\"\"

def get_repo_dir(project_root: Optional[Path] = None) -> Path:
    \"\"\"Get repository directory.\"\"\"
    # Consolidate from recovery.py, worktree/config_helpers.py

def get_sessions_root(project_root: Optional[Path] = None) -> Path:
    \"\"\"Get sessions root directory.\"\"\"
    # Consolidate from multiple files

def get_session_config() -> Dict[str, Any]:
    \"\"\"Get session configuration.\"\"\"
    # Consolidate config access patterns
```

Update these files to use `_utils.py`:
- `session/recovery.py`
- `session/worktree/config_helpers.py`
- `session/paths.py`
- `session/repository.py`
- `session/transaction.py`
- `session/layout.py`
- `session/current.py`

---

### Task 4.2: Create qa/_utils.py Enhancements
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 2-3 hours
**Files affected**: 6 files

Enhance existing `/src/edison/core/qa/_utils.py` with:

```python
def get_qa_root_path(project_root: Optional[Path] = None) -> Path:
    \"\"\"Get QA root directory - single source of truth.\"\"\"
    # Consolidate from scoring.py, context7.py, repository.py, transaction.py

def sort_round_dirs(dirs: Iterable[Path]) -> List[Path]:
    \"\"\"Sort round directories by numeric suffix.\"\"\"
    # Extract from evidence/rounds.py

def read_json_safe(path: Path, default: Any = None) -> Any:
    \"\"\"Safely read JSON with sensible defaults.\"\"\"
    # Extract from evidence/io.py, evidence/followups.py, evidence/analysis.py
```

Update these files:
- `qa/scoring.py`
- `qa/context7.py`
- `qa/repository.py`
- `qa/transaction.py`
- `qa/evidence/rounds.py`
- `qa/evidence/io.py`

---

### Task 4.3: Fix Utils Atomic Write Duplication
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE
**Effort**: 1 hour
**Files affected**: 2 files

```
REFACTOR: /src/edison/core/utils/io/locking.py lines 259-285
```

Replace `write_text_locked()` implementation with composition:

```python
def write_text_locked(path: Path, content: str) -> None:
    \"\"\"Write text atomically while holding an exclusive lock.\"\"\"
    target = Path(path)
    with acquire_file_lock(target):
        write_text(target, content)  # Use existing atomic write
```

---

### Task 4.4: Consolidate Config Loading Pattern
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE
**Effort**: 3-4 hours
**Files affected**: 6 files

The `_cfg()` lazy config loading pattern is duplicated in:
- `utils/time.py`
- `utils/io/json.py`
- `utils/cli/output.py`
- `utils/subprocess.py`
- `utils/io/locking.py`

Create shared pattern in `utils/config.py`:

```python
def get_module_config(section: str, defaults: Dict[str, Any]) -> Dict[str, Any]:
    \"\"\"Get configuration for a module with defaults.\"\"\"
    try:
        from edison.core.config import ConfigManager
        cfg = ConfigManager().load_config(validate=False)
        return cfg.get(section, defaults)
    except Exception:
        return defaults
```

---

### Task 4.5: Create SyncAdapter Base Class
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE (Analysis confirmed: base.py does NOT exist)
**Effort**: 4-5 hours
**Files affected**: 4 files

Create `/src/edison/core/adapters/sync/base.py`:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

@dataclass
class SyncAdapter(ABC):
    \"\"\"Base for all full-featured sync adapters.\"\"\"
    repo_root: Path
    config: Dict[str, Any]

    @classmethod
    def create(cls, repo_root: Optional[Path] = None) -> \"SyncAdapter\":
        \"\"\"Factory method with standard initialization.\"\"\"
        root = repo_root or PathResolver.resolve_project_root()
        config = cls._load_config(root)
        return cls(repo_root=root, config=config)

    @staticmethod
    @abstractmethod
    def _load_config(repo_root: Path) -> Dict[str, Any]:
        \"\"\"Subclasses override to provide config.\"\"\"

    @abstractmethod
    def sync_all(self) -> Dict[str, Any]:
        \"\"\"Unified sync interface.\"\"\"
```

Update these files to inherit from `SyncAdapter`:
- `adapters/sync/claude.py`
- `adapters/sync/cursor.py`
- `adapters/sync/zen/client.py`

---

### Task 4.6: Consolidate PromptAdapter render_* Methods
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE
**Effort**: 2-3 hours
**Files affected**: 5 files

Move default implementations to base class:

```python
# In adapters/base.py
class PromptAdapter(ABC):
    def render_agent(self, agent_name: str) -> str:
        \"\"\"Default implementation - read agent file.\"\"\"
        source = self.agents_dir / f\"{agent_name}.md\"
        if not source.exists():
            raise FileNotFoundError(f\"Agent not found: {agent_name}\")
        content = source.read_text(encoding=\"utf-8\")
        return self._post_process_agent(agent_name, content)

    def _post_process_agent(self, agent_name: str, content: str) -> str:
        \"\"\"Hook for subclasses to format agent content.\"\"\"
        return content

    # Similar for render_validator, render_client
```

Update adapters to use hooks instead of overriding entire methods.

---

## Phase 5: Restructure Large Directories

> **Status**: NOT STARTED
> **Analysis Finding**: session/ has 18 files at root (needs subdirs), qa/ has 10 files at root

### Task 5.1: Restructure session/ Module (18 files)
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE (Analysis confirmed: no subdirectories exist yet)
**Effort**: 4-6 hours
**Files affected**: 18 files + all imports

Current structure has 18 files at root level. Propose reorganization:

```
session/
├── __init__.py              # Public API
├── _config.py               # Keep at root
├── _utils.py                # NEW: shared utilities
│
├── core/                    # NEW: Core session logic
│   ├── __init__.py
│   ├── models.py            # Move from root
│   ├── id.py                # Move from root
│   ├── naming.py            # Move from root
│   ├── layout.py            # Move from root
│   └── context.py           # Move from root
│
├── persistence/             # NEW: Storage layer
│   ├── __init__.py
│   ├── repository.py        # Move from root
│   ├── database.py          # Move from root
│   ├── archive.py           # Move from root
│   └── graph.py             # Move from root
│
├── lifecycle/               # NEW: Lifecycle management
│   ├── __init__.py
│   ├── manager.py           # Move from root
│   ├── transaction.py       # Move from root
│   ├── recovery.py          # Move from root
│   ├── autostart.py         # Move from root
│   └── verify.py            # Move from root (keep logic in core!)
│
├── paths.py                 # Keep at root (widely used)
├── current.py               # Keep at root (widely used)
│
├── next/                    # Keep existing
│   └── ...
│
└── worktree/                # Keep existing
    └── ...
```

**Note on verify.py**: Keep in core since it contains business logic (`verify_session_health()`). The `main()` function can stay as it's just a thin CLI wrapper.

---

### Task 5.2: Restructure qa/ Module (10 files at root)
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE
**Effort**: 3-4 hours
**Files affected**: 10 files + all imports

```
qa/
├── __init__.py
├── _utils.py                # Enhanced shared utilities
├── models.py                # Keep at root
│
├── core/                    # NEW: Core QA logic
│   ├── __init__.py
│   ├── repository.py        # Move from root
│   ├── manager.py           # Move from root
│   ├── transaction.py       # Move from root
│   └── context7.py          # Move from root
│
├── scoring/                 # NEW: Scoring subsystem
│   ├── __init__.py
│   ├── scoring.py           # Move from root
│   └── promoter.py          # Move from root (bundler.py)
│
├── evidence/                # Keep existing
│   └── ...
│
└── validator/               # Keep existing
    └── ...
```

---

### Task 5.3: Restructure utils/ Root Files
**Priority**: P3 - LOW
**Status**: ⬜ NOT DONE
**Effort**: 2-3 hours
**Files affected**: 7 root files

Move root-level utilities into subdirectories:

```
utils/
├── __init__.py
│
├── config/                  # NEW
│   ├── __init__.py
│   └── helpers.py           # Move from utils/config.py
│
├── subprocess/              # NEW
│   ├── __init__.py
│   └── runner.py            # Move from utils/subprocess.py
│
├── resilience/              # NEW
│   ├── __init__.py
│   └── retry.py             # Move from utils/resilience.py
│
├── dependencies.py          # Keep (small)
├── merge.py                 # Keep (small)
├── mcp.py                   # Keep (small)
├── time.py                  # Keep (small)
│
├── io/                      # Keep existing
├── paths/                   # Keep existing
├── cli/                     # Keep existing
├── git/                     # Keep existing
├── text/                    # Keep existing
└── process/                 # Keep existing
```

---

## Phase 6: Decompose Long Functions

> **Status**: NOT STARTED

### Task 6.1: Split session/next/compute.py _child_ready()
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 4-5 hours
**Files affected**: 1 file

The `_child_ready()` nested function is **343 lines** - extract to module level and split:

```python
# Extract from compute.py lines 116-458

def _check_task_readiness(task_id: str, session: Dict, cfg: SessionConfig) -> TaskReadiness:
    \"\"\"Check if a task is ready for processing.\"\"\"
    # ~80 lines

def _check_qa_readiness(task_id: str, session: Dict, cfg: SessionConfig) -> QAReadiness:
    \"\"\"Check if QA is ready for validation.\"\"\"
    # ~80 lines

def _compute_blockers(task_id: str, session: Dict) -> List[str]:
    \"\"\"Compute blockers for a task.\"\"\"
    # ~60 lines

def _build_next_actions(readiness: TaskReadiness) -> List[NextAction]:
    \"\"\"Build list of next actions from readiness.\"\"\"
    # ~40 lines
```

---

### Task 6.2: Split session/autostart.py start()
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 3-4 hours
**Files affected**: 1 file

The `start()` method is **142 lines** with multiple responsibilities:

```python
def start(self, ...) -> SessionStartResult:
    \"\"\"Start a new session.\"\"\"
    self._validate_inputs(...)
    session = self._create_session(...)
    worktree = self._setup_worktree(session, ...)
    self._launch_orchestrator(session, worktree, ...)
    return SessionStartResult(...)

def _validate_inputs(self, task_ids, ...) -> None:
    \"\"\"Validate session start inputs.\"\"\"
    # ~30 lines

def _create_session(self, task_ids, ...) -> Session:
    \"\"\"Create session entity.\"\"\"
    # ~40 lines

def _setup_worktree(self, session, ...) -> Optional[Path]:
    \"\"\"Setup git worktree if enabled.\"\"\"
    # ~35 lines

def _launch_orchestrator(self, session, worktree, ...) -> None:
    \"\"\"Launch orchestrator process.\"\"\"
    # ~25 lines
```

---

### Task 6.3: Split session/verify.py verify_session_health()
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE
**Effort**: 2-3 hours
**Files affected**: 1 file

The function is **129 lines** - split by category:

```python
def verify_session_health(session_id: str) -> SessionHealth:
    \"\"\"Verify session for phase guards.\"\"\"
    session = _load_session(session_id)
    health = SessionHealth(session_id=session_id)

    health.add_findings(_check_state_mismatches(session))
    health.add_findings(_check_unexpected_states(session))
    health.add_findings(_check_missing_qa(session))
    health.add_findings(_check_evidence(session))
    health.add_findings(_check_blockers(session))

    if health.is_healthy:
        _mark_session_closing(session)

    return health

def _check_state_mismatches(session: Dict) -> List[Finding]:
    \"\"\"Check for metadata/directory state mismatches.\"\"\"
    # ~25 lines

def _check_missing_qa(session: Dict) -> List[Finding]:
    \"\"\"Check for tasks in done without QA.\"\"\"
    # ~20 lines
```

---

### Task 6.4: Split utils/paths/resolver.py resolve_project_root()
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE
**Effort**: 2-3 hours
**Files affected**: 1 file

The function is **129 lines** - split into strategies:

```python
def resolve_project_root(start_path: Optional[Path] = None) -> Path:
    \"\"\"Resolve project root using multiple strategies.\"\"\"
    strategies = [
        _resolve_from_environment,
        _resolve_from_git,
        _resolve_from_markers,
        _resolve_from_cwd,
    ]
    for strategy in strategies:
        result = strategy(start_path)
        if result:
            return result
    raise ProjectRootNotFound(...)

def _resolve_from_environment(start_path: Optional[Path]) -> Optional[Path]:
    \"\"\"Try to resolve from environment variables.\"\"\"
    # ~25 lines

def _resolve_from_git(start_path: Optional[Path]) -> Optional[Path]:
    \"\"\"Try to resolve from git repository root.\"\"\"
    # ~25 lines

def _resolve_from_markers(start_path: Optional[Path]) -> Optional[Path]:
    \"\"\"Try to resolve from project marker files.\"\"\"
    # ~35 lines
```

---

### Task 6.5: Split Other Long Functions
**Priority**: P3 - LOW
**Status**: ⬜ NOT DONE
**Effort**: 6-8 hours total
**Files affected**: 15+ files

Additional functions to split (>50 lines):

| File | Function | Lines | Action |
|------|----------|-------|--------|
| `session/next/output.py` | `format_human_readable()` | 169 | Split by section |
| `session/recovery.py` | `recover_incomplete_validation_transactions()` | 85 | Extract helpers |
| `session/graph.py` | `build_validation_bundle()` | 65 | Extract builders |
| `session/id.py` | `validate_session_id()` | 61 | Extract validators |
| `utils/io/locking.py` | `acquire_file_lock()` | 88 | Extract lock strategies |
| `utils/config.py` | `get_semantic_state()` | 65 | Extract parsers |
| `qa/_utils.py` | `parse_primary_files()` | 67 | Extract format handlers |
| `qa/evidence/analysis.py` | `missing_evidence_blockers()` | 57 | Extract checkers |
| `qa/repository.py` | `_parse_qa_markdown()` | 78 | Extract parsers |
| `qa/validator/delegation.py` | `simple_delegation_hint()` | 82 | Extract matchers |
| `qa/validator/delegation.py` | `enhance_delegation_hint()` | 71 | Extract enhancers |
| `qa/validator/roster.py` | `build_validator_roster()` | 53 | Extract builders |
| `adapters/sync/zen/composer.py` | `compose_zen_prompt()` | 60 | Extract composers |
| `adapters/sync/zen/discovery.py` | `get_applicable_guidelines()` | 72 | Extract filters |
| `adapters/sync/zen/sync.py` | `verify_cli_prompts()` | 84 | Extract validators |

---

## Phase 7: Standardize Error Handling

> **Status**: NOT STARTED
> **Analysis Finding**: 153 files have bare `except Exception:` patterns

### Task 7.1: Replace Bare Exception Handlers
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE
**Effort**: 4-5 hours
**Files affected**: 30+ files (153 total occurrences across codebase)

Replace all `except Exception: pass` patterns with specific handlers and logging.

**Pattern to apply**:
```python
# BEFORE
try:
    data = load_config()
except Exception:
    data = {}

# AFTER
import logging
logger = logging.getLogger(__name__)

try:
    data = load_config()
except (FileNotFoundError, OSError) as e:
    logger.warning(f\"Failed to load config: {e}\")
    data = {}
except ValueError as e:
    logger.error(f\"Invalid config format: {e}\")
    raise
```

**Files with bare exceptions to fix**:
- `session/manager.py` (1)
- `session/recovery.py` (4)
- `session/current.py` (4)
- `session/database.py` (4)
- `session/transaction.py` (4)
- `session/autostart.py` (3)
- `session/worktree/cleanup.py` (6)
- `qa/context7.py` (6)
- `qa/evidence/analysis.py` (1)
- `utils/subprocess.py` (1)
- `utils/config.py` (1)
- `utils/io/yaml.py` (2)
- `utils/cli/output.py` (1)
- `utils/mcp.py` (1)
- `adapters/_config.py` (1)
- `adapters/prompt/codex.py` (1)
- `adapters/sync/zen/sync.py` (1)
- `composition/packs/validation.py` (1)
- `composition/packs/composition.py` (1)
- `composition/packs/loader.py` (1)
- `composition/packs/activation.py` (3)
- `composition/includes.py` (2)
- `composition/ide/commands.py` (1)
- `composition/ide/settings.py` (1)
- `composition/ide/hooks.py` (1)
- `composition/registries/agents.py` (1)
- `composition/registries/validators.py` (1)
- `composition/registries/rules.py` (1)

---

### Task 7.2: Fix SystemExit Handling
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 1 hour
**Files affected**: 2 files

```
FIX: /src/edison/core/session/transaction.py lines 99-100, 129-130
```

SystemExit is being caught and suppressed with `pass`, preventing proper cleanup.

**BEFORE**:
```python
except SystemExit:
    pass
```

**AFTER**:
```python
except SystemExit:
    raise  # Always re-raise SystemExit
```

---

## Phase 8: Remove Duplicate Code

> **Status**: NOT STARTED

### Task 8.1: Entity Module - Remove Method Alias
**Priority**: P3 - LOW
**Status**: ⬜ NOT DONE
**Effort**: 1 hour
**Files affected**: 1 file + callers

```
REFACTOR: /src/edison/core/entity/repository.py
```

Remove `list_all()` alias for `get_all()`:
1. Search all usages of `list_all()`
2. Replace with `get_all()`
3. Remove `list_all()` method

---

### Task 8.2: State Module - Unify Validation Entry Points
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE
**Effort**: 2-3 hours
**Files affected**: 2 files + callers

Currently two entry points:
- `StateValidator.ensure_transition()` - raises exceptions
- `transitions.validate_transition()` - returns tuple

Consolidate to single canonical entry point in `StateValidator`.

---

### Task 8.3: Rules Module - Fix Hardcoded Dispatch
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE
**Effort**: 2-3 hours
**Files affected**: 2 files

Refactor `engine.py._check_rule()` to use registry pattern instead of hardcoded dispatch.

---

### Task 8.4: IDE Composer - Consolidate Merge Logic
**Priority**: P3 - LOW
**Status**: ⬜ NOT DONE
**Effort**: 2 hours
**Files affected**: 4 files

Create generic merge method in `IDEComposerBase`:

```python
def _merge_definitions(
    self,
    merged: Dict[str, Dict[str, Any]],
    definitions: Union[List[Dict], Dict[str, Dict]],
    key_getter: Callable[[Dict], str] = lambda d: d.get(\"id\"),
) -> Dict[str, Dict[str, Any]]:
    \"\"\"Generic merge for YAML definitions by key.\"\"\"
```

Update `CommandComposer`, `HookComposer`, `SettingsComposer` to use it.

---

## Phase 9: Type Hints and Documentation

> **Status**: NOT STARTED

### Task 9.1: Add Missing Type Hints
**Priority**: P3 - LOW
**Status**: ⬜ NOT DONE
**Effort**: 4-5 hours
**Files affected**: 20+ files

Focus areas:
- All public API functions
- All class methods
- Replace `dict` with `Dict[str, Any]`
- Replace `list` with `List[T]`
- Use `Optional[T]` instead of `T | None` for consistency

---

### Task 9.2: Remove Type Ignore Comments
**Priority**: P3 - LOW
**Status**: ⬜ NOT DONE
**Effort**: 2-3 hours
**Files affected**: 10+ files

Investigate and fix underlying type issues for:
- `# type: ignore[arg-type]`
- `# type: ignore[no-untyped-call]`
- `# type: ignore[union-attr]`
- `# type: ignore[misc]`

---

### Task 9.3: Add Module Docstrings
**Priority**: P3 - LOW
**Status**: ⬜ NOT DONE
**Effort**: 2-3 hours
**Files affected**: 20+ files

Add docstrings explaining:
- Module purpose
- Key classes/functions
- Usage examples
- Relationship to other modules

---

## Phase 10: Fix Circular Import Architecture

> **Status**: NOT STARTED

### Task 10.1: Refactor Lazy Imports
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE
**Effort**: 6-8 hours
**Files affected**: 30+ files

There are **16+ lazy imports** in utils alone, indicating architectural issues.

**Strategy**:
1. Map all circular dependencies
2. Extract shared types to `core/types.py`
3. Use dependency injection where appropriate
4. Consider splitting modules further

Key areas:
- `utils/` → `config/` → `session/` cycle
- `session/` → `task/` → `qa/` cycle
- `adapters/` → `composition/` cycle

---

## Phase 11: CLI Business Logic Migration (NEW)

> **Status**: NOT STARTED
> **Analysis Finding**: 4 CLI files contain deep business logic that belongs in core/

### Task 11.1: Move CLI Business Logic to Core
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 4-6 hours
**Files affected**: 4 CLI files + new core modules

CLI commands should only be thin wrappers calling core logic. The following files have business logic that needs migration:

| CLI File | Issue | Target Core Module |
|----------|-------|-------------------|
| `cli/session/verify.py` | Contains verification logic | `core/session/verify.py` (create) |
| `cli/rules/check.py` | Contains rule checking logic | `core/rules/checker.py` (create) |
| `cli/session/recovery/*.py` | Contains recovery logic | `core/session/recovery.py` (extend) |
| `cli/git/worktree_*.py` | Contains worktree management | `core/session/worktree/` (extend) |

**Actions**:
1. Extract business logic from each CLI file
2. Create or extend core module with the logic
3. Update CLI to be thin wrapper only (parse args, call core, format output)
4. Update all imports and tests

---

## Phase 12: Test Anti-Pattern Fixes (NEW)

> **Status**: NOT STARTED
> **Analysis Finding**: 79 test files use mocks - VIOLATES CLAUDE.md Principle #2 (NO MOCKS)

### Task 12.1: Remove Mocks from Test Files
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 15-20 hours
**Files affected**: 79 test files

Per CLAUDE.md Principle #2: "Test real behavior, real code, real libs - NO MOCKS EVER"

**Files with mocks to fix** (sample - full list has 79 files):
- `tests/unit/cli/orchestrator/test_launcher.py`
- `tests/unit/composition/*/test_*.py` (multiple)
- `tests/unit/config/*/test_*.py` (multiple)
- `tests/session/*/test_*.py` (multiple)
- `tests/task/test_*.py` (multiple)

**Strategy for each file**:
1. Identify what is being mocked
2. Create real test fixtures/data instead
3. Use real implementations with test configuration
4. For external services, use integration tests or test doubles that exercise real code paths

### Task 12.2: Create Real Test Fixtures
**Priority**: P1 - HIGH
**Status**: ⬜ NOT DONE
**Effort**: 8-10 hours
**Files affected**: tests/conftest.py + test helpers

Create reusable real fixtures to replace mocks:

```python
# tests/conftest.py enhancements
@pytest.fixture
def real_session_repo(tmp_path):
    """Create real session repository for testing."""
    # Setup real repo structure

@pytest.fixture
def real_task_repo(tmp_path):
    """Create real task repository for testing."""
    # Setup real task structure

@pytest.fixture
def real_config(tmp_path):
    """Create real config files for testing."""
    # Setup real YAML config
```

---

## Phase 13: Missing Domain Configs (NEW)

> **Status**: NOT STARTED
> **Analysis Finding**: TimeConfig, JsonIOConfig, CliConfig domain configs planned but never created

### Task 13.1: Create Missing Domain Config Classes
**Priority**: P2 - MEDIUM
**Status**: ⬜ NOT DONE
**Effort**: 3-4 hours
**Files affected**: 4 new files + utils modules

The following domain configs should exist to eliminate hardcoded defaults:

#### Subtask 13.1.1: Create TimeConfig
```
CREATE: /src/edison/core/config/domains/time.py
```
- Move `DEFAULT_TIME_CONFIG` from `utils/time.py`
- Extend `BaseDomainConfig`
- Update `utils/time.py` to use `TimeConfig`

#### Subtask 13.1.2: Create JsonIOConfig
```
CREATE: /src/edison/core/config/domains/json_io.py
```
- Move `DEFAULT_JSON_CONFIG` from `utils/io/json.py`
- Extend `BaseDomainConfig`
- Update `utils/io/json.py` to use `JsonIOConfig`

#### Subtask 13.1.3: Create CliConfig
```
CREATE: /src/edison/core/config/domains/cli.py
```
- Move `DEFAULT_CLI_CONFIG` from `utils/cli/output.py`
- Extend `BaseDomainConfig`
- Update `utils/cli/output.py` to use `CliConfig`

#### Subtask 13.1.4: Update domains/__init__.py
```
UPDATE: /src/edison/core/config/domains/__init__.py
```
- Add exports for TimeConfig, JsonIOConfig, CliConfig

---

## Parallel Execution Plan

> **Updated**: 2025-11-29 - Added Waves 8-9 for new phases

### Wave 1 (Can run in parallel) - CRITICAL FIXES
- Task 1.1.1: Delete task/compat.py
- Task 1.1.2: Delete session/store/
- Task 1.2: Fix test imports
- Task 1.3: Fix composition loader
- Task 1.4: Fix LRU cache

### Wave 2 (After Wave 1) - REMOVE LEGACY
- Task 2.1: Remove config wrappers
- Task 2.2: Remove session compat
- Task 2.3: Remove composition compat
- Task 2.4: Remove QA compat
- Task 2.5: Remove adapters compat

### Wave 3 (After Wave 2) - HARDCODED VALUES
- Task 3.1.1: QA hardcoded values
- Task 3.1.2: Utils hardcoded values
- Task 3.1.3: Session hardcoded values
- Task 3.1.4: Adapters hardcoded values
- Task 13.1: Create missing domain configs (NEW)

### Wave 4 (After Wave 3) - DRY UTILITIES
- Task 4.1: Create session/_utils.py
- Task 4.2: Enhance qa/_utils.py
- Task 4.3: Fix atomic write duplication
- Task 4.4: Consolidate config loading

### Wave 5 (After Wave 4) - STRUCTURE
- Task 4.5: Create SyncAdapter base
- Task 4.6: Consolidate PromptAdapter
- Task 5.1: Restructure session/
- Task 5.2: Restructure qa/
- Task 11.1: Move CLI business logic to core (NEW)

### Wave 6 (After Wave 5) - FUNCTION DECOMPOSITION
- Task 6.1-6.5: Split long functions
- Task 7.1-7.2: Standardize error handling
- Task 8.1-8.4: Remove duplicates

### Wave 7 (After Wave 6) - POLISH
- Task 9.1-9.3: Type hints and docs
- Task 10.1: Fix circular imports
- Task 5.3: Restructure utils/ (optional)

### Wave 8 (Can run in parallel with Wave 7) - TEST FIXES (NEW)
- Task 12.1: Remove mocks from test files (79 files)
- Task 12.2: Create real test fixtures

---

## Summary Statistics

> **Updated**: 2025-11-29 - Added new phases from analysis

| Category | Count | Estimated Effort | Status |
|----------|-------|------------------|--------|
| Critical fixes (Phase 1) | 4 tasks | 7-9 hours | ✅ DONE |
| Remove backward compat (Phase 2) | 5 tasks | 11-14 hours | ⬜ NOT STARTED |
| Remove hardcoded values (Phase 3) | 4 subtasks | 6-8 hours | ⬜ NOT STARTED |
| Extract utilities/DRY (Phase 4) | 6 tasks | 15-19 hours | ⬜ NOT STARTED |
| Restructure directories (Phase 5) | 3 tasks | 9-13 hours | ⬜ NOT STARTED |
| Split long functions (Phase 6) | 5 tasks | 17-23 hours | ⬜ NOT STARTED |
| Standardize error handling (Phase 7) | 2 tasks | 5-6 hours | ⬜ NOT STARTED |
| Remove duplicates (Phase 8) | 4 tasks | 7-9 hours | ⬜ NOT STARTED |
| Type hints & docs (Phase 9) | 3 tasks | 8-11 hours | ⬜ NOT STARTED |
| Fix circular imports (Phase 10) | 1 task | 6-8 hours | ⬜ NOT STARTED |
| CLI business logic migration (Phase 11) | 1 task | 4-6 hours | ⬜ NOT STARTED |
| Test anti-pattern fixes (Phase 12) | 2 tasks | 23-30 hours | ⬜ NOT STARTED |
| Missing domain configs (Phase 13) | 1 task | 3-4 hours | ⬜ NOT STARTED |
| **TOTAL** | **41 tasks** | **121-160 hours** | ⬜ 0% COMPLETE |

---

## Expected Outcomes

After completing this refactoring:

1. **Code reduction**: ~1,500-2,000 LOC removed
2. **No legacy code**: 100% compliance with Principle #3 (NO LEGACY)
3. **No hardcoded values**: 100% compliance with Principle #4 (NO HARDCODED VALUES)
4. **Zero DRY violations**: All shared utilities extracted (Principle #6)
5. **All functions < 50 lines**: Better testability
6. **Consistent error handling**: Easier debugging
7. **Clear module boundaries**: Better maintainability
8. **Complete type coverage**: Better IDE support
9. **NO MOCKS in tests**: 100% compliance with Principle #2 (NO MOCKS)
10. **CLI as thin wrappers**: All business logic in core/ only

---

## Next Steps

> **IMPORTANT**: Previous changes were lost. Starting from scratch.

1. ✅ Review this updated plan (you are here)
2. ⬜ Create git branch: `refactor/core-cleanup`
3. ⬜ Execute Wave 1 (Critical fixes) - Tasks 1.1-1.4
4. ⬜ **COMMIT AFTER EACH TASK** to avoid losing work
5. ⬜ Execute remaining waves sequentially
6. ⬜ Run full test suite after each wave
7. ⬜ Commit frequently with descriptive messages

### Commit Strategy (IMPORTANT)

**Commits happen ONLY after each completed WAVE, not after individual tasks.**

Rules:
1. **Only the orchestrator commits** - subagents MUST NOT touch git
2. **Commit after validating ALL subagent work** in a wave is complete
3. **Verify before committing**: Re-read modified files, run tests if applicable
4. **Commit message format**: `refactor(core): Wave N - [summary of changes]`
5. **DO NOT push** - just commit locally (user will push when ready)

### Subagent Delegation Protocol

When delegating to subagents:
1. **Require factual, concise reports** - no verbose explanations
2. **Report format**:
   - Files changed (list)
   - Status: DONE / BLOCKED / PARTIAL
   - Errors encountered (if any)
   - **Follow-ups needed** (if any - list specific remaining work)
3. **No git operations** by subagents - only file read/write/edit
4. **Subagents report REAL status** - no optimistic reporting
5. **No half-finished work** - if blocked, report what's needed to unblock

### Follow-up Handling

After each wave:
1. Collect all subagent reports
2. If any task reports PARTIAL or has follow-ups:
   - Add follow-ups to next wave
   - Re-delegate until fully DONE
3. Only mark wave complete when ALL tasks are fully DONE
4. **Never leave work half-implemented**

### Context Preservation

To preserve orchestrator context:
1. **Update this tracking document** after each wave completion
2. **Re-read this document** after any context compaction
3. **Keep subagent prompts minimal** - reference this doc instead of repeating details
4. **Mark tasks as DONE in this document** as waves complete

---

## Changelog

| Date | Changes |
|------|---------|
| 2025-11-29 | Full restart - all tasks marked NOT DONE |
| 2025-11-29 | Added Phase 11: CLI Business Logic Migration |
| 2025-11-29 | Added Phase 12: Test Anti-Pattern Fixes (79 files with mocks) |
| 2025-11-29 | Added Phase 13: Missing Domain Configs |
| 2025-11-29 | Updated Wave plan with new phases |
| 2025-11-29 | Updated summary statistics (41 tasks, 121-160 hours) |
| 2025-11-29 | Added commit/delegation/context preservation protocols |
