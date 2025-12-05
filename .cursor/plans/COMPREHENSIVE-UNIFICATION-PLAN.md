# Edison Framework - Comprehensive Unification & Remediation Plan

**Created:** 2025-12-05  
**Status:** IN PROGRESS  
**Goal:** Complete migration to fully configurable, unified, DRY, SOLID, long-term maintainable architecture

---

## Executive Summary

This plan consolidates ALL findings from the architectural audit into a single, executable remediation plan. Every action item includes:
- Exact file paths and line numbers
- Specific code changes required
- Dependencies on other actions
- Verification criteria

**⚠️ CRITICAL DISCOVERY:** The workflow.yaml **actions** (like `record_completion_time`, `record_blocker_reason`, `notify_session_start`, etc.) are **NEVER EXECUTED** because:
1. `StateValidator.ensure_transition()` passes `execute_actions=False`
2. All CLI commands use `validate_transition()` which delegates to `ensure_transition()`
3. CLI commands then manually set state, bypassing the action execution entirely

This is the **highest priority fix** - the entire action system is non-functional.

**Total Action Items:** 80
**Priority Breakdown:**
- P0 (Critical): 8 items - Guard bypasses & circular dependencies (+1: P0-GB-005)
- P1 (High): 24 items - Backward compatibility & hardcoded values (+2: P1-HV-008, P1-HV-009)
- P2 (Medium): 32 items - DRY violations, QA fixes, file abstraction & pattern inconsistencies (+1: P2-REC-003)
- P3 (Low): 7 items - Large file refactoring
- P4 (Enhancement): 9 items - Inheritance improvements & verification

---

## Implementation Phases

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 1: CRITICAL (P0)                                                   │
│ Fix guard bypasses and circular dependencies                            │
│ Duration: ~2 hours                                                       │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 2: HIGH PRIORITY (P1)                                              │
│ Remove backward compatibility code & hardcoded values                   │
│ Duration: ~3 hours                                                       │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 3: MEDIUM PRIORITY (P2)                                           │
│ DRY consolidation, file abstraction & unified transition patterns       │
│ Duration: ~3 hours                                                       │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 4: LOW PRIORITY (P3)                                               │
│ Large file refactoring                                                   │
│ Duration: ~1 hour                                                        │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 5: ENHANCEMENTS (P4)                                               │
│ Inheritance improvements & verification tasks                            │
│ Duration: ~1 hour                                                        │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 6: VERIFICATION                                                    │
│ Run all tests, verify all checklists                                    │
│ Duration: ~30 minutes                                                    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

# PHASE 1: CRITICAL (P0) - Guard Bypasses & Circular Dependencies

## 1.1 Guard Bypass Fixes

### P0-GB-001: Fix verify.py guard bypass
- [ ] **File:** `src/edison/core/session/lifecycle/verify.py`
- [ ] **Lines:** 166-173
- [ ] **Current Code:**
  ```python
  closing_state = WorkflowConfig().get_semantic_state("session", "closing")
  session["state"] = closing_state
  session.setdefault("meta", {})["lastActive"] = io_utc_timestamp()
  graph.save_session(session_id, session)
  ```
- [ ] **Required Change:** Replace with `transition_session()` call that validates guards
- [ ] **Dependencies:** None
- [ ] **Verification:** `edison session verify` checks guards before state change

### P0-GB-002: Fix recovery.py guard bypass
- [ ] **File:** `src/edison/core/session/lifecycle/recovery.py`
- [ ] **Lines:** 241-252, 308
- [ ] **Current Code:**
  ```python
  # Line 244:
  sess["state"] = closing_state
  # Line 308:
  meta['state'] = 'Recovery'
  ```
- [ ] **Required Change:** Use `transition_session()` with proper validation for both locations
- [ ] **Dependencies:** None
- [ ] **Verification:** Recovery flow respects guards

### P0-GB-003: Fix task/claim.py QA path guard bypass
- [ ] **File:** `src/edison/cli/task/claim.py`
- [ ] **Lines:** 120-126
- [ ] **Current Code:**
  ```python
  wip_state = WorkflowConfig().get_semantic_state("qa", "wip")
  old_state = qa.state
  qa.state = wip_state
  qa.session_id = session_id
  qa.record_transition(old_state, wip_state, reason="claimed")
  qa_repo.save(qa)
  ```
- [ ] **Required Change:** Add `validate_transition("qa", old_state, wip_state, context=...)` before modification
- [ ] **Dependencies:** None
- [ ] **Verification:** QA claim validates guards

### P0-GB-004: Fix or remove advance_state() method
- [ ] **File:** `src/edison/core/qa/workflow/repository.py`
- [ ] **Lines:** 178-202
- [ ] **Current Code:** `advance_state()` bypasses guard system entirely
- [ ] **Required Change:** Integrate `validate_transition()` call OR remove if unused
- [ ] **Dependencies:** Search for all callers first
- [ ] **Verification:** No unguarded state transitions via this method

### P0-GB-005: Fix cli/session/recovery/recover.py guard bypass
- [ ] **File:** `src/edison/cli/session/recovery/recover.py`
- [ ] **Line:** 63
- [ ] **Current Code:**
  ```python
  session["state"] = "recovery"
  ```
- [ ] **Required Change:** Use `transition_session()` with proper validation instead of direct state assignment
- [ ] **Dependencies:** None
- [ ] **Verification:** `edison session recovery recover` validates guards before state change

## 1.2 Circular Dependency Fixes

### P0-CD-001: Break composition→config→utils cycle
- [ ] **Files:**
  - `src/edison/core/composition/core/base.py`
  - `src/edison/core/config/manager.py`
  - `src/edison/core/utils/paths/resolver.py`
- [ ] **Problem:** `composition` imports from `config` and `utils`, which import from `composition`
- [ ] **Required Change:**
  1. Move shared utilities to `core/utils/common.py` with no internal dependencies
  2. Use lazy imports (`TYPE_CHECKING`) for type hints causing cycles
  3. Consider dependency injection for runtime dependencies
- [ ] **Dependencies:** None
- [ ] **Verification:** `python -c "from edison.core.composition import *"` succeeds

### P0-CD-002: Break composition→registries cycle
- [ ] **Files:**
  - `src/edison/core/composition/registries/_base.py`
  - `src/edison/core/registries/validators.py`
- [ ] **Required Change:** Use `TYPE_CHECKING` guard for circular type imports
- [ ] **Dependencies:** P0-CD-001
- [ ] **Verification:** No import errors

### P0-CD-003: Break state→entity→session cycle
- [ ] **Files:**
  - `src/edison/core/state/handlers.py`
  - `src/edison/core/entity/repository.py`
  - `src/edison/core/session/core/models.py`
