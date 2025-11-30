# Test Directory Restructuring Plan

## Status: IN PROGRESS
**Last Updated**: 2025-11-30
**Total Tasks**: 67
**Completed**: 9
**In Progress**: 2
**Pending**: 56

---

## Phase 1: Delete Empty Directories [3/3] ✅ COMPLETE

### Task 1.1: Delete tests/tracking/
- [x] **Status**: COMPLETED
- **Action**: Remove empty `tests/tracking/` directory
- **Result**: Verified empty, deleted successfully

### Task 1.2: Delete tests/unit/core/orchestrator/
- [x] **Status**: COMPLETED
- **Action**: Remove empty `tests/unit/core/orchestrator/` directory
- **Result**: Verified empty, deleted successfully

### Task 1.3: Delete tests/unit/adapters/sync/
- [x] **Status**: COMPLETED
- **Action**: Remove empty `tests/unit/adapters/sync/` directory
- **Result**: Verified empty, deleted successfully

---

## Phase 2: Resolve Duplicate File Names [6/8] 🔄 IN PROGRESS

### Task 2.1: Analyze and merge test_guidelines_sanitization.py duplicates
- [x] **Status**: COMPLETED
- **Files**:
  - `tests/guidelines/test_guidelines_sanitization.py` - Tests bundled package data guidelines
  - `tests/e2e/framework/validation/test_guidelines_sanitization.py` - Tests project-level core guidelines
- **Result**: Renamed e2e version to `test_project_guidelines_sanitization.py`

### Task 2.2: Analyze and merge test_guidelines_structure.py duplicates
- [x] **Status**: COMPLETED
- **Files**:
  - `tests/guidelines/test_guidelines_structure.py` - Tests bundled package data structure
  - `tests/e2e/framework/validation/test_guidelines_structure.py` - Tests project-level structure
- **Result**: Renamed e2e version to `test_project_guidelines_structure.py`

### Task 2.3: Rename test_config.py in unit/cli/orchestrator
- [x] **Status**: COMPLETED
- **File**: `tests/unit/cli/orchestrator/test_config.py`
- **New Name**: `test_orchestrator_config.py`
- **Result**: Renamed successfully

### Task 2.4: Rename test_config.py in e2e/framework/config
- [x] **Status**: COMPLETED
- **File**: `tests/e2e/framework/config/test_config.py`
- **New Name**: `test_config_manager_e2e.py`
- **Result**: Renamed successfully

### Task 2.5: Analyze and merge test_validation_transaction.py duplicates
- [x] **Status**: COMPLETED
- **Files**:
  - `tests/validators/test_validation_transaction.py` → `test_validation_transaction_core.py`
  - `tests/e2e/framework/validation/test_validation_transaction.py` → `test_validation_transaction_sessionlib.py`
- **Result**: Both files renamed successfully

### Task 2.6: Update all imports after file renames
- [x] **Status**: COMPLETED
- **Result**: No imports found - test files are standalone

### Task 2.7: Run tests to verify renames don't break anything
- [ ] **Status**: PENDING
- **Action**: Run `pnpm test` or equivalent to verify all tests pass after renames

### Task 2.8: Commit Phase 2 changes
- [ ] **Status**: PENDING
- **Action**: `git add . && git commit -m "refactor(tests): resolve duplicate file names for coherence"`

---

## Phase 3: Consolidate Nearly-Empty Directories [0/14]

### Task 3.1: Move tests/conftest/test_start_session_fixture.py
- [ ] **Status**: PENDING
- **From**: `tests/conftest/test_start_session_fixture.py`
- **To**: `tests/unit/fixtures/test_start_session_fixture.py`
- **Also**: Delete empty `tests/conftest/` directory after move
- **Update imports**: Check if any file imports from this module

### Task 3.2: Move tests/entity/test_repository_transition.py
- [ ] **Status**: PENDING
- **From**: `tests/entity/test_repository_transition.py`
- **To**: `tests/unit/data/test_repository_transition.py`
- **Also**: Delete empty `tests/entity/` directory after move

