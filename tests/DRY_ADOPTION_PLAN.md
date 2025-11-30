# Test Helpers DRY Adoption Plan

## Status: IN PROGRESS
**Created**: 2025-11-30
**Goal**: Ensure all test files use centralized helpers instead of reimplementing patterns

---

## Phase 1: Update Helper Exports [0/2]

### Task 1.1: Update helpers/__init__.py
- Add exports for `fixtures.py` functions
- Add exports for `env_setup.py` functions
- Add exports for `cache_utils.py` functions

### Task 1.2: Verify helper imports work correctly
- Test that `from tests.helpers import setup_project_root` works
- Test that `from helpers import setup_project_root` works

---

## Phase 2: Consolidate Duplicated Functions [0/4]

### Task 2.1: Move reset_session_store_cache to helpers/cache_utils.py
- Source files: `unit/session/persistence/test_session_store.py`, `unit/session/recovery/test_session_recovery.py`
- Target: `helpers/cache_utils.py`

### Task 2.2: Move create_markdown_task to helpers/markdown_utils.py
- Source files: `unit/task/test_task_repository_sessions.py`, `unit/task/test_task_repository_finder.py`
- Target: `helpers/markdown_utils.py`

### Task 2.3: Move create_task_file/create_qa_file to helpers/
- Source files: `unit/task/test_task_repository_workflow.py`, `unit/qa/test_qa_repository_workflow.py`
- Target: `helpers/markdown_utils.py` or new `helpers/entity_utils.py`

### Task 2.4: Update all callers to use centralized functions
- Update imports in all affected files

---

## Phase 3: Adopt Helpers in Task Tests [0/10]

Files to update:
1. `unit/task/test_task_repository_workflow.py`
2. `unit/task/test_task_repository_create.py`
3. `unit/task/test_io_mkdir.py`
4. `unit/task/test_task_store_and_finder.py`
5. `unit/task/test_task_repository_finder.py`
6. `unit/task/test_task_repository_sessions.py`
7. `unit/task/test_task_config.py`
8. `unit/task/test_no_hardcoded_states.py`
9. `unit/task/test_transition_task_validator_approval.py`
10. `unit/task/conftest.py`

Pattern to replace:
```python
# OLD
monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
reset_edison_caches()

# NEW
from tests.helpers.env_setup import setup_project_root
setup_project_root(monkeypatch, tmp_path)
```

---

## Phase 4: Adopt Helpers in Session Tests [0/15]

Files to update:
1. `unit/session/test_no_legacy_project_root_guard.py`
2. `unit/session/test_session_paths.py`
3. `unit/session/validation/test_session_transaction_api.py`
4. `unit/session/persistence/test_session_atomic_write.py`
5. `unit/session/persistence/test_session_state.py`
6. `unit/session/persistence/test_session_store.py`
7. `unit/session/worktree/test_manager_worktree_delegation.py`
8. `unit/session/worktree/test_autostart_worktree_delegation.py`
9. `unit/session/worktree/test_worktree_hardcoded_timeouts.py`
10. `unit/session/worktree/test_session_worktree.py`
11. `unit/session/manager/test_session_context.py`
12. `unit/session/config/test_session_template_resolution.py`
13. `unit/session/recovery/test_session_recovery.py`
14. `unit/session/recovery/test_session_exception_handling.py`
15. `unit/session/conftest.py`

---

## Phase 5: Adopt Helpers in Other Unit Tests [0/15]

Files to update:
1. `unit/state/test_unified_validation.py`
2. `unit/state/test_session_state_unified.py`
3. `unit/qa/test_qa_repository_workflow.py`
4. `unit/qa/test_qa_config.py`
5. `unit/qa/conftest.py`
6. `unit/paths/test_resolver_json_io.py`
7. `unit/paths/test_repo_root_consolidation.py`
8. `unit/lib/test_paths.py`
9. `unit/lib/test_pathlib.py`
10. `unit/lib/test_qa_store_rounds_bundler.py`
11. `unit/lib/test_tasklib_root_resolution.py`
12. `unit/lib/test_locklib.py`
13. `unit/lib/test_management_path_usage.py`
14. `unit/config/loading/test_config_manager.py`
15. `unit/utils/test_resilience_config.py`

---

## Phase 6: Adopt Helpers in E2E/Integration Tests [0/10]

Files to update:
1. `e2e/framework/git/test_atomic_git_move.py`
2. `e2e/framework/validation/test_validation_transaction_sessionlib.py`
3. `e2e/framework/config/test_core_configuration.py`
4. `e2e/scenarios/test_07_context7_enforcement.py`
5. `integration/test_session_autostart.py`
6. `unit/rules/test_validator_approval.py`
7. `unit/scripts/test_session_db_scripts.py`
8. `unit/cli/test_edison_entrypoint.py`
9. `unit/utils/test_cli_output.py`
10. `unit/config/domains/test_project_metadata_config.py`

---

## Phase 7: Final Verification [0/3]

### Task 7.1: Run grep to verify no remaining direct patterns
```bash
grep -r "monkeypatch.setenv.*AGENTS_PROJECT_ROOT" tests/ --include="*.py" | grep -v helpers | grep -v conftest.py
```

### Task 7.2: Run tests to verify no regressions
```bash
pnpm test
```

### Task 7.3: Commit all changes
```bash
git add -A && git commit -m "refactor(tests): Complete DRY adoption - use centralized helpers"
```

---

## Summary

| Phase | Description | Files | Status |
|-------|-------------|-------|--------|
| 1 | Update Helper Exports | 1 | PENDING |
| 2 | Consolidate Duplicated Functions | 4 | PENDING |
| 3 | Adopt Helpers in Task Tests | 10 | PENDING |
| 4 | Adopt Helpers in Session Tests | 15 | PENDING |
| 5 | Adopt Helpers in Other Unit Tests | 15 | PENDING |
| 6 | Adopt Helpers in E2E/Integration Tests | 10 | PENDING |
| 7 | Final Verification | 3 | PENDING |
| **TOTAL** | | **58** | **0 Completed** |