- [ ] **Required Change:** Decouple session models from state handlers
- [ ] **Dependencies:** P0-CD-001, P0-CD-002
- [ ] **Verification:** Clean import graph

---

# PHASE 2: HIGH PRIORITY (P1) - Backward Compatibility & Hardcoded Values

## 2.1 Backward Compatibility Removal

### P1-BC-001: Remove deprecated Session fields
- [ ] **File:** `src/edison/core/session/core/models.py`
- [ ] **Lines:** 144-146
- [ ] **Current Code:** DEPRECATED `tasks` and `qa_records` fields in Session
- [ ] **Required Change:** DELETE fields completely
- [ ] **Dependencies:** P0-CD-003
- [ ] **Migration Pattern:** Replace all `session.tasks` accesses with `TaskIndex.list_tasks_in_session(session_id)`
- [ ] **Migration Pattern:** Replace all `session.qa_records` accesses with `QARepository` queries
- [ ] **Verification:** No code accesses `session.tasks` or `session.qa_records`

### P1-BC-002: Remove legacy graph.py dicts
- [ ] **File:** `src/edison/core/session/persistence/graph.py`
- [ ] **Lines:** 36-37
- [ ] **Current Code:** `tasks: {}` and `qa: {}` "Kept for legacy compatibility"
- [ ] **Required Change:** DELETE from `_new_session_data()`
- [ ] **Dependencies:** P1-BC-001
- [ ] **Verification:** `_new_session_data()` returns clean dict

### P1-BC-003: Delete update_record_status()
- [ ] **File:** `src/edison/core/session/persistence/graph.py`
- [ ] **Line:** 119
- [ ] **Current Code:** `update_record_status()` "kept for backward compatibility"
- [ ] **Required Change:** DELETE function entirely
- [ ] **Dependencies:** P1-BC-002
- [ ] **Verification:** No callers remain

### P1-BC-004: Remove workflow.py module functions
- [ ] **File:** `src/edison/core/config/domains/workflow.py`
- [ ] **Lines:** 425-500
- [ ] **Current Code:** Module-level convenience functions for backward compatibility
- [ ] **Required Change:** DELETE functions, update all callers to use `WorkflowConfig()`
- [ ] **Dependencies:** None
- [ ] **Verification:** All callers use class-based API

### P1-BC-005: Remove context7.py module functions
- [ ] **File:** `src/edison/core/config/domains/context7.py`
- [ ] **Lines:** 104+
- [ ] **Current Code:** Module-level convenience functions
- [ ] **Required Change:** DELETE, update callers to use `Context7Config()`
- [ ] **Dependencies:** None
- [ ] **Verification:** Direct class-based imports work

### P1-BC-006: Remove text/__init__.py aliases
- [ ] **File:** `src/edison/core/utils/text/__init__.py`
- [ ] **Lines:** 26-43
- [ ] **Current Code:** Lazy `ENGINE_VERSION`, `extract_anchor_content` alias
- [ ] **Required Change:** DELETE aliases, update callers
- [ ] **Dependencies:** None
- [ ] **Verification:** Direct imports work

### P1-BC-007: Remove includes.py constants
- [ ] **File:** `src/edison/core/composition/includes.py`
- [ ] **Line:** 31
- [ ] **Current Code:** Engine constants for backward compatibility
- [ ] **Required Change:** DELETE, use config directly
- [ ] **Dependencies:** None
- [ ] **Verification:** Config used directly

### P1-BC-008: Remove rules/__init__.py re-exports
- [ ] **File:** `src/edison/core/rules/__init__.py`
- [ ] **Lines:** 31-36
- [ ] **Current Code:** Re-exports for backwards compatibility
- [ ] **Required Change:** DELETE re-exports, update callers
- [ ] **Dependencies:** None
- [ ] **Verification:** Direct imports work

### P1-BC-009: Remove legacy finder.py methods
- [ ] **File:** `src/edison/core/task/repository.py`
- [ ] **Lines:** 243, 269
- [ ] **Current Code:** Methods for "legacy finder.py" compatibility
- [ ] **Required Change:** DELETE methods if finder.py removed
- [ ] **Dependencies:** None
- [ ] **Verification:** No callers remain

### P1-BC-010: Remove --base alias
- [ ] **File:** `src/edison/cli/task/allocate_id.py`
- [ ] **Line:** 23
- [ ] **Current Code:** `--base` alias for backwards compatibility
- [ ] **Required Change:** DELETE alias
- [ ] **Dependencies:** None
- [ ] **Verification:** Tests updated

### P1-BC-011: Remove ConfigManager._apply_project_env_aliases
- [ ] **File:** `src/edison/core/config/manager.py`
- [ ] **Lines:** 215-230, 286
- [ ] **Current Code:** `_apply_project_env_aliases()` maps legacy PROJECT_NAME to project.name
- [ ] **Required Change:** DELETE method and its call in `get()` - enforce NO LEGACY
- [ ] **Dependencies:** None
- [ ] **Verification:** Direct env var access only, no legacy aliasing

### P1-BC-012: Move LEGACY_ROOT_MARKERS to config
- [ ] **File:** `src/edison/core/legacy_guard.py`
- [ ] **Line:** 16
- [ ] **Current Code:** `LEGACY_ROOT_MARKERS = ("project-pre-edison",)` hardcoded
- [ ] **Required Change:** Move markers to `workflow.yaml` or remove if legacy support is dropped
- [ ] **Dependencies:** None
- [ ] **Verification:** No hardcoded legacy markers in code

### P1-BC-013: Remove backward compat re-exports in adapters/settings.py
- [ ] **File:** `src/edison/core/adapters/components/settings.py`
- [ ] **Line:** 182
- [ ] **Current Code:** `# Re-export ALLOWED_TYPES from hooks for backward compatibility`
- [ ] **Required Change:** DELETE re-export, update callers to import directly
- [ ] **Dependencies:** None
- [ ] **Verification:** Direct imports work

### P1-BC-014: Remove backward compat in setup/questionnaire
- [ ] **Files:**
  - `src/edison/core/setup/questionnaire/__init__.py` (lines 9-13)
  - `src/edison/core/setup/questionnaire/rendering.py` (line 120)
- [ ] **Current Code:** Re-exports for backward compatibility
- [ ] **Required Change:** DELETE re-exports, update callers
- [ ] **Dependencies:** None
- [ ] **Verification:** Direct imports work

### P1-BC-015: Remove backward compat alias in rules/checkers.py
- [ ] **File:** `src/edison/core/rules/checkers.py`
- [ ] **Line:** 251
- [ ] **Current Code:** `# Alias for backward compatibility - validator-approval uses the existing function`
- [ ] **Required Change:** DELETE alias, update validator-approval to use direct import
- [ ] **Dependencies:** None
- [ ] **Verification:** Direct imports work