### Task 3.3: Move tests/entrypoint/test_bin_edison.py
- [ ] **Status**: PENDING
- **From**: `tests/entrypoint/test_bin_edison.py`
- **To**: `tests/cli/test_bin_edison.py`
- **Also**: Delete empty `tests/entrypoint/` directory after move

### Task 3.4: Move tests/performance/test_autostart_performance.py
- [ ] **Status**: PENDING
- **From**: `tests/performance/test_autostart_performance.py`
- **To**: `tests/e2e/test_autostart_performance.py`
- **Also**: Delete empty `tests/performance/` directory after move

### Task 3.5: Move tests/process/test_inspector.py
- [ ] **Status**: PENDING
- **From**: `tests/process/test_inspector.py`
- **To**: `tests/unit/lib/test_inspector.py`
- **Also**: Delete empty `tests/process/` directory after move

### Task 3.6: Move tests/tdd/ files to tests/unit/
- [ ] **Status**: PENDING
- **Files**:
  - `tests/tdd/test_tdd_example.py` → `tests/unit/tdd/test_tdd_example.py`
  - `tests/tdd/test_test_layout_structure.py` → `tests/unit/tdd/test_test_layout_structure.py`
- **Also**: Delete empty `tests/tdd/` directory after move

### Task 3.7: Move tests/templates/ files to tests/unit/composition/
- [ ] **Status**: PENDING
- **Files**:
  - `tests/templates/test_command_templates.py` → `tests/unit/composition/templates/test_command_templates.py`
  - `tests/templates/test_hook_templates.py` → `tests/unit/composition/templates/test_hook_templates.py`
- **Also**: Delete empty `tests/templates/` directory after move

### Task 3.8: Move tests/constitutions/test_core_constitution_templates.py
- [ ] **Status**: PENDING
- **From**: `tests/constitutions/test_core_constitution_templates.py`
- **To**: `tests/unit/composition/test_core_constitution_templates.py`
- **Also**: Delete empty `tests/constitutions/` directory after move

### Task 3.9: Move tests/legacy/ files to tests/unit/
- [ ] **Status**: PENDING
- **Files**:
  - `tests/legacy/test_no_legacy_imports_in_core_libs.py` → `tests/unit/legacy/test_no_legacy_imports_in_core_libs.py`
  - `tests/legacy/test_no_legacy_json_configs_cleanup.py` → `tests/unit/legacy/test_no_legacy_json_configs_cleanup.py`
- **Also**: Delete empty `tests/legacy/` directory after move

### Task 3.10: Move tests/verification/test_final_acceptance.py
- [ ] **Status**: PENDING
- **From**: `tests/verification/test_final_acceptance.py`
- **To**: `tests/e2e/test_final_acceptance.py`
- **Also**: Delete empty `tests/verification/` directory after move

### Task 3.11: Move tests/implementation/ files to tests/unit/
- [ ] **Status**: PENDING
- **Files**:
  - `tests/implementation/test_implementation_validate_wrapper.py` → `tests/unit/implementation/test_implementation_validate_wrapper.py`
  - `tests/implementation/test_stdout_stderr_conventions.py` → `tests/unit/implementation/test_stdout_stderr_conventions.py`
- **Also**: Delete empty `tests/implementation/` directory after move

### Task 3.12: Move tests/git/test_operations.py
- [ ] **Status**: PENDING
- **From**: `tests/git/test_operations.py`
- **To**: `tests/unit/git/test_operations.py`
- **Also**: Delete empty `tests/git/` directory after move

### Task 3.13: Move tests/data/ test files to tests/unit/data/
- [ ] **Status**: PENDING
- **Files**:
  - `tests/data/test_agent_frontmatter.py` → Keep in `tests/unit/data/` (already exists there or merge)
  - `tests/data/test_database_architect_schema_template.py` → `tests/unit/data/test_database_architect_schema_template.py`
