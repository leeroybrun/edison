# AUDIT 1: DRY & Duplication - Action Checklist

**Last Updated:** 2025-11-26
**Status:** Ready for Implementation

---

## CRITICAL PRIORITY (22-29 hours)

### 1. Consolidate JSON I/O (8-10 hours)
- [ ] Audit all 36 instances of direct `json.load()`/`json.dump()`
- [ ] Replace with `utils.json_io.read_json()` and `write_json_atomic()`
- [ ] Update `file_io/utils.py` to delegate to `json_io`
- [ ] Test all replacement locations
- [ ] Remove any remaining duplicates

**Files to Update:**
- ide/settings.py
- config.py
- setup/discovery.py
- qa/store.py
- composition/includes.py
- task/io.py
- (30 more files)

---

### 2. Consolidate Repository Root Detection (4-6 hours)
- [ ] Remove `_repo_root()` from composition/includes.py:28
- [ ] Remove `_repo_root()` from composition/audit/discovery.py:43
- [ ] Remove `_repo_root()` from composition/guidelines.py:41
- [ ] Remove `_resolve_repo_root()` from utils/subprocess.py:33
- [ ] Remove `_detect_repo_root()` from adapters/sync/zen.py:35
- [ ] Remove `_detect_repo_root()` from adapters/sync/cursor.py:46
- [ ] Remove `_resolve_repo_root()` from task/paths.py:17
- [ ] Consolidate `_get_worktree_base()` (session/store.py:448 vs session/worktree.py:74)
- [ ] Update all call sites to use `utils.git.get_repo_root()`
- [ ] Test all replacement locations

---

### 3. Consolidate Time/Timestamp Functions (2-3 hours)
- [ ] Remove `utc_timestamp()` from task/io.py:224
- [ ] Remove `_now_iso()` from task/io.py:220
- [ ] Remove `_now_iso()` from qa/scoring.py:11
- [ ] Remove `_now_iso()` from composition/delegation.py:74
- [ ] Update all call sites to use `utils.time.utc_timestamp()`
- [ ] Verify `file_io/utils.py:112` delegation is correct
- [ ] Test timestamp consistency

---

### 4. Centralize mkdir Pattern (6-8 hours)
- [ ] Create `file_io.utils.ensure_dir(path: Path)` function
- [ ] Update all 85 instances of `.mkdir(parents=True, exist_ok=True)`
  - [ ] ide/ modules (5 instances)
  - [ ] file_io/ modules (2 instances)
  - [ ] paths/ modules (1 instance)
  - [ ] qa/ modules (4 instances)
  - [ ] composition/ modules (7 instances)
  - [ ] adapters/ modules (12 instances)
  - [ ] task/ modules (9 instances)
  - [ ] orchestrator/ modules (3 instances)
  - [ ] session/ modules (25 instances)
- [ ] Test all replacement locations

---

### 5. Fix write_text_locked Duplication (2 hours)
- [ ] Keep implementation in task/locking.py:157
- [ ] Remove wrapper from task/io.py:192 or make it clearer it's a delegate
- [ ] Update all call sites
- [ ] Test locking behavior

---

## HIGH PRIORITY (10-13 hours)

### 6. Centralize YAML Loading (3-4 hours)
- [ ] Audit all 18 instances of direct `yaml.safe_load()`
- [ ] Replace with `file_io.utils.read_yaml_safe()`
- [ ] Test all replacement locations

**Files to Update:**
- config.py
- setup/discovery.py, setup/questionnaire.py
- paths/management.py, paths/project.py
- composition/orchestrator.py, composition/workflow.py, composition/packs.py
- task/metadata.py, task/locking.py, task/context7.py
- rules/registry.py
- process/inspector.py
- session/state_machine_docs.py

---

### 7. Remove QA Evidence Wrapper Functions (2-3 hours)
- [ ] Delete `missing_evidence_blockers()` from session/next/actions.py:23
- [ ] Delete `read_validator_jsons()` from session/next/actions.py:28
- [ ] Delete `load_impl_followups()` from session/next/actions.py:33
- [ ] Delete `load_bundle_followups()` from session/next/actions.py:38
- [ ] Update all callers to import from `qa.evidence` directly
- [ ] Test all call sites

---

### 8. Rename ValidationTransaction Classes (3-4 hours)
- [ ] Rename to `QAValidationTransaction` in qa/transaction.py:16
- [ ] Rename to `SessionValidationTransaction` in session/transaction.py:249
- [ ] Update all call sites
- [ ] Test both transaction types