## 2.2 Hardcoded Value Elimination

### P1-HV-001: Add get_all_states() to WorkflowConfig
- [ ] **File:** `src/edison/core/config/domains/workflow.py`
- [ ] **Operation:** ADD METHOD
- [ ] **Required Change:** Add `get_all_states(entity_type: str) -> List[str]` method
- [ ] **Dependencies:** None
- [ ] **Verification:** Unit test the new method

### P1-HV-002: Fix utils.py hardcoded states (line 53)
- [ ] **File:** `src/edison/core/session/next/utils.py`
- [ ] **Line:** 53
- [ ] **Current Code:** `for st in ["todo", "wip", "blocked", "done", "validated"]:`
- [ ] **Required Change:** Use `WorkflowConfig().get_all_states("task")`
- [ ] **Dependencies:** P1-HV-001
- [ ] **Verification:** All states come from config

### P1-HV-003: Fix utils.py hardcoded states (line 94)
- [ ] **File:** `src/edison/core/session/next/utils.py`
- [ ] **Line:** 94
- [ ] **Current Code:** `states = ["todo","wip","blocked","done","validated"]`
- [ ] **Required Change:** Use `WorkflowConfig().get_all_states("task")`
- [ ] **Dependencies:** P1-HV-001
- [ ] **Verification:** All states come from config

### P1-HV-004: Fix context7.py hardcoded states
- [ ] **File:** `src/edison/core/qa/context/context7.py`
- [ ] **Line:** 148
- [ ] **Current Code:** `for state in ("todo", "wip", "blocked", "done", "validated"):`
- [ ] **Required Change:** Use `WorkflowConfig().get_all_states("task")`
- [ ] **Dependencies:** P1-HV-001
- [ ] **Verification:** All states come from config

### P1-HV-005: Create RulesConfig for default rule IDs
- [ ] **File:** `src/edison/core/config/domains/rules.py` (NEW)
- [ ] **Operation:** CREATE
- [ ] **Required Change:** Domain config class that provides default rule IDs from configuration
- [ ] **Dependencies:** None
- [ ] **Verification:** Unit test the new class

### P1-HV-006: Fix recovery.py hardcoded 'Recovery' state
- [ ] **File:** `src/edison/core/session/lifecycle/recovery.py`
- [ ] **Line:** 308
- [ ] **Current Code:** `meta['state'] = 'Recovery'`
- [ ] **Required Change:** Use `WorkflowConfig().get_semantic_state("session", "recovery")` or define "recovery" as semantic state in workflow.yaml
- [ ] **Dependencies:** None
- [ ] **Verification:** No hardcoded 'Recovery' string in recovery.py

### P1-HV-007: Fix task/paths.py hardcoded "wip" fallback
- [ ] **File:** `src/edison/core/task/paths.py`
- [ ] **Lines:** 258, 281
- [ ] **Current Code:** `session_base = _session_state_dir("wip") / session_id` (in `_session_task_dir` and `_session_qa_dir`)
- [ ] **Required Change:** Use `SessionConfig().get_initial_session_state()` or `WorkflowConfig().get_initial_state("session")` instead of hardcoded "wip"
- [ ] **Dependencies:** None
- [ ] **Verification:** No hardcoded "wip" fallback in path resolution functions

### P1-HV-008: Fix workflow.py hardcoded fallback states
- [ ] **File:** `src/edison/core/config/domains/workflow.py`
- [ ] **Lines:** 164, 166, 168, 179, 181, 183, 185, 187
- [ ] **Current Code:**
  ```python
  return _parse_target(on_approve.get("taskState", "")) or "validated"
  return _parse_source(on_approve.get("taskState", "")) or "done"
  return _parse_target(on_reject.get("taskState", "")) or "wip"
  # ... and similar patterns returning "waiting", "todo"
  ```
- [ ] **Required Change:** These methods should raise `ConfigurationError` if config is missing, not return hardcoded defaults. The workflow.yaml MUST define all semantic states.
- [ ] **Dependencies:** Ensure workflow.yaml has all required semantic states defined
- [ ] **Verification:** `grep -n 'or "validated"\|or "done"\|or "wip"\|or "waiting"\|or "todo"' src/edison/core/config/domains/workflow.py` returns 0 results

### P1-HV-009: Remove "or {}" fallback patterns in domain configs
- [ ] **Files:**
  - `src/edison/core/config/domains/task.py`
  - `src/edison/core/config/domains/session.py`
  - `src/edison/core/config/domains/cli.py`
  - `src/edison/core/config/domains/orchestrator.py`
  - `src/edison/core/config/domains/composition.py`
  - `src/edison/core/config/domains/qa.py`
- [ ] **Current Code:** Uses patterns like `.get("key", {}) or {}` which silently return empty dicts when config is missing
- [ ] **Required Change:** Config accessors should fail explicitly with `ConfigurationError` when required sections are missing. YAML is the ONLY source of truth.
- [ ] **Dependencies:** Ensure all required config sections exist in YAML files
- [ ] **Verification:** `grep -rn "or {}" src/edison/core/config/domains` returns 0 results

---

# PHASE 3: MEDIUM PRIORITY (P2) - DRY Consolidation & Unified Patterns

## 3.1 DRY Violations - Duplicate Code Extraction

### P2-DRY-001: Extract shared _get_task_id() utility
- [ ] **File:** `src/edison/data/utils/context.py` (NEW)
- [ ] **Operation:** CREATE
- [ ] **Required Change:** Create shared utility with `get_task_id_from_context()` function
- [ ] **Dependencies:** None
- [ ] **Verification:** Unit test the new function

### P2-DRY-002: Update guards/qa.py to use shared utility
- [ ] **File:** `src/edison/data/guards/qa.py`
- [ ] **Lines:** 258-282
- [ ] **Current Code:** Duplicate `_get_task_id()` function (24 lines)
- [ ] **Required Change:** Replace with import from `data/utils/context.py`
- [ ] **Dependencies:** P2-DRY-001
- [ ] **Verification:** Guards work correctly

### P2-DRY-003: Update conditions/qa.py to use shared utility
- [ ] **File:** `src/edison/data/conditions/qa.py`
- [ ] **Lines:** 137-161
- [ ] **Current Code:** Duplicate `_get_task_id()` function (24 lines)
- [ ] **Required Change:** Replace with import from `data/utils/context.py`
- [ ] **Dependencies:** P2-DRY-001
- [ ] **Verification:** Conditions work correctly