- **Keep**: `tests/data/config/` as test fixture data (rename to `tests/fixtures/data/config/`)
- **Also**: Delete empty `tests/data/` directory after moves

### Task 3.14: Commit Phase 3 changes
- [ ] **Status**: PENDING
- **Action**: `git add . && git commit -m "refactor(tests): consolidate nearly-empty directories"`

---

## Phase 4: Move Root-Level Test Files [0/8]

### Task 4.1: Move test_orchestrator.py
- [ ] **Status**: PENDING
- **From**: `tests/test_orchestrator.py`
- **To**: `tests/unit/cli/test_orchestrator.py`

### Task 4.2: Move test_other_modules.py
- [ ] **Status**: PENDING
- **From**: `tests/test_other_modules.py`
- **To**: `tests/unit/test_other_modules.py`

### Task 4.3: Move test_conftest_no_legacy_tasks.py
- [ ] **Status**: PENDING
- **From**: `tests/test_conftest_no_legacy_tasks.py`
- **To**: `tests/unit/fixtures/test_conftest_no_legacy_tasks.py`

### Task 4.4: Move test_isolated_project_env_scaffolding.py
- [ ] **Status**: PENDING
- **From**: `tests/test_isolated_project_env_scaffolding.py`
- **To**: `tests/unit/fixtures/test_isolated_project_env_scaffolding.py`

### Task 4.5: Move test_timestamp_refactor.py
- [ ] **Status**: PENDING
- **From**: `tests/test_timestamp_refactor.py`
- **To**: `tests/unit/utils/test_timestamp_refactor.py`

### Task 4.6: Move test_cursor_adapter_merge.py
- [ ] **Status**: PENDING
- **From**: `tests/test_cursor_adapter_merge.py`
- **To**: `tests/unit/adapters/test_cursor_adapter_merge.py`

### Task 4.7: Move test_no_legacy_imports.py
- [ ] **Status**: PENDING
- **From**: `tests/test_no_legacy_imports.py`
- **To**: `tests/unit/legacy/test_no_legacy_imports.py`

### Task 4.8: Commit Phase 4 changes
- [ ] **Status**: PENDING
- **Action**: `git add . && git commit -m "refactor(tests): move root-level test files to appropriate directories"`

---

## Phase 5: Consolidate Session Tests [0/6]

### Task 5.1: Audit session test coverage overlap
- [ ] **Status**: PENDING
- **Locations to audit**:
  1. `tests/session/` (7 files + 7 subdirectories)
  2. `tests/e2e/framework/session/` (6 files)
  3. `tests/unit/session/` (4 files)
  4. `tests/unit/lib/session/` (1 file)
- **Action**: Create mapping of which tests cover which functionality

### Task 5.2: Merge tests/session/ into tests/unit/session/
- [ ] **Status**: PENDING
- **Subdirectories to merge**:
  - `tests/session/config/` → `tests/unit/session/config/` (merge or move)
  - `tests/session/lifecycle/` → `tests/unit/session/lifecycle/`
  - `tests/session/manager/` → `tests/unit/session/manager/`
  - `tests/session/naming/` → `tests/unit/session/naming/`
  - `tests/session/next/` → `tests/unit/session/next/`
  - `tests/session/persistence/` → `tests/unit/session/persistence/`
  - `tests/session/recovery/` → `tests/unit/session/recovery/`
  - `tests/session/validation/` → `tests/unit/session/validation/`
  - `tests/session/worktree/` → `tests/unit/session/worktree/`
- **Root files**: Move to appropriate subdirectories based on content

### Task 5.3: Move tests/unit/lib/session/ content
- [ ] **Status**: PENDING
- **From**: `tests/unit/lib/session/test_layout.py`
- **To**: `tests/unit/session/test_layout.py`
- **Delete**: Empty `tests/unit/lib/session/` after move

### Task 5.4: Update tests/session/conftest.py
- [ ] **Status**: PENDING
- **Action**: Merge session-specific fixtures into main conftest or keep in unit/session/conftest.py

