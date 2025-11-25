# E2E Test Suite Rewrite Progress

## Executive Summary

**Status:** Phase 1 Complete - Infrastructure Fixed ✅
**Next Phase:** Full Test Suite Rewrite (5-7 weeks estimated)

### Critical Finding (Validated)

All 3 independent LLM reviews (Codex, Gemini, Claude Code) unanimously confirmed:
- **0% of tests execute real CLI commands**
- **100% of tests create mock data directly**
- Tests provide "false sense of safety"

### User Approval

User approved "Option 1: Complete Rewrite" to create tests that execute REAL CLI commands.

---

## Phase 1 Completed ✅

### Infrastructure Fixes

1. **command_runner.py Environment Variables** ✅
   - Changed from `DATA_ROOT` to `project_ROOT` and `project_PROJECT_ROOT`
   - File: `.agents/scripts/tests/e2e/helpers/command_runner.py:44-45`

2. **test_env.py Session Paths** ✅
   - Changed sessions from `.agents/sessions/` to `.project/sessions/`
   - File: `.agents/scripts/tests/e2e/helpers/test_env.py:366-367`

3. **Deprecated Mock Data Methods** ✅
   - Added deprecation warnings to:
     - `create_task()` - line 301-302
     - `create_session()` - line 352-353
     - `create_mock_evidence()` - line 403-404
   - File: `.agents/scripts/tests/e2e/helpers/test_env.py`

4. **Python Package Structure** ✅
   - Created `__init__.py` files for proper imports
   - Added `golden_path` marker to `pytest.ini`

5. **Golden-Path Example Tests** ✅
   - Created `test_00_golden_path_examples.py` demonstrating CORRECT patterns
   - File shows:
     - ✅ HOW to execute real CLI commands
     - ✅ HOW to validate output (stdout/stderr/exit codes)
     - ✅ HOW to test error cases
     - ✅ HOW to test guard enforcement
     - ❌ ANTI-PATTERNS to avoid (mocking data directly)

---

## Validation of Approach

### First Test Execution Result

Ran: `TestTaskCreationRealCLI::test_create_task_via_cli_success`

**Outcome:** Test executed REAL CLI command! ✅

**Output:**
```
STDERR: Task already exists: ${PROJECT_ROOT}/.project/tasks/todo/150-wave1-auth-wave1-auth-implementation.md
```

**Analysis:**
- ✅ Test successfully called `run_script("tasks/new", ...)`
- ✅ Real `tasks/new` CLI was executed
- ✅ CLI correctly detected duplicate task
- ❌ Test discovered root issue: CLI operates on REAL repo, not isolated test environment

**This is EXACTLY what we wanted:** Tests executing REAL code and discovering REAL issues!

---

## Root Issue Discovered

### Problem: CLI Scripts Calculate REPO_ROOT from File Location

**Example:** `tasks/new` line 23:
```python
REPO_ROOT = Path(__file__).resolve().parents[3]
```

The CLI ignores `project_ROOT` environment variable and calculates root from its own location.

### Impact

- Tests run against REAL `.project/` directory instead of isolated `tmp_path`
- Test runs pollute actual project state
- Tests are not isolated

### Solution Options

**Option A: Modify CLI scripts to respect project_ROOT**
```python
import os
REPO_ROOT = Path(os.getenv('project_ROOT', Path(__file__).resolve().parents[3]))
```
- Pros: Clean, simple, tests work immediately
- Cons: Modifies production CLI code for test purposes

**Option B: Copy CLI scripts to test tmp_path**
- Pros: No production code changes
- Cons: Complex setup, doesn't test REAL scripts in their REAL location

**Option C: Run tests against real .project but clean up after**
- Pros: Tests absolutely real behavior
- Cons: Risk of polluting actual project state, harder cleanup

**Recommendation:** Option A - Modify CLI scripts to respect project_ROOT as override.
This is a common testing pattern and doesn't harm production use (falls back to current behavior).

---

## Next Steps

### Immediate (Week 1)

1. **Decide on REPO_ROOT override approach** (requires user approval)
2. **Fix golden-path tests to run in isolation**
3. **Validate all golden-path examples pass**

### Short-term (Weeks 2-3)

4. **Rewrite test_01_session_management.py** (12 tests)
   - Replace all `test_project_dir.create_session()` with `run_script("session", ...)`
   - Validate command output
   - Test error cases

5. **Rewrite test_02_task_lifecycle.py** (15 tests)
   - Replace all `test_project_dir.create_task()` with `run_script("tasks/new", ...)`
   - Use `run_script("tasks/claim", ...)` and `run_script("tasks/status", ...)`
   - Validate transitions

### Medium-term (Weeks 4-5)

6. **Rewrite test_03_qa_lifecycle.py** (14 tests)
7. **Rewrite test_04_worktree_integration.py** (18 tests) - partially correct already
8. **Rewrite test_05_git_based_detection.py** (12 tests)
9. **Rewrite test_06_tracking_system.py** (8 tests)

### Long-term (Weeks 6-7)

10. **Rewrite test_07_context7_enforcement.py** (10 tests)
11. **Rewrite test_08_session_next.py** (14 tests)
12. **Rewrite test_09_evidence_system.py** (9 tests)
13. **Rewrite test_11_complex_scenarios.py** (12 tests)

### Final (Week 7)

14. **Run complete suite and fix root issues**
15. **Document all real CLI behaviors discovered**
16. **Create test coverage report**

---

## Files Modified