### P2-DRY-004: Replace _load_yaml_file() in file_patterns.py
- [ ] **File:** `src/edison/core/composition/registries/file_patterns.py`
- [ ] **Lines:** ~56
- [ ] **Current Code:** Local `_load_yaml_file()` function
- [ ] **Required Change:** Use `from edison.core.utils.io import read_yaml`
- [ ] **Dependencies:** None
- [ ] **Verification:** File patterns load correctly

### P2-DRY-005: Replace _load_yaml_file() in rules/registry.py
- [ ] **File:** `src/edison/core/rules/registry.py`
- [ ] **Lines:** ~69
- [ ] **Current Code:** Local `_load_yaml_file()` function
- [ ] **Required Change:** Use `from edison.core.utils.io import read_yaml`
- [ ] **Dependencies:** None
- [ ] **Verification:** Rules registry loads correctly

### P2-DRY-006: Extract _normalize_servers() utility
- [ ] **File:** `src/edison/cli/mcp/_utils.py` (NEW)
- [ ] **Operation:** CREATE
- [ ] **Required Change:** Extract shared `normalize_servers()` function
- [ ] **Dependencies:** None
- [ ] **Verification:** Unit test the new function

### P2-DRY-007: Update mcp/configure.py to use shared utility
- [ ] **File:** `src/edison/cli/mcp/configure.py`
- [ ] **Lines:** ~43
- [ ] **Current Code:** Local `_normalize_servers()` function
- [ ] **Required Change:** Import from `cli/mcp/_utils.py`
- [ ] **Dependencies:** P2-DRY-006
- [ ] **Verification:** MCP configure works correctly

### P2-DRY-008: Update mcp/setup.py to use shared utility
- [ ] **File:** `src/edison/cli/mcp/setup.py`
- [ ] **Lines:** ~49
- [ ] **Current Code:** Local `_normalize_servers()` function
- [ ] **Required Change:** Import from `cli/mcp/_utils.py`
- [ ] **Dependencies:** P2-DRY-006
- [ ] **Verification:** MCP setup works correctly

### P2-DRY-009: Consolidate get_config() in composition
- [ ] **Files:**
  - `src/edison/core/composition/context.py` (line 41)
  - `src/edison/core/composition/transformers/base.py` (line 58)
- [ ] **Current Code:** Duplicate `get_config()` methods
- [ ] **Required Change:** Extract to mixin or base class
- [ ] **Dependencies:** None
- [ ] **Verification:** Composition context works correctly

### P2-DRY-010: Replace _load_yaml_file() in mcp/config.py
- [ ] **File:** `src/edison/core/mcp/config.py`
- [ ] **Current Code:** Local `_load_yaml_file()` function
- [ ] **Required Change:** Use `from edison.core.utils.io import read_yaml`
- [ ] **Dependencies:** None
- [ ] **Verification:** MCP config loads correctly

### P2-DRY-011: Delete or consolidate qa/_utils.py get_qa_root_path
- [ ] **File:** `src/edison/core/qa/_utils.py`
- [ ] **Lines:** 12-28
- [ ] **Current Code:** `get_qa_root_path()` duplicates logic in `task/paths.py:get_qa_root()`
- [ ] **Required Change:** 
  - Option A: DELETE `qa/_utils.py` entirely, use `task/paths.get_qa_root()`
  - Option B: Have `qa/_utils.get_qa_root_path()` delegate to `task/paths.get_qa_root()`
- [ ] **Dependencies:** None
- [ ] **Verification:** All QA path resolution uses single source of truth

### P2-DRY-012: Fix fragile detect_record_type in cli/_utils.py
- [ ] **File:** `src/edison/cli/_utils.py`
- [ ] **Current Code:** `detect_record_type` uses fragile string matching (`if "-qa" in record_id`)
- [ ] **Required Change:** Use explicit type argument in CLI or regex pattern matching
- [ ] **Dependencies:** None
- [ ] **Verification:** Record type detection is robust

## 3.2 QA Layer Fixes

### P2-QA-001: Refactor qa/round.py to use QAManager
- [ ] **File:** `src/edison/cli/qa/round.py`
- [ ] **Current Code:** Manually appends text to MD files for "append round"
- [ ] **Required Change:** Move logic into `QAManager` or `EvidenceService`. CLI should not touch disk directly.
- [ ] **Dependencies:** None
- [ ] **Verification:** QA round management works via QAManager

### P2-QA-002: Fix next/actions.py to use TaskRepository
- [ ] **File:** `src/edison/core/session/next/actions.py`
- [ ] **Current Code:** `infer_task_status` reads files directly
- [ ] **Required Change:** Use `TaskRepository` or `TaskIndex` for reliable state
- [ ] **Dependencies:** None
- [ ] **Verification:** Task status inference uses repository pattern

### P2-QA-003: Fix QA repository _get_states_to_search to use QAConfig
- [ ] **File:** `src/edison/core/qa/workflow/repository.py`
- [ ] **Current Code:** `_get_states_to_search` may have hardcoded states
- [ ] **Required Change:** Use `QAConfig` or `WorkflowConfig` for state list
- [ ] **Dependencies:** None
- [ ] **Verification:** QA repository state search is config-driven

### P2-QA-004: Fix validator roster to use SessionContext
- [ ] **File:** `src/edison/core/qa/validator/roster.py`
- [ ] **Current Code:** `_detect_validators_from_git_diff` may not use SessionContext for worktree
- [ ] **Required Change:** Use `SessionContext` to find worktree reliably
- [ ] **Dependencies:** None
- [ ] **Verification:** Validator roster uses SessionContext

### P2-QA-005: Update cli/qa/bundle.py to use QAManager
- [ ] **File:** `src/edison/cli/qa/bundle.py`
- [ ] **Current Code:** May use EvidenceService directly
- [ ] **Required Change:** Use `EvidenceService` via `QAManager` for consistent API
- [ ] **Dependencies:** None
- [ ] **Verification:** Bundle management goes through QAManager

### P2-QA-006: Refactor cli/qa/new.py to use QAManager
- [ ] **File:** `src/edison/cli/qa/new.py`
- [ ] **Current Code:** Manual EvidenceService calls for QA brief creation
- [ ] **Required Change:** Use `QAManager.initialize_round()` for consistent initialization
- [ ] **Dependencies:** None
- [ ] **Verification:** QA creation uses QAManager

### P2-QA-007: Ensure CLI uses QAManager exclusively
- [ ] **File:** `src/edison/core/qa/manager.py`
- [ ] **Current Code:** QAManager wraps EvidenceService but CLI may bypass it
- [ ] **Required Change:** Audit all CLI QA commands to ensure they use QAManager exclusively
- [ ] **Dependencies:** P2-QA-005, P2-QA-006
- [ ] **Verification:** All CLI QA commands use QAManager, not direct EvidenceService

## 3.3 Verify/Recovery File Abstraction