### Task 5.5: Delete empty tests/session/ after consolidation
- [ ] **Status**: PENDING
- **Action**: Remove empty directory tree

### Task 5.6: Commit Phase 5 changes
- [ ] **Status**: PENDING
- **Action**: `git add . && git commit -m "refactor(tests): consolidate session tests under unit/session/"`

---

## Phase 6: Consolidate State Tests [0/4]

### Task 6.1: Audit state test coverage
- [ ] **Status**: PENDING
- **Files in tests/state/**:
  - `test_rich_state_machine.py`
  - `test_session_state_unified.py`
  - `test_state_validator.py`
  - `test_unified_validation.py`
- **Files in tests/e2e/framework/state/**:
  - `test_state_machine_docs.py`
  - `test_state_machine_guards.py`
  - `test_state_transitions.py`

### Task 6.2: Move tests/state/ to tests/unit/state/
- [ ] **Status**: PENDING
- **Action**: Move all 4 files to `tests/unit/state/`
- **Verify**: No duplicates with existing unit/state files

### Task 6.3: Delete empty tests/state/
- [ ] **Status**: PENDING
- **Action**: Remove empty directory

### Task 6.4: Commit Phase 6 changes
- [ ] **Status**: PENDING
- **Action**: `git add . && git commit -m "refactor(tests): consolidate state tests under unit/state/"`

---

## Phase 7: Consolidate Top-Level Domain Directories [0/12]

### Task 7.1: Move tests/adapters/ to tests/unit/adapters/
- [ ] **Status**: PENDING
- **Files**:
  - `test_claude_full_integration.py`
  - `test_command_integration.py`
  - `test_cursor_snapshot.py`
  - `test_prompt_adapters.py`
  - `test_schema_refactor.py`
- **Action**: Merge with existing `tests/unit/adapters/`

### Task 7.2: Move tests/cli/ to tests/unit/cli/
- [ ] **Status**: PENDING
- **Files**:
  - `test_cli_uses_utilities.py`
  - `test_compose_all_paths.py`
  - `test_compose_orchestrator_removal.py`
  - `test_edison_entrypoint.py`
  - `test_session_cli_imports.py`
- **Action**: Merge with existing `tests/unit/cli/`

### Task 7.3: Move tests/delegation/ to tests/unit/delegation/
- [ ] **Status**: PENDING
- **Files**: 7 test files
- **Action**: Create `tests/unit/delegation/` and move all files

### Task 7.4: Move tests/guidelines/ to tests/unit/guidelines/
- [ ] **Status**: PENDING
- **Files**: 10 test files
- **Action**: Create `tests/unit/guidelines/` and move all files

### Task 7.5: Move tests/lib/ to tests/unit/lib/
- [ ] **Status**: PENDING
- **Files**: 7 test files
- **Action**: Merge with existing `tests/unit/lib/`

### Task 7.6: Move tests/packs/ to tests/unit/packs/
- [ ] **Status**: PENDING
- **Files**: 7 test files
- **Action**: Create `tests/unit/packs/` and move all files

### Task 7.7: Move tests/rules/ to tests/unit/rules/
- [ ] **Status**: PENDING
- **Files**: 8 test files
- **Action**: Create `tests/unit/rules/` and move all files

### Task 7.8: Move tests/scripts/ to tests/unit/scripts/
- [ ] **Status**: PENDING
- **Files**: 13 test files + __init__.py
- **Action**: Merge with existing `tests/unit/scripts/`

### Task 7.9: Move tests/task/ to tests/unit/task/
- [ ] **Status**: PENDING
- **Files**: 18 test files + conftest.py
- **Action**: Create `tests/unit/task/` and move all files

### Task 7.10: Move tests/utils/ to tests/unit/utils/
- [ ] **Status**: PENDING
- **Files**: 10 test files
- **Action**: Merge with existing `tests/unit/utils/`

### Task 7.11: Move tests/validators/ to tests/unit/validators/
- [ ] **Status**: PENDING
- **Files**: 5 test files
- **Action**: Create `tests/unit/validators/` and move all files

### Task 7.12: Commit Phase 7 changes
- [ ] **Status**: PENDING
- **Action**: `git add . && git commit -m "refactor(tests): consolidate top-level domain directories under unit/"`

---

## Phase 8: Consolidate IDE and Start Tests [0/4]

### Task 8.1: Move tests/ide/ to tests/unit/ide/
- [ ] **Status**: PENDING
- **Files**:
  - `test_settings_io.py`
  - `test_settings_refactor.py`
- **Action**: Create `tests/unit/ide/` and move files

### Task 8.2: Move tests/start/ to tests/unit/start/
- [ ] **Status**: PENDING
- **Files**:
  - `test_start_state_machine_reference.py`
- **Action**: Merge with existing `tests/unit/core/start/`

### Task 8.3: Delete empty directories
- [ ] **Status**: PENDING
- **Action**: Remove `tests/ide/` and `tests/start/` after moves

### Task 8.4: Commit Phase 8 changes
- [ ] **Status**: PENDING
- **Action**: `git add . && git commit -m "refactor(tests): consolidate IDE and start tests"`

---

## Phase 9: Reorganize Context Directory [0/4]

### Task 9.1: Move context analysis scripts to tests/tools/
- [ ] **Status**: PENDING
- **Files to move from tests/context/**:
  - `baseline_profiler.py` → `tests/tools/context/baseline_profiler.py`
  - `bloat_detector.py` → `tests/tools/context/bloat_detector.py`
  - `context_impact_analyzer.py` → `tests/tools/context/context_impact_analyzer.py`
  - `scenario_simulator.py` → `tests/tools/context/scenario_simulator.py`
  - `token_counter.py` → `tests/tools/context/token_counter.py`
  - `analyze` (script) → `tests/tools/context/analyze`
  - `__init__.py` → `tests/tools/context/__init__.py`
  - `README.md` → `tests/tools/context/README.md`
  - `IMPLEMENTATION_SUMMARY.md` → `tests/tools/context/IMPLEMENTATION_SUMMARY.md`

### Task 9.2: Move comp_samples to fixtures
- [ ] **Status**: PENDING
- **From**: `tests/context/comp_samples/`
- **To**: `tests/fixtures/context/comp_samples/` (merge with existing)
- **Note**: `tests/fixtures/context/comp_samples/` already exists - merge contents

### Task 9.3: Delete empty tests/context/
- [ ] **Status**: PENDING
- **Action**: Remove directory after moves

### Task 9.4: Commit Phase 9 changes
- [ ] **Status**: PENDING
- **Action**: `git add . && git commit -m "refactor(tests): reorganize context directory - separate tools from fixtures"`

---

## Phase 10: Extract Duplicated Code to Helpers [0/10]

### Task 10.1: Create tests/helpers/fixtures.py
- [ ] **Status**: PENDING
- **Action**: Create new file with reusable fixture factories
- **Contents**:
  ```python
  """Reusable fixture factories for test setup."""

  def create_repo_with_config(tmp_path, monkeypatch, config=None):
      """Create a repository with Edison config structure."""
      ...

  def create_minimal_project_structure(project_root):
      """Create minimal .project directory structure."""
      ...

  def setup_config_and_reload(tmp_path, monkeypatch, config_data):
      """Write config and reload affected modules."""
      ...
  ```

### Task 10.2: Create tests/helpers/env_setup.py
- [ ] **Status**: PENDING
- **Action**: Create helper for environment variable setup
- **Contents**:
  ```python
  """Environment setup helpers for tests."""

  def setup_project_root(monkeypatch, project_path):
      """Setup AGENTS_PROJECT_ROOT and reset caches."""
      from tests.helpers.cache_utils import reset_edison_caches
      monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(project_path))
      reset_edison_caches()

  def setup_isolated_environment(monkeypatch, tmp_path):
      """Setup fully isolated test environment."""
      ...
  ```

### Task 10.3: Extend tests/helpers/cache_utils.py
- [ ] **Status**: PENDING
- **Action**: Add module reload helper
- **Add**:
  ```python
  def reload_config_modules(*module_names):
      """Reload Edison config-dependent modules."""
      import importlib
      for name in module_names:
          try:
              mod = importlib.import_module(name)
              importlib.reload(mod)
          except ImportError:
              pass

  CONFIG_MODULES = [
      "edison.core.config.domains.task",
      "edison.core.task.paths",
      "edison.core.utils.paths.resolver",
  ]

  def reset_all_and_reload():
      """Reset caches and reload common config modules."""
      reset_edison_caches()
      reload_config_modules(*CONFIG_MODULES)
  ```

### Task 10.4: Extend tests/helpers/markdown_utils.py
- [ ] **Status**: PENDING
- **Action**: Add file creation functions
- **Add**:
  ```python
  def create_task_file(path, task_id, title="Test Task", state="todo", session_id=None):
      """Create a markdown task file."""
      path.parent.mkdir(parents=True, exist_ok=True)
      lines = [
          f"<!-- Status: {state} -->",
          f"# {title}",
          f"Task ID: {task_id}",
      ]
      if session_id:
          lines.append(f"Session: {session_id}")
      path.write_text("\n".join(lines), encoding="utf-8")
      return path

  def create_qa_file(path, qa_id, title="Test QA", state="pending"):
      """Create a markdown QA file."""
      ...
  ```

### Task 10.5: Extend tests/helpers/json_utils.py
- [ ] **Status**: PENDING
- **Action**: Add session JSON helpers
- **Add**:
  ```python
  def create_session_json(session_id, owner="test", state="draft"):
      """Create session JSON structure."""
      return {
          "meta": {
              "sessionId": session_id,
              "owner": owner,
              "status": state,
          },
          "state": state,
          "tasks": {},
          "qa": {},
      }

  def get_session_field(session_data, field_path):
      """Get field from session JSON with dot notation."""
      parts = field_path.split(".")
      value = session_data
      for part in parts:
          value = value.get(part, {})
      return value if value != {} else None
  ```

### Task 10.6: Extend tests/helpers/path_utils.py
- [ ] **Status**: PENDING
- **Action**: Add state directory helpers
- **Add**:
  ```python
  def ensure_state_directories(project_root, entity_type="session"):
      """Ensure state directories exist for entity type."""
      from tests.config import load_states
      states = load_states()
      dirs = states.get(entity_type, {}).get("directories", {})
      for state, dirname in dirs.items():
          path = project_root / ".project" / f"{entity_type}s" / dirname
          path.mkdir(parents=True, exist_ok=True)
      return dirs

  def get_state_directory(project_root, entity_type, state, entity_id):
      """Get directory for entity in specific state."""
      from tests.config import load_states
      states = load_states()
      dirname = states.get(entity_type, {}).get("directories", {}).get(state, state)
      return project_root / ".project" / f"{entity_type}s" / dirname / entity_id
  ```

### Task 10.7: Update tests that use duplicated patterns
- [ ] **Status**: PENDING
- **Action**: Find and update tests using duplicated patterns
- **Files to update** (sample - need full search):
  - `tests/task/test_task_repository_finder.py`
  - `tests/task/test_task_repository_create.py`
  - `tests/session/persistence/test_session_store.py`
  - All files using `resolver._PROJECT_ROOT_CACHE = None`
  - All files using `monkeypatch.setenv("AGENTS_PROJECT_ROOT", ...)`

### Task 10.8: Ensure helpers/__init__.py exports all helpers
- [ ] **Status**: PENDING
- **Action**: Update `tests/helpers/__init__.py` to export new functions
- **Add imports for**:
  - `fixtures`
  - `env_setup`
  - New functions in extended helpers

### Task 10.9: Run tests to verify helper changes
- [ ] **Status**: PENDING
- **Action**: Run full test suite to verify no regressions

### Task 10.10: Commit Phase 10 changes
- [ ] **Status**: PENDING
- **Action**: `git add . && git commit -m "refactor(tests): extract duplicated code to helpers"`

---

## Phase 11: Final Cleanup and Verification [0/8]

### Task 11.1: Remove duplicate fixtures/context/comp_samples/deep if empty
- [ ] **Status**: PENDING
- **Path**: `tests/fixtures/context/comp_samples/deep/`
- **Action**: Check if empty and delete or merge

### Task 11.2: Verify no broken imports
- [ ] **Status**: PENDING
- **Action**: Run `python -c "import tests"` and check for import errors

### Task 11.3: Verify all __init__.py files exist
- [ ] **Status**: PENDING
- **Action**: Ensure all new directories have `__init__.py`

### Task 11.4: Run full test suite
- [ ] **Status**: PENDING
- **Action**: `pnpm test` or equivalent
- **Verify**: All tests pass

### Task 11.5: Update any documentation referencing old paths
- [ ] **Status**: PENDING
- **Files to check**:
  - `tests/README.md`
  - Any CI/CD configs referencing test paths

### Task 11.6: Clean up any leftover empty directories
- [ ] **Status**: PENDING
- **Action**: Find and remove any remaining empty directories
- **Command**: `find tests -type d -empty -delete`

### Task 11.7: Final structure verification
- [ ] **Status**: PENDING
- **Action**: Verify final structure matches target:
  ```
  tests/
  ├── e2e/
  │   ├── framework/
  │   └── scenarios/
  ├── fixtures/
  │   ├── context/
  │   ├── guidelines/
  │   └── pack-scenarios/
  ├── helpers/
  ├── integration/
  ├── tools/
  │   └── context/
  ├── unit/
  │   ├── adapters/
  │   ├── cli/
  │   ├── composition/
  │   ├── config/
  │   ├── core/
  │   ├── data/
  │   ├── delegation/
  │   ├── file_io/
  │   ├── fixtures/
  │   ├── git/
  │   ├── guidelines/
  │   ├── helpers/
  │   ├── ide/
  │   ├── implementation/
  │   ├── legacy/
  │   ├── lib/
  │   ├── packs/
  │   ├── paths/
  │   ├── qa/
  │   ├── rules/
  │   ├── scripts/
  │   ├── session/
  │   ├── setup/
  │   ├── state/
  │   ├── task/
  │   ├── tdd/
  │   ├── utils/
  │   └── validators/
  ├── config/
  ├── conftest.py
  └── pytest.ini
  ```

### Task 11.8: Final commit
- [ ] **Status**: PENDING
- **Action**: `git add . && git commit -m "refactor(tests): complete test directory restructuring"`

---

## Summary

| Phase | Description | Tasks | Status |
|-------|-------------|-------|--------|
| 1 | Delete Empty Directories | 3 | PENDING |
| 2 | Resolve Duplicate File Names | 8 | PENDING |
| 3 | Consolidate Nearly-Empty Directories | 14 | PENDING |
| 4 | Move Root-Level Test Files | 8 | PENDING |
| 5 | Consolidate Session Tests | 6 | PENDING |
| 6 | Consolidate State Tests | 4 | PENDING |
| 7 | Consolidate Top-Level Domain Directories | 12 | PENDING |
| 8 | Consolidate IDE and Start Tests | 4 | PENDING |
| 9 | Reorganize Context Directory | 4 | PENDING |
| 10 | Extract Duplicated Code to Helpers | 10 | PENDING |
| 11 | Final Cleanup and Verification | 8 | PENDING |
| **TOTAL** | | **67** | **PENDING** |

---

## Execution Notes

1. **Each phase should be committed separately** for easy rollback if needed
2. **Run tests after each phase** to catch regressions early
3. **Update imports** as files are moved
4. **Preserve git history** using `git mv` where possible
5. **Follow TDD**: If tests fail after moves, investigate root cause before proceeding
