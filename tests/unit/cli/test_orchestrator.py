import os
from pathlib import Path

from edison.core.config.cache import clear_all_caches
from edison.core.config.domains import OrchestratorConfig
from edison.core.orchestrator import OrchestratorLauncher
from edison.core.session.core.context import SessionContext
from tests.helpers.io_utils import write_orchestrator_config


def _session_context(session_id: str, project_root: Path, worktree: Path) -> SessionContext:
    """Create a SessionContext with session metadata attached."""
    worktree.mkdir(parents=True, exist_ok=True)
    ctx = SessionContext()
    ctx.session_id = session_id  # type: ignore[attr-defined]
    ctx.session_worktree = worktree  # type: ignore[attr-defined]
    ctx.project_root = project_root  # type: ignore[attr-defined]
    return ctx


def _make_mock_bin(bin_dir: Path, name: str, content: str) -> Path:
    """Create an executable script for testing."""
    path = bin_dir / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)
    return path


def test_launcher_log_path_mkdir(tmp_path: Path, isolated_project_env: Path, monkeypatch) -> None:
    """Test that launcher creates log directory and file when launching."""
    bin_dir = tmp_path / "bin"

    # Create a simple executable that exits immediately
    script = "#!/bin/bash\nexit 0\n"
    mock_bin = _make_mock_bin(bin_dir, "test-logger", script)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    # Configure orchestrator profile
    profiles = {
        "test-profile": {
            "command": mock_bin.name,
            "args": ["hello"],
            "cwd": "custom_cwd",
            "initial_prompt": {"enabled": False},
        }
    }
    write_orchestrator_config(tmp_path, profiles, default="test-profile")

    # Clear cache to ensure fresh config load
    clear_all_caches()

    # Create launcher with real config (validate=False to avoid schema requirement)
    config = OrchestratorConfig(repo_root=tmp_path, validate=False)
    context = _session_context("sess-123", tmp_path, tmp_path / "wt-logtest")
    launcher = OrchestratorLauncher(config, context)

    # Set up log path in directory that doesn't exist yet
    log_path = tmp_path / "logs" / "orch.log"

    # Ensure log dir doesn't exist before launch
    assert not log_path.parent.exists()

    # Launch process with log path
    process = launcher.launch("test-profile", log_path=log_path)
    process.wait(timeout=5)

    # Verify that log directory and file were created
    assert log_path.parent.exists()
    assert log_path.exists()

    # Verify log file has content
    log_content = log_path.read_text(encoding="utf-8")
    assert "[launch]" in log_content
    assert "profile=test-profile" in log_content


def test_launcher_cwd_mkdir(tmp_path: Path, isolated_project_env: Path, monkeypatch) -> None:
    """Test that launcher creates cwd directory when specified in profile."""
    bin_dir = tmp_path / "bin"

    # Create a simple executable that exits immediately
    script = "#!/bin/bash\nexit 0\n"
    mock_bin = _make_mock_bin(bin_dir, "test-cwd", script)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    # Configure orchestrator profile with custom cwd
    profiles = {
        "test-profile": {
            "command": mock_bin.name,
            "args": ["hello"],
            "cwd": "custom_cwd",  # Relative path that doesn't exist yet
            "initial_prompt": {"enabled": False},
        }
    }
    write_orchestrator_config(tmp_path, profiles, default="test-profile")

    # Clear cache to ensure fresh config load
    clear_all_caches()

    # Create launcher with real config (validate=False to avoid schema requirement)
    config = OrchestratorConfig(repo_root=tmp_path, validate=False)
    context = _session_context("sess-123", tmp_path, tmp_path / "wt-cwdtest")
    launcher = OrchestratorLauncher(config, context)

    # Resolve expected cwd path (relative to project_root)
    cwd_path = tmp_path / "custom_cwd"

    # Ensure cwd doesn't exist before launch
    assert not cwd_path.exists()

    # Launch process
    process = launcher.launch("test-profile")
    process.wait(timeout=5)

    # Verify that cwd directory was created
    assert cwd_path.exists()
    assert cwd_path.is_dir()