### P2-VF-001: Abstract verify.py file access
- [ ] **File:** `src/edison/core/session/lifecycle/verify.py`
- [ ] **Current Code:** `verify_session_health` manually reads JSON files for task/QA data
- [ ] **Required Change:** Use `TaskIndex` and `EvidenceService` to abstract file access instead of direct JSON reads
- [ ] **Dependencies:** P0-GB-001
- [ ] **Verification:** No direct JSON file reads in `verify_session_health()` - all data access through repository/service layer

### P2-REC-001: Abstract recovery.py JSON manipulation
- [ ] **File:** `src/edison/core/session/lifecycle/recovery.py`
- [ ] **Current Code:** Manual JSON manipulation for session data (direct file reads/writes)
- [ ] **Required Change:** Use `SessionRepository` instead of direct JSON manipulation
- [ ] **Dependencies:** P0-GB-002
- [ ] **Verification:** No direct JSON manipulation in `recovery.py` - all session data access through `SessionRepository`

### P2-REC-002: Clean up technical debt comments in recovery.py
- [ ] **File:** `src/edison/core/session/lifecycle/recovery.py`
- [ ] **Current Code:** Contains technical debt comments like `# We can instantiate a ValidationTransaction and call abort? Or just manually clean up.`
- [ ] **Required Change:** Either implement the proper logic or remove commented dead code blocks
- [ ] **Dependencies:** P2-REC-001
- [ ] **Verification:** No TODO/FIXME/technical debt comments remain in recovery.py

### P2-REC-003: Implement or remove TODO staleness check in recovery.py
- [ ] **File:** `src/edison/core/session/lifecycle/recovery.py`
- [ ] **Line:** 544
- [ ] **Current Code:** `# TODO: Implement staleness check based on lock age`
- [ ] **Required Change:** Either implement the staleness check based on lock age, or remove the TODO if not needed
- [ ] **Dependencies:** P2-REC-001
- [ ] **Verification:** No TODO comments remain in recovery.py

## 3.4 Unified Transition Pattern

### P2-TP-001: Enable action execution in state transitions
- [ ] **Files:**
  - `src/edison/core/state/validator.py` (ROOT CAUSE - line 51)
  - `src/edison/core/state/transitions.py`
- [ ] **Operation:** MODIFY
- [ ] **ROOT CAUSE ANALYSIS:**
  1. `StateValidator.ensure_transition()` at line 51 passes `execute_actions=False`:
     ```python
     machine.validate(str(from_state), str(to_state), context=ctx, execute_actions=False)
     ```
  2. `validate_transition()` in transitions.py delegates to `ensure_transition()`
  3. ALL CLI commands use `validate_transition()` for validation, then manually set state
  4. This means workflow.yaml actions are NEVER executed in any CLI command
  5. `transition_entity()` correctly passes `execute_actions=True` but is NEVER called by CLI
- [ ] **Required Change:**
  - Option A (Recommended): Update all CLI commands to use `transition_entity()` instead of `validate_transition()` + manual state change
  - Option B: Create `execute_validated_transition()` that performs state change AND action execution
  - Option C: Change `ensure_transition()` to pass `execute_actions=True` by default (BREAKING CHANGE)
- [ ] **Critical Fix Required:** Currently workflow.yaml actions like `record_completion_time`, `notify_session_start`, `finalize_session` are NEVER executed
- [ ] **Dependencies:** None
- [ ] **Verification:**
  - Unit test that `record_completion_time` action executes when transitioning wip→done
  - Unit test that `record_blocker_reason` action executes when transitioning to blocked
  - Unit test that `notify_session_start` action executes when transitioning pending→wip

### P2-TP-002: Update cli/task/status.py to use transition_entity()
- [ ] **File:** `src/edison/cli/task/status.py`
- [ ] **Lines:** 126-129
- [ ] **Current Code:**
  ```python
  entity.state = args.status
  entity.record_transition(old_state, args.status, reason="cli-status-command")
  repo.save(entity)
  ```
- [ ] **Required Change:** Use `transition_entity()` which handles guards and actions
- [ ] **Dependencies:** P2-TP-001
- [ ] **Verification:** Actions execute on task status change

### P2-TP-003: Update cli/qa/promote.py to use transition_entity()
- [ ] **File:** `src/edison/cli/qa/promote.py`
- [ ] **Lines:** 170-173
- [ ] **Current Code:**
  ```python
  old_state = qa_entity.state
  qa_entity.state = args.status
  qa_entity.record_transition(old_state, args.status, reason="cli-qa-promote")
  qa_repo.save(qa_entity)
  ```
- [ ] **Required Change:** Use `transition_entity()` which handles guards and actions
- [ ] **Dependencies:** P2-TP-001
- [ ] **Verification:** Actions execute on QA promotion

### P2-TP-004: Fix compute.py hardcoded rule IDs (21 instances)
- [ ] **File:** `src/edison/core/session/next/compute.py`
- [ ] **Lines:** 190, 230-231, 246, 267-268, 280, 297, 368, 409-454
- [ ] **Current Code:** Hardcoded `"RULE.VALIDATION.FIRST"`, `"RULE.GUARDS.FAIL_CLOSED"`, etc.
- [ ] **Required Change:** Use `RulesConfig().get_default_rule(context)` or similar
- [ ] **Dependencies:** P1-HV-005
- [ ] **Verification:** Rule IDs come from configuration

### P2-TP-005: Update CLI task/link.py to use entity pattern
- [ ] **File:** `src/edison/cli/task/link.py`
- [ ] **Current Code:** Manually updates `tasks` dict in session JSON (Legacy!)
- [ ] **Required Change:** Update `parent_id`/`child_ids` on Task entities via `TaskRepository`
- [ ] **Dependencies:** None
- [ ] **Verification:** No session JSON manipulation

### P2-TP-006: Move allocate_id logic to TaskRepository
- [ ] **File:** `src/edison/cli/task/allocate_id.py`
- [ ] **Current Code:** Contains file scanning logic
- [ ] **Required Change:** Move scanning logic to `TaskRepository.get_next_child_id(parent_id)`
- [ ] **Dependencies:** None
- [ ] **Verification:** ID allocation via repository

### P2-TP-007: Update core/task/workflow.py to use transition_entity()
- [ ] **File:** `src/edison/core/task/workflow.py`
- [ ] **Current Code:** Uses `validate_transition()` + direct `task.state = ...` assignment
- [ ] **Required Change:** Use `transition_entity()` which handles guards, actions, and state change atomically
- [ ] **Dependencies:** P2-TP-001
- [ ] **Verification:** Task workflow uses unified transition pattern