### Infrastructure
- `.agents/scripts/tests/e2e/helpers/command_runner.py` - Fixed env vars
- `.agents/scripts/tests/e2e/helpers/test_env.py` - Fixed paths, added deprecation warnings
- `.agents/scripts/tests/e2e/pytest.ini` - Added golden_path marker
- `.agents/scripts/tests/e2e/conftest.py` - Fixed imports
- `.agents/scripts/tests/__init__.py` - Created
- `.agents/scripts/tests/e2e/__init__.py` - Created
- `.agents/scripts/tests/e2e/helpers/__init__.py` - Created
- `.agents/scripts/tests/e2e/scenarios/__init__.py` - Created

### Tests
- `.agents/scripts/tests/e2e/scenarios/test_00_golden_path_examples.py` - Created ✅

### Tests Requiring Rewrite (146 tests total)
- `test_01_session_management.py` (12 tests) - ❌ Uses mock data
- `test_02_task_lifecycle.py` (15 tests) - ❌ Uses mock data
- `test_03_qa_lifecycle.py` (14 tests) - ❌ Uses mock data
- `test_04_worktree_integration.py` (18 tests) - ⚠️ Partial (git real, tasks/qa mock)
- `test_05_git_based_detection.py` (12 tests) - ❌ Uses mock data
- `test_06_tracking_system.py` (8 tests) - ❌ Uses mock data
- `test_07_context7_enforcement.py` (10 tests) - ❌ Uses mock data
- `test_08_session_next.py` (14 tests) - ❌ Uses mock data
- `test_09_evidence_system.py` (9 tests) - ❌ Uses mock data
- `test_11_complex_scenarios.py` (12 tests) - ❌ Uses mock data

---

## Success Metrics

### Phase 1 (Complete) ✅
- [x] Infrastructure fixes applied
- [x] Golden-path examples created
- [x] First test executes REAL CLI command
- [x] Test discovers REAL issue (duplicate detection)

### Phase 2 (Pending)
- [ ] Tests run in isolated environment (tmp_path)
- [ ] All golden-path examples pass
- [ ] Zero mock data creation in active tests

### Phase 3 (Pending)
- [ ] All 146 tests rewritten to use real CLI
- [ ] 100% of tests execute real commands
- [ ] All tests validate stdout/stderr/exit codes
- [ ] Guard enforcement tested

### Final Success Criteria
- [ ] Full test suite passes
- [ ] Tests discover and document real CLI behaviors
- [ ] Zero false confidence - tests only pass if CLIs work
- [ ] Evidence of bugs caught (if CLIs are broken, tests fail)

---

## Lessons Learned

### What Worked ✅

1. **Independent reviews were critical** - All 3 LLMs caught the fundamental flaw
2. **Golden-path examples demonstrate correct patterns** - Future tests can copy these
3. **Running tests immediately found root issue** - REPO_ROOT calculation
4. **command_runner.py infrastructure was ready** - Just never used!

### What Didn't Work ❌

1. **Assuming DATA_ROOT would work** - Real scripts don't use it
2. **Writing 146 tests before running any** - Should have validated infrastructure first
3. **Not checking actual CLI behavior** - Assumed "Created task" message existed

### Best Practices Going Forward

1. **Always run 1-2 golden-path tests first** - Validate infrastructure
2. **Check actual CLI output before writing assertions** - Read the real code
3. **Test in small batches** - Rewrite 5-10 tests, run them, fix issues, repeat
4. **Document real behaviors discovered** - Tests are also documentation
5. **Fix root issues, never change tests to pass** - User's critical requirement

---

## Estimated Timeline

- **Phase 1 (Infrastructure):** Complete ✅
- **Phase 2 (Environment Isolation):** 1 week
- **Phase 3 (Rewrite 146 tests):** 5 weeks
- **Phase 4 (Validation & Fixes):** 1 week

**Total:** 7 weeks

**Current Progress:** Week 1 of 7 (14% complete)

---

## Questions for User

1. **REPO_ROOT Override:** Approve Option A (modify CLI scripts to respect project_ROOT)?
2. **Prioritization:** Rewrite tests in order listed, or prioritize specific workflows?
3. **Test Coverage:** Are there workflows not covered in current 146 tests?
4. **Definition of Done:** Any additional validation beyond "tests execute real CLIs and validate output"?

---

## Appendix: Golden-Path Test Example

```python
def test_create_task_via_cli_success(self, test_project_dir: TestProjectDir):
    """✅ CORRECT: Execute real 'tasks/new' CLI and validate output."""
    task_id = "150-wave1-auth"

    # Execute REAL CLI command
    result = run_script(
        "tasks/new",
        ["--id", task_id, "--wave", "wave1", "--slug", "auth-implementation"],
        cwd=test_project_dir.tmp_path,
    )

    # Validate command succeeded
    assert_command_success(result)

    # Validate command output
    assert_output_contains(result, task_id)
    assert_output_contains(result, ".md")

    # Validate CLI created the expected file
    task_path = test_project_dir.project_root / "tasks" / "todo" / f"{task_id}.md"
    assert_file_exists(task_path)
    assert_file_contains(task_path, f"**Wave:** wave1")
```

**Key Pattern:**
1. Execute real CLI with `run_script()`
2. Validate exit code with `assert_command_success()`
3. Validate stdout/stderr with `assert_output_contains()`
4. Validate file system changes
5. Validate file contents

**Anti-Pattern to Avoid:**
```python
# ❌ WRONG - bypasses real CLI
task_path = test_project_dir.create_task(task_id, wave="wave1", state="todo")
```
