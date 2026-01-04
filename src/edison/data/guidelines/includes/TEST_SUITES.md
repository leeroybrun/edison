# Test Suites (Edison Development) - Include-Only File

<!-- WARNING: This file is for {{include-section:}} only. DO NOT read directly. -->

<!-- section: suite-selection -->
## Test Suite Selection (Fast vs Slow)

Edison’s tests are divided into two practical suites:

- **Fast** (`pytest -m fast`): deterministic unit tests that avoid heavy git/subprocess/E2E workflows.
- **Slow** (`pytest -m slow`): anything that uses substantial subprocess/git, integration, or E2E flows.

**Rule of thumb**:
- For tight iteration loops (RED/GREEN): run **fast**.
- Before handoff or when touching cross-cutting behavior (session/task/worktree/evidence/composition/config loading): run **slow**.

Convenience wrappers (preferred):
```bash
scripts/test-fast
scripts/test-slow
```

Both wrappers automatically use `pytest-xdist` when available (parallel mode), and fall back to single-process otherwise.
<!-- /section: suite-selection -->

<!-- section: wiring -->
## Wiring New Tests Correctly

### 1) Put heavy tests in the right place (so they auto-mark correctly)
The test harness auto-assigns markers based on test file location. Prefer these directories:
- `tests/e2e/**` and `tests/integration/**` for end-to-end/integration flows (auto-marked `slow`)
- `tests/unit/cli/**` for CLI subprocess-heavy tests (auto-marked `slow`)
- `tests/unit/**` for pure unit behavior (auto-marked `fast`)

If a test is subprocess/git-heavy but doesn’t live under a slow bucket, **explicitly add**:
```python
import pytest
pytestmark = pytest.mark.slow
```

### 2) Use the shared fixtures (avoid per-test repo bootstrapping)
For git/worktree behavior, prefer:
- `git_repo` fixture (fast template copy)
- `combined_env` fixture (project + git, both isolated)

Do not call `git init` ad-hoc inside tests; use `TestGitRepo`/fixtures so the suite stays fast and parallel-safe.
<!-- /section: wiring -->

<!-- section: parallelism -->
## Parallelism Notes (xdist)

- `scripts/test-fast` and `scripts/test-slow` run with `-n auto --dist loadfile` when `pytest-xdist` is installed.
- Tests must not write shared paths (repo root, fixed `/tmp/...` paths) without per-test isolation (`tmp_path`, per-test dirs).
<!-- /section: parallelism -->