### P2-TP-008: Update core/session/lifecycle/manager.py to use transition_entity()
- [ ] **File:** `src/edison/core/session/lifecycle/manager.py`
- [ ] **Lines:** 124-143 (`transition_session` function)
- [ ] **Current Code:** 
  ```python
  validator.ensure_transition("session", current, target)  # execute_actions=False!
  entity.record_transition(current, target)
  entity.state = target
  repo.save(entity)
  ```
- [ ] **Problem:** Actions from workflow.yaml for session transitions (e.g., `notify_session_start`, `finalize_session`) are NEVER executed
- [ ] **Required Change:** Use `transition_entity()` which handles guards, actions, and state change atomically
- [ ] **Dependencies:** P2-TP-001
- [ ] **Verification:** 
  - Session transition actions from workflow.yaml are executed
  - `notify_session_start` runs on pending→wip transition
  - `finalize_session` runs on closing→closed transition

### P2-TP-009: Add TaskQAWorkflow.transition_task() facade method
- [ ] **File:** `src/edison/core/task/workflow.py`
- [ ] **Operation:** ADD METHOD
- [ ] **Required Change:** Add `transition_task(task_id: str, to_state: str, session_id: str, reason: str = None)` method that:
  1. Loads task via TaskRepository
  2. Calls `transition_entity()` with proper context
  3. Returns the updated task
- [ ] **Rationale:** Maintains TaskQAWorkflow as the facade for all task operations, ensuring CLI doesn't need to know about transition_entity() internals
- [ ] **Dependencies:** P2-TP-001
- [ ] **Verification:** CLI `task status` can use `TaskQAWorkflow.transition_task()` for encapsulated transitions

---

# PHASE 4: LOW PRIORITY (P3) - Large File Refactoring

### P3-LF-001: Split compute.py
- [ ] **File:** `src/edison/core/session/next/compute.py` (585 lines)
- [ ] **Operation:** SPLIT into:
  - `compute.py` - Main compute_next function
  - `builders.py` - Action builders
  - `formatters.py` - Output formatters
- [ ] **Dependencies:** P2-TP-004
- [ ] **Verification:** Each file <300 lines

### P3-LF-002: Split workflow.py config
- [ ] **File:** `src/edison/core/config/domains/workflow.py` (666 lines)
- [ ] **Operation:** SPLIT into:
  - `workflow.py` - Workflow configuration
  - `statemachine.py` - State machine configuration
- [ ] **Dependencies:** P1-BC-004
- [ ] **Verification:** Each file <400 lines

### P3-LF-003: Split _base.py registries
- [ ] **File:** `src/edison/core/composition/registries/_base.py` (631 lines)
- [ ] **Operation:** SPLIT into:
  - `base.py` - Base registry class
  - `discovery_mixin.py` - Discovery mixin
- [ ] **Dependencies:** P2-DRY-*
- [ ] **Verification:** Each file <400 lines

### P3-LF-004: Refactor rules/engine.py
- [ ] **File:** `src/edison/core/rules/engine.py` (602 lines)
- [ ] **Operation:** Extract helper classes
- [ ] **Dependencies:** None
- [ ] **Verification:** File <400 lines

### P3-LF-005: Refactor rules/registry.py
- [ ] **File:** `src/edison/core/rules/registry.py` (586 lines)
- [ ] **Operation:** Extract helper utilities
- [ ] **Dependencies:** P2-DRY-005
- [ ] **Verification:** File <400 lines

### P3-LF-006: Refactor recovery.py
- [ ] **File:** `src/edison/core/session/lifecycle/recovery.py` (550 lines)
- [ ] **Operation:** Extract recovery strategies to separate module
- [ ] **Dependencies:** P0-GB-002
- [ ] **Verification:** File <400 lines

### P3-LF-007: Consolidate path modules
- [ ] **Files:**
  - `src/edison/core/session/paths.py`
  - `src/edison/core/task/paths.py`
  - `src/edison/core/utils/paths/`
- [ ] **Operation:** Deprecate domain-specific ones if they just wrap utility ones
- [ ] **Dependencies:** None
- [ ] **Verification:** Single source of truth for paths

---

# PHASE 5: ENHANCEMENTS (P4) - Inheritance Improvements

### P4-INH-001: Make Task inherit from BaseEntity
- [ ] **File:** `src/edison/core/task/models.py`
- [ ] **Current Code:** Task has its own `record_transition()` implementation
- [ ] **Required Change:** `class Task(BaseEntity)` - inherit common methods
- [ ] **Dependencies:** P2-DRY-*
- [ ] **Verification:** `record_transition()` inherited from BaseEntity

### P4-INH-002: Make QARecord inherit from BaseEntity
- [ ] **File:** `src/edison/core/qa/models.py`
- [ ] **Current Code:** QARecord has its own `record_transition()` implementation
- [ ] **Required Change:** `class QARecord(BaseEntity)` - inherit common methods
- [ ] **Dependencies:** P2-DRY-*
- [ ] **Verification:** `record_transition()` inherited from BaseEntity

### P4-INH-003: Update Session to use BaseEntity pattern
- [ ] **File:** `src/edison/core/session/core/models.py`
- [ ] **Lines:** ~151 (record_transition), 144-146 (deprecated fields)
- [ ] **Current Code:** Session has deprecated fields AND its own `record_transition()` implementation (duplicated from BaseEntity)
- [ ] **Required Change:** 
  1. Clean up Session model to match BaseEntity pattern
  2. Either inherit from BaseEntity OR delegate `record_transition()` to BaseEntity's implementation
  3. Remove duplicate `record_transition()` method
- [ ] **Dependencies:** P1-BC-001
- [ ] **Verification:** 
  - Session model is clean and consistent
  - Session uses unified `record_transition()` pattern (no duplication with `entity/base.py:164`)

## 5.2 Verification & Performance

### P4-VER-001: Verify rules/engine.py get_rules_for_context coverage
- [ ] **File:** `src/edison/core/rules/engine.py`
- [ ] **Current Code:** `get_rules_for_context` may not cover all context types from workflow.yaml
- [ ] **Required Change:** Verify and update to cover all new context types
- [ ] **Dependencies:** None
- [ ] **Verification:** All context types from workflow.yaml are handled

### P4-VER-002: Verify TaskIndex speed and caching
- [ ] **File:** `src/edison/core/task/index.py`
- [ ] **Current Code:** TaskIndex performance not verified
- [ ] **Required Change:** Verify speed and add caching if necessary
- [ ] **Dependencies:** None
- [ ] **Verification:** TaskIndex operations complete in <100ms for typical session

### P4-VER-003: Verify qa/audit.py uses CompositionConfig
- [ ] **File:** `src/edison/cli/qa/audit.py`
- [ ] **Current Code:** May have hardcoded composition values
- [ ] **Required Change:** Verify it uses `CompositionConfig` for all composition-related configuration
- [ ] **Dependencies:** None
- [ ] **Verification:** No hardcoded composition values in qa/audit.py

