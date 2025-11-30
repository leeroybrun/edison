# Test Suite Improvement Plan

## Status: IN PROGRESS - PHASE 2
**Created**: 2025-11-30
**Last Updated**: 2025-11-30 (After Phase 1 Fixes)

---

## Test Results Summary

| Metric | Initial | After Phase 1 |
|--------|---------|---------------|
| Passed | 1537 | 1566 |
| Failed | 488 | 459 |
| Skipped | 185 | 185 |
| Total | 2210 | 2210 |

**Progress**: 29 tests fixed (6% improvement)

---

## Phase 1: Core Infrastructure (✅ COMPLETE)

- [x] Fix circular import in qa/session modules (lazy imports)
- [x] Fix missing get_current_owner export
- [x] Fix missing get_task_states import path
- [x] Fix AgentRegistry repo_root -> project_root refactoring
- [x] Fix ValidatorRegistry helper functions
- [x] Fix rosters.py repo_root references
- [x] Fix tests.helpers.session missing attributes (validation_transaction, _get_project_name, _get_database_url)
- [x] Add AgentRegistry.get_all_metadata() method

---

## Phase 2: Remaining Test Failures (IN PROGRESS)

### Statistics (459 failing tests)
- **230 unique failing tests**
- **434 error instances**
- **16 distinct categories**

---

### Priority 1: Critical Infrastructure (🔴 HIGH)

#### Task 2.1: Fix Attribute Errors (7 instances)
**Status**: [ ] PENDING
**Missing Attributes:**
1. `edison.core.config.domains.qa.load_delegation_config`
2. `edison.core.config.domains.qa.load_validation_config`
3. `edison.core.session.lifecycle.recovery._sessions_root`
4. `edison.core.utils.resilience.list_recoverable_sessions`
5. `RulesRegistry.extract_anchor_content`

**Affected Files:**
- tests/e2e/framework/error/test_error_handling.py
- tests/unit/lib/test_management_path_usage.py
- tests/unit/qa/test_qa_config_export.py
- tests/unit/utils/test_timestamp_refactor.py

#### Task 2.2: Fix Import Errors (7 instances)
**Status**: [ ] PENDING
**Errors:**
- `cannot import name 'CompositionEngine' from 'edison.core.composition'`
- `No module named 'edison.core.session.autostart'`
- `cannot import name '_reset_all_global_caches' from 'tests.conftest'`

**Affected Files:**
- tests/e2e/test_mcp_integration.py
- tests/unit/lib/test_management_path_usage.py
- tests/unit/fixtures/test_conftest_no_legacy_tasks.py

#### Task 2.3: Fix MCP Config Runtime Errors (4 instances)
**Status**: [ ] PENDING
**Error:** `RuntimeError: mcp configuration section is missing`
**Affected Files:**
- tests/unit/utils/test_mcp_call_generation.py
- tests/unit/utils/test_cli_output.py

---

### Priority 2: E2E Test Failures (🟠 MEDIUM-HIGH)

#### Task 2.4: Fix Command Failures (96 instances)
**Status**: [ ] PENDING
**Most Affected:**
- tests/e2e/scenarios/test_10_edge_cases.py (15 tests)
- tests/e2e/scenarios/test_05_git_based_detection.py (12 tests)
- tests/e2e/scenarios/test_11_complex_scenarios.py (11 tests)

#### Task 2.5: Fix E2E Session/State Tests (50+ instances)
**Status**: [ ] PENDING
**Categories:**
- Session lifecycle failures
- State machine validation errors
- Recovery workflow issues

---

### Priority 3: File/Configuration Issues (🟡 MEDIUM)

#### Task 2.6: Fix Data Structure Issues (58 instances)
**Status**: [ ] PENDING
**Affected:** JSON/YAML parsing and schema mismatches

#### Task 2.7: Fix File Not Found Errors (41 instances)
**Status**: [ ] PENDING
**Missing:** Test data, config files, generated artifacts

#### Task 2.8: Fix Delegation Documentation (14 instances)
**Status**: [ ] PENDING
**Missing Files:**
- `.agents/delegation/README.md`
- `.agents/delegation/config.json`

---

### Priority 4: Cleanup (🟢 LOW)

#### Task 2.9: Fix Assertion Failures (63 instances)
**Status**: [ ] PENDING
**Requires:** Individual analysis of test expectations

#### Task 2.10: Fix Uncategorized Failures (75 instances)
**Status**: [ ] PENDING
**Top Errors:**
- jinja2.exceptions.UndefinedError
- SessionError: Session already exists
- Various state mismatches

---

## Execution Strategy

1. **Phase 2a**: Fix Priority 1 issues (attribute/import/config errors)
2. **Phase 2b**: Fix E2E command failures
3. **Phase 2c**: Fix file/configuration issues
4. **Phase 2d**: Cleanup remaining failures
5. **Phase 3**: Final verification - all tests must pass

---

## Progress Tracking

| Task | Category | Status | Tests Fixed |
|------|----------|--------|-------------|
| 2.1 | Attribute Errors | ⏳ PENDING | 0 |
| 2.2 | Import Errors | ⏳ PENDING | 0 |
| 2.3 | MCP Config | ⏳ PENDING | 0 |
| 2.4 | Command Failures | ⏳ PENDING | 0 |
| 2.5 | Session/State | ⏳ PENDING | 0 |
| 2.6 | Data Structure | ⏳ PENDING | 0 |
| 2.7 | File Not Found | ⏳ PENDING | 0 |
| 2.8 | Delegation Docs | ⏳ PENDING | 0 |
| 2.9 | Assertions | ⏳ PENDING | 0 |
| 2.10 | Uncategorized | ⏳ PENDING | 0 |
| **TOTAL** | | | **0** |

---

## Files Modified in Phase 1

### Source Code
1. `src/edison/core/session/next/actions.py` - Lazy imports for QARepository
2. `src/edison/core/session/lifecycle/verify.py` - Lazy imports
3. `src/edison/core/session/lifecycle/__init__.py` - Lazy wrapper
4. `src/edison/core/utils/process/__init__.py` - Added get_current_owner
5. `src/edison/core/utils/process/inspector.py` - Added get_current_owner
6. `src/edison/core/composition/registries/agents.py` - project_root refactor, get_all_metadata()
7. `src/edison/core/composition/registries/validators.py` - project_root refactor
8. `src/edison/core/composition/registries/rosters.py` - project_root refactor
9. `src/edison/core/composition/orchestrator.py` - project_root refactor
10. `src/edison/core/adapters/sync/cursor.py` - project_root refactor

### Test Code
1. `tests/unit/task/test_no_hardcoded_states.py` - Updated import path
2. `tests/unit/composition/test_rosters.py` - Updated API usage
3. `tests/helpers/session.py` - Added missing functions
