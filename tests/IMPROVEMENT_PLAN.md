# Test Suite Improvement Plan

## Status: PHASE 4 COMPLETE ✅
**Created**: 2025-11-30
**Last Updated**: 2025-11-30 (Final Phase 4 Results)

---

## Test Results Summary

| Metric | Initial | Phase 1 | Phase 2a | Phase 2b | Phase 2c | Phase 3 | Phase 4 |
|--------|---------|---------|----------|----------|----------|---------|---------|
| Passed | 1537 | 1566 | 1602 | 1611 | 1631 | 1678 | 1692 |
| Failed | 488 | 459 | 423 | 414 | 394 | 380 | 366 |
| Skipped | 185 | 185 | 185 | 185 | 185 | 187 | 187 |
| Total | 2210 | 2210 | 2210 | 2210 | 2210 | 2245 | 2245 |

**Total Progress**: 122 tests fixed (25% improvement)

---

## Completed Phases

### Phase 1: Core Infrastructure (✅ COMPLETE - 29 tests fixed)
- [x] Fix circular import in qa/session modules (lazy imports)
- [x] Fix missing get_current_owner export
- [x] Fix missing get_task_states import path
- [x] Fix AgentRegistry repo_root -> project_root refactoring
- [x] Fix ValidatorRegistry helper functions
- [x] Fix rosters.py repo_root references
- [x] Fix tests.helpers.session missing attributes
- [x] Add AgentRegistry.get_all_metadata() method

### Phase 2a: Attribute/Import/Config Errors (✅ COMPLETE - 36 tests fixed)
- [x] Add load_delegation_config, load_validation_config to QAConfig
- [x] Add _sessions_root alias to recovery module
- [x] Add list_recoverable_sessions to resilience module
- [x] Add extract_anchor_content static method to RulesRegistry
- [x] Fix CompositionEngine -> GuidelineRegistry import
- [x] Fix autostart module import path
- [x] Fix _reset_all_global_caches -> reset_edison_caches
- [x] ConfigManager now loads both .yml and .yaml from core config

### Phase 2b: E2E Quick Wins (✅ COMPLETE - 9 tests fixed)
- [x] Created recovery scripts (clear-locks, recover-validation-tx, repair-session, clean-worktrees)
- [x] Fixed _validate_refactor_cycle signature mismatch
- [x] Fixed session cleanup in tests (autouse fixture)
- [x] Fixed git repo detection (real git init)

### Phase 2c: Parameter Names and Module Imports (✅ COMPLETE - 20 tests fixed)
- [x] Fixed repo_root -> project_root in validator tests
- [x] Fixed module imports (context7, transaction)
- [x] Fixed SetupQuestionnaire _context_with_defaults

### Phase 3a: Circular Import Fix (✅ COMPLETE)
- [x] Fixed circular import between orchestrator and session.lifecycle.autostart
- [x] Used lazy imports for OrchestratorLauncher in autostart.py
- [x] Removed redundant OrchestratorError catch block

### Phase 3b: Hook Tests Fix (✅ COMPLETE - 10 tests fixed)
- [x] Updated test_hooks.py to use correct config paths (.edison/config/hooks.yml)
- [x] Fixed tests to account for bundled core hooks from edison.data
- [x] Updated pack config tests to write packs.active to disk config
- [x] Fixed all 10 hook composition tests

### Phase 3c: Database Config Tests (✅ COMPLETE - 5 tests fixed)
- [x] Fixed config path from .edison/core/config to .edison/config
- [x] Removed outdated database._CONFIG pattern
- [x] Added proper cache clearing with reset_config_cache()

### Phase 3d: Launcher Tests (✅ COMPLETE - 8 tests fixed)
- [x] Fixed write_orchestrator_config helper to use `orchestrators:` key
- [x] Changed tests to write to project config (.edison/config)
- [x] Added reset_edison_caches() after config writes

### Phase 3e: CLI Output/Confirm Tests (✅ COMPLETE - 4 tests fixed)
- [x] Added AGENTS_PROJECT_ROOT to subprocess environment
- [x] Fixed confirm() to use function parameter instead of global default
- [x] Removed invalid global `default` key from config
- [x] Cleaned up legacy CLIConfig code

### Phase 3f: Subprocess Timeout Tests (✅ COMPLETE - 3 tests fixed)
- [x] Fixed config path to use .edison/config/timeouts.yaml
- [x] Added missing timeout type mappings (db_operations, json_io_lock)
- [x] Updated tests to use correct timeout type names

---

## Remaining Failures (366 tests)

### Top Failing Test Categories
1. **E2E scenario tests** (~100 tests) - Command execution failures
2. **State machine tests** (~25 tests) - State transition logic
3. **Script tests** (~40 tests) - CLI script execution
4. **Integration tests** (~50 tests) - External dependencies
5. **Misc unit tests** (~150 tests) - Various root causes

### Common Error Patterns
1. Script subprocess execution failures
2. State transition validation issues
3. Git/worktree operation failures
4. Session lifecycle issues
5. Validation transaction failures

---

## Key Fixes Applied

### Configuration System Fixes
- Tests now write to `.edison/config/*.yaml` (project overrides), not `.edison/core/config/`
- ConfigManager loads bundled defaults from `edison.data/config/` merged with project overrides
- Proper cache clearing with `reset_edison_caches()` and `clear_all_caches()`

### Import/Circular Dependency Fixes
- Lazy imports to break circular dependencies (qa/session, orchestrator/autostart)
- Proper module re-exports following refactoring conventions

### Test Infrastructure Fixes
- Correct YAML key names (`orchestrators:` not `orchestrator:`)
- Environment variable passing to subprocesses
- Proper fixture cleanup with autouse fixtures

---

## Files Modified

### Source Code
- src/edison/core/session/lifecycle/autostart.py - Lazy imports
- src/edison/core/utils/cli/output.py - Fixed confirm() logic
- src/edison/core/utils/subprocess.py - Added timeout type mappings
- src/edison/core/config/domains/cli.py - Cleaned up legacy code
- src/edison/data/config/defaults.yaml - Removed invalid config keys

### Test Files
- tests/unit/composition/test_hooks.py - Fixed config paths and bundled hook handling
- tests/unit/config/domains/test_database_config.py - Fixed config loading
- tests/unit/cli/orchestrator/test_launcher.py - Fixed profile config
- tests/unit/utils/test_cli_output.py - Fixed subprocess env
- tests/unit/utils/test_subprocess_wrapper.py - Fixed timeout config
- tests/helpers/io_utils.py - Fixed write_orchestrator_config helper