---

### 9. Consolidate _latest_round_dir (2 hours)
- [ ] Keep implementation in qa/evidence.py:538
- [ ] Remove from task/context7.py:202
- [ ] Remove from session/verify.py:16
- [ ] Update all call sites to import from `qa.evidence`
- [ ] Test all use cases

---

## MEDIUM PRIORITY (19-26 hours)

### 10. Rename _cfg Functions (2-3 hours)
- [ ] Rename utils/time.py:21 `_cfg()` to `_time_cfg()`
- [ ] Rename utils/json_io.py:24 `_cfg()` to `_json_cfg()`
- [ ] Rename utils/cli_output.py:40 `_cfg()` to `_cli_output_cfg()`
- [ ] Update all call sites within each module
- [ ] Test config loading

---

### 11. Consolidate qa_root (2 hours)
- [ ] Move to single implementation in paths/management.py
- [ ] Support optional project_root parameter
- [ ] Remove from qa/store.py:16
- [ ] Remove from task/store.py:22
- [ ] Update all call sites
- [ ] Test both use cases

---

### 12. Fix find_record Duplication (2 hours)
- [ ] Analyze task/finder.py:98 vs task/metadata.py:317
- [ ] Consolidate if same functionality
- [ ] Or rename if different: `find_metadata_record()`
- [ ] Update all call sites
- [ ] Test both use cases

---

### 13. Fix load_delegation_config Duplication (2-3 hours)
- [ ] Analyze qa/config.py:66 vs composition/orchestrator.py:232
- [ ] Rename orchestrator version to `load_orchestrator_delegation_config()`
- [ ] Or consolidate if same functionality
- [ ] Update all call sites
- [ ] Test both use cases

---

### 14. Audit State Machine Duplication (3-4 hours)
- [ ] Analyze task/state.py:8 `build_default_state_machine()`
- [ ] Analyze session/state.py:73 `build_default_state_machine()`
- [ ] Determine if should be unified or separate
- [ ] If separate: rename to `build_task_state_machine()` and `build_session_state_machine()`
- [ ] If unified: consolidate into state/engine.py
- [ ] Document decision in CLAUDE.md
- [ ] Update all call sites
- [ ] Test both state machines

---

### 15. Document Module Structure Patterns (8-12 hours)
- [ ] Document canonical locations for common operations
- [ ] Create architecture diagram showing module dependencies
- [ ] Document Manager pattern guidelines
- [ ] Document Config pattern guidelines
- [ ] Add "Where to find..." guide to CLAUDE.md
- [ ] Document session/task/qa module structure pattern

---

## LOW PRIORITY (5-7 hours)

### 16. Audit render_markdown (1 hour)
- [ ] Check if session/manager.py:146 delegates to session/store.py:405
- [ ] If duplicate, remove from manager.py
- [ ] Update call sites
- [ ] Test rendering

---

### 17. Create Path Utility Functions (4-6 hours)
- [ ] Add `ensure_exists(path: Path, error_msg: str) -> Path` to file_io/utils.py
- [ ] Add `read_if_exists(path: Path, default: Any = None) -> str` to file_io/utils.py
- [ ] Add `path_or_default(path: Path, default: Path) -> Path` to file_io/utils.py
- [ ] Selectively refactor high-impact .exists() checks (from 284 total)
- [ ] Test new utilities

---

## PREVENTION MEASURES

### Code Review Checklist Updates
- [ ] Add to PR template: No duplicate function names without justification
- [ ] Add to PR template: All file I/O uses centralized utilities
- [ ] Add to PR template: No direct json.load/dump or yaml.safe_load calls
- [ ] Add to PR template: No duplicate implementations of existing utilities

### Pre-commit Hooks
- [ ] Add check for direct json.load/dump usage
- [ ] Add check for direct yaml.safe_load usage
- [ ] Add check for duplicate function names across modules

### Documentation
- [ ] Update CLAUDE.md with canonical utility locations
- [ ] Add architecture diagram to docs/
- [ ] Create CONTRIBUTING.md with DRY guidelines

---

## PROGRESS TRACKING

**Overall Progress:** 0/17 items completed

**By Priority:**
- Critical: 0/5 items (0%)
- High: 0/4 items (0%)
- Medium: 0/6 items (0%)
- Low: 0/2 items (0%)

**Estimated Time Remaining:** 56-75 hours (7-10 developer days)

---

## NOTES

Add implementation notes, blockers, or decisions here as work progresses.
