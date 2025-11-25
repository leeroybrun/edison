

# E2E Workflow Tests

Comprehensive end-to-end test suite for the project project management workflow.

## 📋 Overview

This test suite validates the complete workflow including:
- Session management (creation, lifecycle, state transitions)
- Task management (creation, claiming, completion, validation)
- QA workflow (validation, evidence, rounds)
- Git worktree integration (creation, isolation, merge)
- Context7 enforcement (cross-check with git diff)
- Edge cases and error handling

## 🏗️ Architecture

```
.agents/scripts/tests/e2e/
├── conftest.py                    # Pytest fixtures & configuration
├── pytest.ini                     # Pytest settings
├── helpers/                       # Test utilities
│   ├── __init__.py
│   ├── test_env.py               # TestProjectDir, TestGitRepo
│   ├── command_runner.py         # CLI execution helpers
│   ├── git_helpers.py            # Git operation wrappers
│   └── assertions.py             # Custom assertion helpers
├── fixtures/                      # Pre-built test scenarios (optional)
└── scenarios/                     # Test files
    ├── test_01_session_management.py       # Session tests (12 tests)
    ├── test_02_task_lifecycle.py           # Task tests (15 tests)
    ├── test_04_worktree_integration.py     # Worktree tests (18 tests)
    └── test_10_edge_cases.py               # Edge case tests (20 tests)
```

## 🧪 Test Helpers

### TestProjectDir

Manages isolated `.project` directory for each test:

```python
def test_example(test_project_dir: TestProjectDir):
    # Create test data
    task_id = "100-wave1-test"
    test_project_dir.create_task(task_id, state="wip")

    # Query state
    state = test_project_dir.get_task_state(task_id)
    assert state == "wip"

    # Create evidence
    test_project_dir.create_mock_evidence(task_id, round_num=1)
    test_project_dir.add_context7_evidence(task_id, "react")

    # Assertions
    test_project_dir.assert_task_in_state(task_id, "wip")
    test_project_dir.assert_evidence_exists(task_id, "command-type-check.txt")
```

### TestGitRepo

Manages isolated git repository with worktree support:

```python
def test_example(test_git_repo: TestGitRepo):
    # Create worktree
    worktree_path = test_git_repo.create_worktree("session-1")

    # Make changes
    file = worktree_path / "src" / "App.tsx"
    test_git_repo.create_test_file(file, "content")
    test_git_repo.commit_in_worktree(worktree_path, "Add App")

    # Check diff
    changed = test_git_repo.get_changed_files_in_worktree(worktree_path, "main")
    assert "src/App.tsx" in changed

    # Assertions
    test_git_repo.assert_worktree_exists(worktree_path)
    test_git_repo.assert_branch_exists("session/session-1")
```

### Combined Environment

Use both helpers together:

```python
def test_example(combined_env):
    test_project_dir, test_git_repo = combined_env

    # Create session with worktree
    worktree_path = test_git_repo.create_worktree("session-1")
    test_project_dir.create_session(
        "session-1",
        with_worktree=True,
        worktree_path=worktree_path
    )
```

## 🚀 Running Tests

### Run all tests
```bash
pytest .agents/scripts/tests/e2e/ -v
```

### Run specific test file
```bash
pytest .agents/scripts/tests/e2e/scenarios/test_01_session_management.py -v
```

### Run specific test
```bash
pytest .agents/scripts/tests/e2e/scenarios/test_01_session_management.py::test_create_basic_session -v
```

### Run by marker

```bash
# Only fast tests
pytest .agents/scripts/tests/e2e/ -m fast

# Skip slow tests
pytest .agents/scripts/tests/e2e/ -m "not slow"

# Only worktree tests
pytest .agents/scripts/tests/e2e/ -m worktree

# Only integration tests
pytest .agents/scripts/tests/e2e/ -m integration

# Only edge case tests
pytest .agents/scripts/tests/e2e/ -m edge_case
```

### Run in parallel (faster)

```bash
# Requires: pip install pytest-xdist
pytest .agents/scripts/tests/e2e/ -n auto
```

### Run with coverage

```bash
# Requires: pip install pytest-cov
pytest .agents/scripts/tests/e2e/ --cov=../../ --cov-report=html --cov-report=term

# Open coverage report
open htmlcov/index.html
```

### Run specific categories

```bash
# Session management tests
pytest .agents/scripts/tests/e2e/ -m session -v

# Task lifecycle tests
pytest .agents/scripts/tests/e2e/ -m task -v

# Git worktree tests
pytest .agents/scripts/tests/e2e/ -m worktree -v

# Context7 tests
pytest .agents/scripts/tests/e2e/ -m context7 -v

# QA workflow tests
pytest .agents/scripts/tests/e2e/ -m qa -v
```

## 📊 Test Markers

Tests are tagged with markers for easy filtering:

| Marker | Description | Example |
|--------|-------------|---------|
| `fast` | Quick tests (< 1s) | `-m fast` |
| `slow` | Slow tests (> 5s) | `-m "not slow"` |
| `requires_git` | Needs git operations | `-m requires_git` |
| `requires_pnpm` | Needs pnpm/node | `-m requires_pnpm` |
| `worktree` | Worktree functionality | `-m worktree` |
| `session` | Session management | `-m session` |
| `task` | Task lifecycle | `-m task` |
| `qa` | QA/validation | `-m qa` |
| `context7` | Context7 enforcement | `-m context7` |
| `integration` | Integration tests | `-m integration` |
| `edge_case` | Edge cases | `-m edge_case` |