### P4-VER-004: Verify build_validator_roster uses QAConfig
- [ ] **Files:** 
  - `src/edison/cli/qa/validate.py`
  - `src/edison/core/qa/validator/roster.py`
- [ ] **Current Code:** `build_validator_roster()` may have hardcoded validator configuration
- [ ] **Required Change:** Verify `build_validator_roster()` uses `QAConfig` for all validator configuration
- [ ] **Dependencies:** None
- [ ] **Verification:** No hardcoded validator configuration in roster.py

### P4-VER-005: Verify promoter.py uses validate_transition
- [ ] **File:** `src/edison/core/qa/promoter.py`
- [ ] **Current Code:** May check promotion eligibility without using unified validation
- [ ] **Required Change:** Verify it uses `validate_transition()` for checking if promotion is allowed
- [ ] **Dependencies:** P2-TP-001
- [ ] **Verification:** All promotion eligibility checks go through unified `validate_transition()`

### P4-VER-006: Verify no Python fallback defaults for config
- [ ] **Files:** All `core/config/domains/*.py`
- [ ] **Current Code:** Some domain configs have Python fallback defaults when YAML is missing
- [ ] **Required Change:** YAML should be the ONLY source of truth - code should fail if config missing, not fallback
- [ ] **Dependencies:** None
- [ ] **Verification:** grep for fallback patterns like `or {}`, `.get("key", "default")`

---

# PHASE 6: VERIFICATION

## 6.1 Import Verification
- [ ] `python -c "from edison.core import *"` - No import errors
- [ ] `python -c "from edison.cli import *"` - No import errors
- [ ] `python -c "from edison.data import *"` - No import errors

## 6.2 Legacy Code Elimination
- [ ] `grep -r "backward.compat\|backwards.compat\|DEPRECATED" src/edison` returns 0 results
- [ ] `grep -r "\"todo\"\|\"wip\"\|\"done\"\|\"validated\"\|\"blocked\"" src/edison --include="*.py"` - Only in tests/configs
- [ ] `grep -r "_apply_project_env_aliases" src/edison` returns 0 results
- [ ] No technical debt comments (TODO/FIXME/HACK) in recovery.py
- [ ] No hardcoded `'Recovery'` state in recovery.py (HV-006)
- [ ] No hardcoded `"wip"` fallback in task/paths.py (HV-007)

## 6.3 DRY Verification
- [ ] No duplicate `_get_task_id()` functions exist
- [ ] No duplicate `_load_yaml_file()` functions exist
- [ ] No duplicate `_normalize_servers()` functions exist
- [ ] No duplicate `record_transition()` implementations (Task, QARecord, Session all use BaseEntity)
- [ ] No duplicate `get_qa_root` implementations (qa/_utils.py vs task/paths.py)
- [ ] `detect_record_type` uses robust pattern matching (not fragile string contains)

## 6.4 Guard System Verification
- [ ] All state transitions go through `validate_transition()` or `transition_entity()`
- [ ] All guards referenced in workflow.yaml are called during transitions
- [ ] All conditions referenced in workflow.yaml are evaluated during transitions
- [ ] All actions referenced in workflow.yaml are executed during transitions

## 6.5 File Abstraction Verification
- [ ] `verify_session_health()` uses TaskIndex/EvidenceService (no direct JSON reads)
- [ ] `recovery.py` uses SessionRepository (no direct JSON manipulation)
- [ ] All data access goes through Repository/Service layer

## 6.6 Config Usage Verification
- [ ] `qa/audit.py` uses CompositionConfig (VER-003)
- [ ] `build_validator_roster()` uses QAConfig (VER-004)
- [ ] `promoter.py` uses validate_transition() (VER-005)
- [ ] `rules/engine.py` get_rules_for_context covers all context types (VER-001)
- [ ] TaskIndex operations complete in <100ms (VER-002)

## 6.7 Test Suite
- [ ] `pytest tests/` - All tests pass
- [ ] No file exceeds 500 lines (except data files)
- [ ] All entity models inherit from BaseEntity

## 6.8 CLI Command Verification
- [ ] `edison session next` returns correct recommendations
- [ ] `edison task status` correctly validates transitions
- [ ] `edison qa promote` correctly validates transitions
- [ ] `edison session verify` checks guards before state change
- [ ] `edison task claim` validates guards for both task and QA paths

---

# APPENDIX A: Files to Create

| File | Purpose | Phase |
|------|---------|-------|
| `src/edison/data/utils/__init__.py` | Utils package init | P2 |
| `src/edison/data/utils/context.py` | Shared context utilities | P2 |
| `src/edison/cli/mcp/_utils.py` | Shared MCP CLI utilities | P2 |
| `src/edison/core/config/domains/rules.py` | Rules domain config | P1 |
| `src/edison/core/session/next/builders.py` | Action builders | P3 |
| `src/edison/core/session/next/formatters.py` | Output formatters | P3 |
| `src/edison/core/config/domains/statemachine.py` | State machine config | P3 |
| `src/edison/core/composition/registries/discovery_mixin.py` | Discovery mixin | P3 |

---

# APPENDIX B: Files to Modify (Summary)

