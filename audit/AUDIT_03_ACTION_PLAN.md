# AUDIT 03: Action Plan for Mock Violations
## Detailed Remediation Steps

**Target:** 100% mock-free compliance (Rule #2)  
**Current Status:** 96.8% compliant (8 files with violations)  
**Target Date:** [To be assigned]  

---

## PRIORITY 1: HIGH SEVERITY VIOLATIONS (1 file)

### 1. tests/cli/test_compose_all_paths.py

**Severity:** 🔴 HIGH - Mocking core business logic  
**Effort:** 2-4 hours  
**Lines:** 2, 9-21, 28-37, 59-63  

#### Current Code (VIOLATES Rule #2):
```python
from unittest.mock import MagicMock, patch

@pytest.fixture
def mock_args():
    args = MagicMock()
    args.repo_root = None
    args.agents = False
    # ... more mock attributes
    return args

def test_compose_all_uses_resolved_config_dir_for_validators(tmp_path, mock_args):
    with patch("edison.core.paths.resolve_project_root", return_value=repo_root), \
         patch("edison.core.composition.CompositionEngine") as MockEngine:
        engine = MockEngine.return_value
        val_result = MagicMock()
        val_result.text = "validator content"
```

#### Recommended Solution (COMPLIANT):
```python
import argparse
from pathlib import Path
from edison.cli.compose.all import main
from edison.core.composition import CompositionEngine

@pytest.fixture
def real_args():
    """Create real argparse Namespace for testing."""
    args = argparse.Namespace()
    args.repo_root = None
    args.agents = False
    args.validators = False
    args.orchestrator = False
    args.guidelines = False
    args.dry_run = False
    args.json = False
    args.claude = False
    args.cursor = False
    args.zen = False
    args.platforms = None
    return args

def test_compose_all_uses_resolved_config_dir_for_validators(tmp_path, real_args):
    """Test validators use resolved config dir with REAL CompositionEngine."""
    # Setup real project structure
    repo_root = tmp_path
    config_dir = repo_root / ".edison" / "config"
    config_dir.mkdir(parents=True)
    
    # Create real config files that CompositionEngine needs
    (config_dir / "validators.yml").write_text("""
validators:
  test-val:
    name: Test Validator
    description: Test validator
""")
    
    # Setup real output directory
    output_dir = config_dir / "_generated" / "validators"
    output_dir.mkdir(parents=True)
    
    # Enable validators flag
    real_args.validators = True
    real_args.repo_root = repo_root
    
    # Execute with REAL engine
    main(real_args)
    
    # Assert REAL behavior - check that files were created
    expected_file = output_dir / "test-val.md"
    assert expected_file.exists(), f"Validator should be generated at {expected_file}"
    
    # Verify content was actually composed (not mocked)
    content = expected_file.read_text()
    assert len(content) > 0, "Validator should have real content"
    assert "Test Validator" in content or "test-val" in content
```

#### Steps to Fix:
1. ✅ Replace `MagicMock()` with `argparse.Namespace()`
2. ✅ Replace `patch("resolve_project_root")` with real tmp_path setup
3. ✅ Replace `patch("CompositionEngine")` with real CompositionEngine
4. ✅ Create real config files in tmp_path
5. ✅ Test real composition behavior and file creation
6. ✅ Remove all unittest.mock imports
7. ✅ Run test to verify it passes with real implementation

#### Verification:
```bash
cd /Users/leeroy/Documents/Development/edison
python -m pytest tests/cli/test_compose_all_paths.py -v
```

---

## PRIORITY 2: MEDIUM SEVERITY VIOLATIONS (3 files)

### 2. tests/unit/utils/test_cli_output.py

**Severity:** 🟡 MEDIUM - Mocking stdlib I/O  
**Effort:** 3-4 hours  
**Lines:** 16, 142-220  

#### Current Code (VIOLATES Rule #2):
```python
from unittest.mock import patch

def test_confirm_returns_true_for_yes() -> None:
    with patch("builtins.input", return_value="yes"):
        assert confirm("Continue?") is True

def test_error_prints_to_stderr() -> None:
    with patch("sys.stderr", new_callable=StringIO) as mock_stderr:
        exit_code = error("Something failed")
        output = mock_stderr.getvalue()
```

#### Recommended Solution (COMPLIANT):
```python
import io
import sys
from contextlib import redirect_stdin, redirect_stderr

def test_confirm_returns_true_for_yes(monkeypatch) -> None:
    """Test confirm with real input stream (no mocks)."""
    # Use real StringIO for input (not a mock)
    fake_input = io.StringIO("yes\n")
    monkeypatch.setattr('sys.stdin', fake_input)
    
    assert confirm("Continue?") is True

def test_error_prints_to_stderr() -> None:
    """Test error output with real stderr redirection (no mocks)."""
    # Use real StringIO capture (not a mock)
    captured_stderr = io.StringIO()
    
    with redirect_stderr(captured_stderr):
        exit_code = error("Something failed")
    
    output = captured_stderr.getvalue()
    assert "Something failed" in output
    assert "[ERR]" in output
    assert exit_code == 1
```

#### Alternative Solution (Even Better):
```python
def test_confirm_returns_true_for_yes(capsys) -> None:
    """Test confirm with pytest's capsys fixture."""
    # Pytest capsys captures real stdout/stderr
    import io
    import sys
    
    # Redirect stdin to provide input
    original_stdin = sys.stdin
    sys.stdin = io.StringIO("yes\n")
    
    try:
        result = confirm("Continue?")
    finally:
        sys.stdin = original_stdin
    
    assert result is True
```

#### Steps to Fix:
1. ✅ Replace `patch("builtins.input")` with `monkeypatch.setattr('sys.stdin', StringIO(...))`
2. ✅ Replace `patch("sys.stderr")` with `redirect_stderr(StringIO())`
3. ✅ Replace `patch("edison.core.utils.cli_output._cfg")` with real config setup
4. ✅ Remove all unittest.mock imports
5. ✅ Update all 16 test functions
6. ✅ Run tests to verify

#### Verification:
```bash
python -m pytest tests/unit/utils/test_cli_output.py -v
```

---

### 3. tests/e2e/framework/test_cli_workflow.py

**Severity:** 🟡 MEDIUM - Mocking process detection  
**Effort:** 2-3 hours  
**Lines:** 15, 36-49  

#### Current Code (VIOLATES Rule #2):
```python
from unittest import mock

class DefaultOwnerTests(unittest.TestCase):
    def test_prefers_highest_llm_process_in_chain(self) -> None:
        chain = [(3210, "claude-helper"), (4321, "claude"), (1001, "zsh")]
        with mock.patch.object(task, "_calling_process_chain", return_value=chain):
            owner = task.default_owner()
        self.assertEqual(owner, "claude-pid-4321")
```

#### Recommended Solution (COMPLIANT):
```python
# Refactor task module to accept injectable process provider

# In task.py (add dependency injection):
def default_owner(process_provider=None):
    """Get default owner from process chain.
    
    Args:
        process_provider: Optional callable that returns process chain.
                         Defaults to _calling_process_chain.
    """
    if process_provider is None:
        process_provider = _calling_process_chain
    
    chain = process_provider()
    # ... rest of logic

# In test (use real dependency injection):
def test_prefers_highest_llm_process_in_chain(self) -> None:
    """Test with real dependency injection (no mocks)."""
    # Real function that returns test data
    def test_process_provider():
        return [(3210, "claude-helper"), (4321, "claude"), (1001, "zsh")]
    
    # Test with real dependency injection
    owner = task.default_owner(process_provider=test_process_provider)
    
    self.assertEqual(owner, "claude-pid-4321")
```

#### Alternative Solution (Test with Real Process):
```python
import os
import psutil

def test_prefers_highest_llm_process_in_chain(self) -> None:
    """Test with real process chain."""
    # Get actual process chain
    owner = task.default_owner()
    
    # Verify it returns expected format (process-based testing)
    if owner:  # Only if we have a real process chain
        assert owner.startswith("claude-pid-") or owner.startswith("cursor-pid-")
    else:
        # No process chain available - skip or use real subprocess
        pytest.skip("No LLM process chain available in test environment")
```

#### Steps to Fix:
1. ✅ Refactor `task.default_owner()` to accept optional process_provider parameter
2. ✅ Update tests to use dependency injection instead of mocks
3. ✅ Remove unittest.mock imports
4. ✅ Run tests to verify

#### Verification:
```bash
python -m pytest tests/e2e/framework/test_cli_workflow.py::DefaultOwnerTests -v
```

---

### 4. tests/session/test_session_config_paths.py

**Severity:** 🟡 MEDIUM - Mocking path resolution  
**Effort:** 1-2 hours  
**Lines:** 45, 71-72  

#### Current Code (VIOLATES Rule #2):
```python
def test_manifest_path_respects_project_config_dir(self, tmp_path, monkeypatch):
    monkeypatch.setattr("edison.core.paths.resolver.PathResolver.resolve_project_root", 
                       lambda: repo_root)
    monkeypatch.setenv("EDISON_paths__project_config_dir", str(custom_config_dir))
```

#### Recommended Solution (COMPLIANT):
```python
import os

def test_manifest_path_respects_project_config_dir(self, tmp_path):
    """Test with real environment setup (no mocks)."""
    repo_root = tmp_path
    edison_dir = repo_root / ".edison"
    edison_dir.mkdir()
    
    # Create real manifest
    manifest = {"worktrees": {"branchPrefix": "edison-prefix/"}}
    (edison_dir / "manifest.json").write_text(json.dumps(manifest))
    
    # Use real environment and real SessionConfig
    # Change to repo_root directory so path resolution works naturally
    original_cwd = os.getcwd()
    try:
        os.chdir(repo_root)
        
        # Real SessionConfig with real path resolution
        config = SessionConfig(repo_root=repo_root)
        wt_config = config.get_worktree_config()
        
        assert wt_config["branchPrefix"] == "edison-prefix/"
    finally:
        os.chdir(original_cwd)

def test_manifest_path_respects_env_var_override(self, tmp_path):
    """Test with real environment variables (no mocks)."""
    repo_root = tmp_path
    custom_config_dir = repo_root / ".custom-config"
    custom_config_dir.mkdir()
    
    # Create real manifest
    manifest = {"worktrees": {"branchPrefix": "custom-prefix/"}}
    (custom_config_dir / "manifest.json").write_text(json.dumps(manifest))
    
    # Set REAL environment variable
    original_env = os.environ.get("EDISON_paths__project_config_dir")
    try:
        os.environ["EDISON_paths__project_config_dir"] = str(custom_config_dir)
        
        # Real SessionConfig reads real env var
        config = SessionConfig(repo_root=repo_root)
        wt_config = config.get_worktree_config()
        
        assert wt_config["branchPrefix"] == "custom-prefix/"
    finally:
        # Restore environment
        if original_env is not None:
            os.environ["EDISON_paths__project_config_dir"] = original_env
        else:
            os.environ.pop("EDISON_paths__project_config_dir", None)
```

#### Steps to Fix:
1. ✅ Replace `monkeypatch.setattr` with real directory setup and os.chdir()
2. ✅ Replace `monkeypatch.setenv` with real os.environ manipulation
3. ✅ Use proper cleanup (try/finally)
4. ✅ Remove monkeypatch usage
5. ✅ Run tests to verify

#### Verification:
```bash
python -m pytest tests/session/test_session_config_paths.py -v
```

---

## PRIORITY 3: LOW SEVERITY (Acceptable Edge Cases) (4 files)

### 5. tests/composition/test_settings.py (Line 130)

**Severity:** 🟢 LOW - Testing integration point  
**Current:** Uses monkeypatch for HookComposer  
**Recommendation:** OPTIONAL - Can fix for 100% compliance or accept as edge case  
**Effort:** 1 hour  

**If fixing:**
```python
# Instead of mocking HookComposer, use real one with test config
from edison.core.ide.hooks import HookComposer

def test_compose_with_hooks_section(tmp_path: Path) -> None:
    # Setup real hook config
    hooks_dir = tmp_path / ".edison" / "core" / "config"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "hooks.yml").write_text("""
hooks:
  PreToolUse:
    - echo from hook
""")
    
    composer = SettingsComposer(
        config={"hooks": {"enabled": True}}, 
        repo_root=tmp_path
    )
    settings = composer.compose_settings()
    
    # Test real hook composition
    assert settings["hooks"]["PreToolUse"] == ["echo from hook"]
```

### 6. tests/unit/adapters/test_schemas.py (Line 254)

**Severity:** 🟢 LOW - Testing library absence  
**Current:** Mocks jsonschema as None to test fallback  
**Recommendation:** ACCEPTABLE - Testing import error scenarios is valid  
**Action:** NO CHANGE REQUIRED  

### 7-8. tests/e2e/framework/test_tdd_enforcement_ready.py & tests/helpers/test_env.py

**Status:** ✅ ALREADY COMPLIANT - No mocks detected  
**Action:** NONE REQUIRED  

---

## IMPLEMENTATION TIMELINE

### Phase 1: HIGH Severity (Week 1)
- [ ] Day 1-2: Fix test_compose_all_paths.py
- [ ] Day 2: Run full test suite to ensure no regressions
- [ ] Day 2: Document changes

### Phase 2: MEDIUM Severity (Week 1-2)
- [ ] Day 3: Fix test_cli_output.py (largest file)
- [ ] Day 4: Fix test_cli_workflow.py
- [ ] Day 4: Fix test_session_config_paths.py
- [ ] Day 5: Run full test suite
- [ ] Day 5: Document changes

### Phase 3: LOW Severity (Optional - Week 2)
- [ ] If pursuing 100%: Fix test_settings.py
- [ ] Final verification

### Phase 4: Verification & Documentation (Week 2)
- [ ] Run complete test suite
- [ ] Update AUDIT_03 report with results
- [ ] Document patterns for future tests
- [ ] Create PR with all changes

---

## SUCCESS CRITERIA

### Must Have (Required):
- ✅ Zero HIGH severity mock violations
- ✅ Zero MEDIUM severity mock violations
- ✅ All affected tests pass
- ✅ No regressions in other tests

### Nice to Have (Optional):
- ✅ Zero LOW severity mock violations (100% compliance)
- ✅ Documentation of testing patterns
- ✅ Reusable test fixtures for common patterns

---

## ROLLBACK PLAN

If fixes cause issues:
1. Each file has isolated changes - can revert individually
2. Keep original test files as `.bak` during development
3. Git branch for all mock removal work
4. Can merge incrementally (file by file) if needed

---

## NOTES FOR IMPLEMENTER

### Key Principles:
1. **Use tmp_path for isolation** - pytest provides this fixture
2. **Use real file I/O** - create actual files in tmp_path
3. **Use dependency injection** - pass test data as parameters
4. **Use monkeypatch for env vars** - acceptable for environment setup
5. **Use StringIO for I/O** - real stream redirection, not mocks

### Common Patterns:

#### Pattern 1: Replace MagicMock with real objects
```python
# BEFORE (mock)
mock_obj = MagicMock()
mock_obj.attribute = "value"

# AFTER (real)
from types import SimpleNamespace
real_obj = SimpleNamespace(attribute="value")
```

#### Pattern 2: Replace patch with real file setup
```python
# BEFORE (mock)
with patch("module.function", return_value="result"):
    result = code_under_test()

# AFTER (real)
# Setup real files/config that function reads
(tmp_path / "config.yml").write_text("key: value")
result = code_under_test()  # Uses real file
```

#### Pattern 3: Replace input mock with StringIO
```python
# BEFORE (mock)
with patch("builtins.input", return_value="yes"):
    result = prompt_user()

# AFTER (real)
import sys
import io
sys.stdin = io.StringIO("yes\n")
result = prompt_user()  # Reads from real stream
```

---

## TRACKING

### Progress Checklist

- [ ] HIGH: test_compose_all_paths.py
- [ ] MEDIUM: test_cli_output.py
- [ ] MEDIUM: test_cli_workflow.py
- [ ] MEDIUM: test_session_config_paths.py
- [ ] LOW: test_settings.py (optional)
- [ ] Verification: Full test suite passes
- [ ] Documentation: Update AUDIT_03 report
- [ ] Review: Code review completed
- [ ] Merge: Changes merged to main

---

**Action Plan Created:** 2025-11-26  
**Owner:** [To be assigned]  
**Status:** 📋 READY FOR IMPLEMENTATION  