## 🎯 Test Coverage

Target coverage goals:

| Component | Target | Key Areas |
|-----------|--------|-----------|
| `scripts/tasks/*` | 90% | new, claim, ready, status |
| `scripts/qa/*` | 90% | new, promote, bundle |
| `scripts/session*` | 95% | create, complete, worktree |
| `scripts/lib/*` | 90% | sessionlib, task |
| **Overall** | **90%+** | Statement coverage |

## 📝 Writing New Tests

### Test Template

```python
"""Test: Description

Test Coverage:
- Feature 1
- Feature 2
"""
from __future__ import annotations

import pytest
from helpers import TestProjectDir, TestGitRepo


@pytest.mark.fast
@pytest.mark.session  # Add relevant markers
def test_feature_name(test_project_dir: TestProjectDir):
    """Test description."""
    # Arrange: Set up test data
    session_id = "test-session"
    test_project_dir.create_session(session_id, state="wip")

    # Act: Perform action
    # ... test logic ...

    # Assert: Verify results
    test_project_dir.assert_session_exists(session_id)
```

### Best Practices

1. **Use descriptive test names**: `test_create_worktree_for_session` not `test_wt1`
2. **Add relevant markers**: Help categorize and filter tests
3. **Isolate tests**: Each test should be independent (use fixtures)
4. **Test one thing**: Keep tests focused on a single behavior
5. **Use helpers**: Leverage TestProjectDir and TestGitRepo
6. **Document**: Add docstrings explaining what's being tested

## 🔍 Key Test Scenarios

### Happy Path: Basic Session
```python
def test_basic_session_workflow(test_project_dir):
    # Create → Claim → Implement → Complete → Validate
    session_id = test_project_dir.create_session("test-1")
    task_id = test_project_dir.create_task("100-wave1-test")
    test_project_dir.claim_task(task_id, session_id)
    test_project_dir.complete_implementation(task_id)
    test_project_dir.mark_task_done(task_id)
    test_project_dir.validate_task(task_id)
```

### Happy Path: Worktree Session
```python
def test_worktree_session_full_workflow(combined_env):
    test_project_dir, test_git_repo = combined_env

    # Create session with worktree
    worktree_path = test_git_repo.create_worktree("session-1")
    test_project_dir.create_session("session-1", with_worktree=True)

    # Make changes in worktree
    file = worktree_path / "src/App.tsx"
    test_git_repo.create_test_file(file, "content")
    test_git_repo.commit_in_worktree(worktree_path, "Add App")

    # Verify git diff detection
    changed = test_git_repo.get_changed_files_in_worktree(worktree_path)
    assert "src/App.tsx" in changed
```

### Critical: Context7 Cross-Check
```python
def test_context7_cross_check_git_diff(combined_env):
    """Verify Context7 uses BOTH task metadata AND git diff."""
    test_project_dir, test_git_repo = combined_env

    # Task claims React files
    test_project_dir.create_task(
        "100-test",
        primary_files=["src/Button.tsx"]  # React
    )

    # But ACTUALLY change Zod files in worktree
    worktree_path = test_git_repo.create_worktree("session-1")
    api_file = worktree_path / "src/schema.ts"
    test_git_repo.create_test_file(
        api_file,
        'import { z } from "zod"; const schema = z.object({});'
    )
    test_git_repo.commit_in_worktree(worktree_path, "Add schema")

    # Context7 should require BOTH React AND Zod evidence
    # (Task metadata shows React, git diff shows Zod)
```

## 🐛 Debugging Tests

### Verbose output
```bash
pytest .agents/scripts/tests/e2e/ -vv
```

### Show print statements
```bash
pytest .agents/scripts/tests/e2e/ -s
```

### Drop into debugger on failure
```bash
pytest .agents/scripts/tests/e2e/ --pdb
```

### Run last failed tests
```bash
pytest .agents/scripts/tests/e2e/ --lf
```

### Show test durations
```bash
pytest .agents/scripts/tests/e2e/ --durations=10
```

## 📦 Dependencies

Required:
- `pytest` >= 7.0
- Python >= 3.11

Optional:
- `pytest-cov` - Coverage reporting
- `pytest-xdist` - Parallel execution
- `pytest-timeout` - Timeout protection

Install:
```bash
pip install pytest pytest-cov pytest-xdist pytest-timeout
```

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install pytest pytest-cov pytest-xdist

      - name: Run E2E tests
        run: |
          cd .agents/scripts/tests/e2e
          pytest -v --cov=../../ --cov-report=xml -n auto

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

## 📈 Test Metrics

Current test count: **65+ tests**

Breakdown:
- Session Management: 12 tests
- Task Lifecycle: 15 tests
- Worktree Integration: 18 tests
- Edge Cases: 20 tests

Target: **140+ tests** (see full spec for complete list)

## 🤝 Contributing

When adding new features:

1. Write tests FIRST (TDD)
2. Add tests to appropriate scenario file
3. Use relevant markers
4. Update this README if needed
5. Ensure tests pass: `pytest .agents/scripts/tests/e2e/ -v`
6. Check coverage: `pytest --cov=../../ --cov-report=term`

## 📚 Additional Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Pytest Markers](https://docs.pytest.org/en/stable/mark.html)
- [project Workflow Documentation](../../../.agents/guidelines/SESSION_WORKFLOW.md)

## 🙋 Help

For issues or questions:
1. Check test output: `pytest -vv`
2. Enable debugging: `pytest --pdb`
3. Review helper docs: See docstrings in `helpers/`
4. Check fixtures: See `conftest.py`