| Priority | File | Actions |
|----------|------|---------|
| P0 | `core/session/lifecycle/verify.py` | GB-001, VF-001 |
| P0 | `core/session/lifecycle/recovery.py` | GB-002, REC-001, HV-006, LF-006 |
| P0 | `cli/task/claim.py` | GB-003 |
| P0 | `core/qa/workflow/repository.py` | GB-004, QA-003 |
| P0 | `core/composition/core/base.py` | CD-001 |
| P0 | `core/config/manager.py` | CD-001 |
| P0 | `core/utils/paths/resolver.py` | CD-001 |
| P1 | `core/session/core/models.py` | BC-001, INH-003 |
| P1 | `core/session/persistence/graph.py` | BC-002, BC-003 |
| P1 | `core/config/domains/workflow.py` | BC-004, HV-001, LF-002 |
| P1 | `core/config/domains/context7.py` | BC-005 |
| P1 | `core/utils/text/__init__.py` | BC-006 |
| P1 | `core/composition/includes.py` | BC-007 |
| P1 | `core/rules/__init__.py` | BC-008 |
| P1 | `core/task/repository.py` | BC-009 |
| P1 | `cli/task/allocate_id.py` | BC-010, TP-006 |
| P1 | `core/config/manager.py` | BC-011, CD-001 |
| P1 | `core/legacy_guard.py` | BC-012 |
| P1 | `core/adapters/components/settings.py` | BC-013 |
| P1 | `core/setup/questionnaire/__init__.py` | BC-014 |
| P1 | `core/setup/questionnaire/rendering.py` | BC-014 |
| P1 | `core/rules/checkers.py` | BC-015 |
| P1 | `core/session/next/utils.py` | HV-002, HV-003 |
| P1 | `core/qa/context/context7.py` | HV-004 |
| P1 | `core/task/paths.py` | HV-007 |
| P2 | `data/guards/qa.py` | DRY-002 |
| P2 | `data/conditions/qa.py` | DRY-003 |
| P2 | `core/composition/registries/file_patterns.py` | DRY-004 |
| P2 | `core/rules/registry.py` | DRY-005, LF-005 |
| P2 | `cli/mcp/configure.py` | DRY-007 |
| P2 | `cli/mcp/setup.py` | DRY-008 |
| P2 | `core/composition/context.py` | DRY-009 |
| P2 | `core/composition/transformers/base.py` | DRY-009 |
| P2 | `core/mcp/config.py` | DRY-010 |
| P2 | `core/qa/_utils.py` | DRY-011 |
| P2 | `cli/_utils.py` | DRY-012 |
| P2 | `cli/qa/round.py` | QA-001 |
| P2 | `core/session/next/actions.py` | QA-002 |
| P2 | `core/qa/validator/roster.py` | QA-004 |
| P2 | `cli/qa/bundle.py` | QA-005 |
| P2 | `cli/qa/new.py` | QA-006 |
| P2 | `core/qa/manager.py` | QA-007 |
| P2 | `core/state/transitions.py` | TP-001 |
| P2 | `cli/task/status.py` | TP-002 |
| P2 | `cli/qa/promote.py` | TP-003 |
| P2 | `core/session/next/compute.py` | TP-004, LF-001 |
| P2 | `cli/task/link.py` | TP-005 |
| P2 | `core/task/workflow.py` | TP-007, TP-009 |
| P2 | `core/session/lifecycle/manager.py` | TP-008 |
| P3 | `core/composition/registries/_base.py` | LF-003 |
| P3 | `core/rules/engine.py` | LF-004, VER-001 |
| P4 | `core/task/models.py` | INH-001 |
| P4 | `core/qa/models.py` | INH-002 |
| P4 | `core/task/index.py` | VER-002 |
| P4 | `cli/qa/audit.py` | VER-003 |
| P4 | `cli/qa/validate.py` | VER-004 |
| P4 | `core/qa/validator/roster.py` | QA-004, VER-004 |
| P4 | `core/qa/promoter.py` | VER-005 |
| P4 | `core/config/domains/*.py` | VER-006 |

---

# APPENDIX C: Orphaned Handlers (Decision Required)

These handlers are implemented but NOT referenced in workflow.yaml:

**Guards (keep for extensibility):**
- `fail_closed` - Core guard for explicit blocking
- `has_implementation_report` - Alias for can_finish_task
- `has_session_blockers` - Session-specific blocker check
- `is_session_ready` - Session readiness check
- `has_all_waves_passed` (as guard) - Also exists as condition
- `has_bundle_approval` (as guard) - Also exists as condition

**Conditions (keep for extensibility):**
- `all_blocking_validators_passed` - Similar to has_all_waves_passed
- `has_blocker_reason` - Opposite of blockers_resolved
- `session_has_owner` - Owner check
- `task_ready_for_qa` - QA readiness check
- `has_validator_reports` - Also exists as guard

**Actions (keep for extensibility):**
- `append_session_log` - Utility for logging
- `log_transition` - Transition logging

**Recommendation:** Keep all for project-level customization, but document their purpose.

---

# APPENDIX D: Implementation Notes

## Dependency Graph

```
Phase 1 (P0):
  GB-001, GB-002, GB-003, GB-004 (parallel)
  CD-001 → CD-002 → CD-003

Phase 2 (P1):
  BC-004, BC-005, BC-006, BC-007, BC-008, BC-009, BC-010 (parallel)
  CD-003 → BC-001 → BC-002 → BC-003
  HV-001 → HV-002, HV-003, HV-004 (HV-001 is dependency)
  HV-005, HV-006, HV-007 (independent)

Phase 3 (P2):
  DRY-001 → DRY-002, DRY-003
  DRY-004, DRY-005, DRY-010 (parallel)
  DRY-006 → DRY-007, DRY-008
  DRY-009 (independent)
  QA-001, QA-002, QA-003, QA-004 (parallel - independent QA fixes)
  QA-005, QA-006 (parallel) → QA-007
  GB-001 → VF-001 (verify.py file abstraction after guard fix)
  GB-002 → REC-001 (recovery.py file abstraction after guard fix)
  TP-001 → TP-002, TP-003, TP-007, TP-008, TP-009
  HV-005 → TP-004
  TP-005, TP-006 (parallel)

Phase 4 (P3):
  TP-004 → LF-001
  BC-004 → LF-002
  DRY-* → LF-003
  LF-004, LF-005, LF-006, LF-007 (parallel)

Phase 5 (P4):
  DRY-* → INH-001, INH-002
  BC-001 → INH-003
  VER-001, VER-002, VER-003, VER-004 (parallel - verification tasks)
  TP-001 → VER-005 (promoter.py verification after transition pattern)
```

---

## Final Verification Commands

After completing all phases, run these verification commands to ensure all issues are resolved:

```bash
# Guard Bypass Verification - should return 0 results
grep -rn 'session\["state"\]\s*=' src/edison --include="*.py"
grep -rn '\.state\s*=' src/edison/cli --include="*.py"

# Hardcoded Values Verification - should return 0 results
grep -rn 'or "validated"\|or "done"\|or "wip"\|or "waiting"\|or "todo"' src/edison/core/config/domains --include="*.py"
grep -rn "or {}" src/edison/core/config/domains --include="*.py"

# Backward Compatibility Verification - should return 0 results
grep -rn "backward\|compat\|legacy\|deprecated\|DEPRECATED" src/edison --include="*.py" | grep -v "test"

# DRY Violations Verification - should return 0 results
grep -rn "def _get_task_id" src/edison/data --include="*.py"
grep -rn "def _load_yaml_file" src/edison/core --include="*.py"
grep -rn "def _normalize_servers" src/edison/cli --include="*.py"

# TODO/FIXME Verification - should return 0 results
grep -rn "TODO\|FIXME\|HACK\|XXX" src/edison --include="*.py"

# Import Cycle Verification - should succeed without errors
python -c "from edison.core.composition import *"
python -c "from edison.core.state import *"
python -c "from edison.core.session import *"

# Full Test Suite
pytest tests/ -v --tb=short
```

---

**END OF COMPREHENSIVE UNIFICATION PLAN**

