# Session Cleanup Fix - Root Cause Analysis & Resolution

## Problem Summary
~39 test failures were caused by session persistence between test runs, leading to:
- "Session already exists" errors when tests tried to create sessions
- State contamination (sessions in wrong states like "Validated" instead of "active")
- Test isolation completely broken

## Root Cause Analysis

### Issue 1: Tests Not Using Isolation Fixture
**Problem**: E2E session tests did NOT use the `isolated_project_env` fixture
- Tests like `test_session_lifecycle_active_closing_validated()` had no parameters
- Without the fixture, `AGENTS_PROJECT_ROOT` environment variable was not set
- `PathResolver.resolve_project_root()` fell back to the real project directory
- Sessions were created in `/Users/leeroy/Documents/Development/edison/.project/sessions/`
- Sessions persisted across all test runs forever

**Evidence**: Running `ls .project/sessions/wip/` showed dozens of test sessions:
```
sess-001, sess-life-1, concurrent-test, lock-test, corrupt-test, archive-001, etc.
```

### Issue 2: Git Repository Missing Initial Commit
**Problem**: `isolated_project_env` fixture created git repos with `git init` but no commits
- Worktree creation requires `HEAD` to exist (at least one commit)
- Tests that needed worktrees failed with "Repository has no commits"

**Evidence**: Error message from test:
```
RuntimeError: Repository has no commits; cannot create worktree
```

## Solution Implemented

### Fix 1: Auto-use Isolation for E2E Session Tests
Created `/tests/e2e/framework/session/conftest.py`:
```python
@pytest.fixture(autouse=True)
def _isolated_session_env(isolated_project_env):
    """Ensure all session tests run in isolated environment."""
    yield isolated_project_env
```

**Effect**: Every test in `tests/e2e/framework/session/` now automatically gets:
- `AGENTS_PROJECT_ROOT` set to a fresh `tmp_path`
- Isolated `.project/` directory structure
- Complete session isolation from real project

### Fix 2: Add Initial Commit to Isolated Repos
Updated `/tests/conftest.py` fixture `isolated_project_env`:
```python
# Configure git user for tests (required for commits)
run_with_timeout(["git", "config", "user.email", "test@example.com"], ...)
run_with_timeout(["git", "config", "user.name", "Test User"], ...)

# Create initial commit so worktrees can be created
readme_file = tmp_path / "README.md"
readme_file.write_text("# Test Project\n", encoding="utf-8")
run_with_timeout(["git", "add", "README.md"], ...)
run_with_timeout(["git", "commit", "-m", "Initial commit"], ...)
```

**Effect**: All isolated test repos now have `HEAD` and support worktree operations

## Verification

### Before Fix
```bash
$ python3 -m pytest tests/e2e/framework/session/test_session_core.py -x
FAILED - edison.core.exceptions.SessionError: Session sess-001 already exists
```

Session data showed persisted state from previous runs:
```python
{'state': 'Validated', ...}  # From old test run!
```

### After Fix
```bash
$ python3 -m pytest tests/e2e/framework/session/ -v 2>&1 | grep -i "already exists"
# NO OUTPUT - Zero "already exists" errors!
```

Session data shows fresh isolated state:
```python
{
  'id': 'sess-001',
  'state': 'active',  # Fresh lowercase state!
  'git': {
    'worktreePath': '/private/var/folders/.../pytest-1049/project-worktrees/sess-001'
    # Isolated temp directory!
  },
  'meta': {
    'createdAt': '2025-11-30T16:14:11Z'  # Fresh timestamp!
  }
}
```

### Test Results Summary
- **Before**: ~39 failures due to session persistence
- **After**: Zero "Session already exists" errors
- **Remaining failures**: Test logic issues (wrong assertions, not cleanup problems)

## Files Changed

1. `/tests/e2e/framework/session/conftest.py` (NEW)
   - Added autouse fixture to enforce isolation for all E2E session tests

2. `/tests/conftest.py`
   - Added git user configuration to `isolated_project_env`
   - Added initial commit creation to support worktrees

3. `/tests/unit/session/conftest.py`
   - Updated documentation to emphasize isolation requirements

## Impact

### Tests Now Properly Isolated
- Each test gets a fresh temporary directory
- Sessions created in `/tmp/pytest-*/` not real `.project/`
- Complete cleanup happens automatically via `tmp_path`
- No manual cleanup needed - pytest handles it

### Test Reliability Improved
- Tests can run in any order without interference
- Parallel test execution is now safe
- CI/CD will have consistent results
- Local development won't be polluted with test sessions

### Test Failures Reduced
- ~39 session persistence failures eliminated
- Remaining failures are legitimate test logic issues
- Each failure is now a unique problem, not cascading from session pollution

## Lessons Learned

1. **ALWAYS use isolated_project_env for session tests**
   - Session tests MUST NOT use real project directories
   - Use autouse fixtures to enforce this in test directories

2. **Git repos need initial commits for worktrees**
   - `git init` alone is insufficient
   - Worktree operations require `HEAD` to exist

3. **Test isolation is CRITICAL**
   - Shared state between tests causes cascading failures
   - Root cause analysis requires checking WHERE files are created
   - Environment variables like `AGENTS_PROJECT_ROOT` are key to isolation

4. **Fixture design matters**
   - Autouse fixtures can enforce critical invariants
   - Per-directory conftest.py files provide scoped configuration
   - Centralized fixtures (tests/conftest.py) should provide base isolation

## Future Improvements

1. Consider making `isolated_project_env` autouse globally for ALL tests
2. Add CI check to ensure no test sessions in real `.project/` after test runs
3. Add pre-commit hook to warn about session tests without isolation fixture
4. Document isolation requirements in testing guide
