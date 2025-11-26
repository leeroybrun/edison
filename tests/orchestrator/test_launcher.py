import os
import subprocess
from pathlib import Path
from typing import Dict

import pytest
import yaml

from edison.core.config.domains import OrchestratorConfig
from edison.core.orchestrator.launcher import (
    OrchestratorLauncher,
    OrchestratorNotFoundError,
)
from edison.core.session.context import SessionContext


def _write_orchestrator_config(repo_root: Path, profiles: Dict[str, Dict], default: str) -> None:
    """Helper to write orchestrator.yaml into the isolated repo."""
    config_dir = repo_root / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    data = {"orchestrators": {"default": default, "profiles": profiles}}
    (config_dir / "orchestrator.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False), encoding="utf-8"
    )


def _session_context(session_id: str, project_root: Path, worktree: Path) -> SessionContext:
    """Create a SessionContext stub with session metadata attached."""
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


def test_launcher_initialization(tmp_path: Path, isolated_project_env, monkeypatch) -> None:
    bin_dir = tmp_path / "bin"
    mock_bin = _make_mock_bin(bin_dir, "mock-launch", "#!/bin/bash\nexit 0\n")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    profiles = {
        "mock": {
            "command": mock_bin.name,
            "args": [],
            "cwd": "{session_worktree}",
            "initial_prompt": {"enabled": False},
        }
    }
    _write_orchestrator_config(tmp_path, profiles, default="mock")
    launcher = OrchestratorLauncher(
        OrchestratorConfig(repo_root=tmp_path, validate=True),
        _session_context("sess-init", tmp_path, tmp_path / "wt"),
    )
    assert launcher is not None


def test_launch_with_stdin_prompt(tmp_path: Path, isolated_project_env, monkeypatch) -> None:
    bin_dir = tmp_path / "bin"
    output_file = tmp_path / "received-stdin.txt"
    script = f"#!/bin/bash\ncat > \"{output_file}\"\n"
    mock_bin = _make_mock_bin(bin_dir, "mock-stdin", script)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    profiles = {
        "mock-stdin": {
            "command": mock_bin.name,
            "args": [],
            "cwd": "{session_worktree}",
            "env": {"OUTPUT_FILE": str(output_file)},
            "initial_prompt": {"enabled": True, "method": "stdin"},
        }
    }
    _write_orchestrator_config(tmp_path, profiles, default="mock-stdin")

    launcher = OrchestratorLauncher(
        OrchestratorConfig(repo_root=tmp_path, validate=True),
        _session_context("sess-stdin", tmp_path, tmp_path / "wt-stdin"),
    )

    prompt = "Implement feature X"
    process = launcher.launch("mock-stdin", initial_prompt=prompt)
    process.wait(timeout=5)
    assert output_file.read_text(encoding="utf-8") == prompt
    launcher.cleanup_temp_files()


def test_launch_with_file_prompt(tmp_path: Path, isolated_project_env, monkeypatch) -> None:
    bin_dir = tmp_path / "bin"
    output_file = tmp_path / "received-file.txt"
    script = (
        "#!/bin/bash\n"
        "PROMPT_FILE=\"\"\n"
        "while [[ $# -gt 0 ]]; do\n"
        "  if [[ \"$1\" == \"--prompt-file\" ]]; then\n"
        "    PROMPT_FILE=\"$2\"\n"
        "    shift 2\n"
        "  else\n"
        "    shift 1\n"
        "  fi\n"
        "done\n"
        "cat \"$PROMPT_FILE\" > \"$OUTPUT_FILE\"\n"
    )
    mock_bin = _make_mock_bin(bin_dir, "mock-file", script)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    profiles = {
        "mock-file": {
            "command": mock_bin.name,
            "args": [],
            "cwd": "{session_worktree}",
            "env": {"OUTPUT_FILE": str(output_file)},
            "initial_prompt": {"enabled": True, "method": "file", "arg_flag": "--prompt-file"},
        }
    }
    _write_orchestrator_config(tmp_path, profiles, default="mock-file")

    launcher = OrchestratorLauncher(
        OrchestratorConfig(repo_root=tmp_path, validate=True),
        _session_context("sess-file", tmp_path, tmp_path / "wt-file"),
    )

    prompt = "Persist prompt via file"
    process = launcher.launch("mock-file", initial_prompt=prompt)
    process.wait(timeout=5)
    assert output_file.read_text(encoding="utf-8") == prompt
    launcher.cleanup_temp_files()


def test_launch_with_arg_prompt(tmp_path: Path, isolated_project_env, monkeypatch) -> None:
    bin_dir = tmp_path / "bin"
    output_file = tmp_path / "received-arg.txt"
    script = (
        "#!/bin/bash\n"
        "while [[ $# -gt 0 ]]; do\n"
        "  if [[ \"$1\" == \"--prompt\" ]]; then\n"
        "    echo -n \"$2\" > \"$OUTPUT_FILE\"\n"
        "    shift 2\n"
        "  else\n"
        "    shift 1\n"
        "  fi\n"
        "done\n"
    )
    mock_bin = _make_mock_bin(bin_dir, "mock-arg", script)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    profiles = {
        "mock-arg": {
            "command": mock_bin.name,
            "args": [],
            "cwd": "{session_worktree}",
            "env": {"OUTPUT_FILE": str(output_file)},
            "initial_prompt": {"enabled": True, "method": "arg", "arg_flag": "--prompt"},
        }
    }
    _write_orchestrator_config(tmp_path, profiles, default="mock-arg")

    launcher = OrchestratorLauncher(
        OrchestratorConfig(repo_root=tmp_path, validate=True),
        _session_context("sess-arg", tmp_path, tmp_path / "wt-arg"),
    )

    prompt = "Inline arg prompt"
    process = launcher.launch("mock-arg", initial_prompt=prompt)
    process.wait(timeout=5)
    assert output_file.read_text(encoding="utf-8") == prompt
    launcher.cleanup_temp_files()


def test_launch_with_env_prompt(tmp_path: Path, isolated_project_env, monkeypatch) -> None:
    bin_dir = tmp_path / "bin"
    output_file = tmp_path / "received-env.txt"
    script = "#!/bin/bash\necho -n \"$PROMPT_TEXT\" > \"$OUTPUT_FILE\"\n"
    mock_bin = _make_mock_bin(bin_dir, "mock-env", script)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    profiles = {
        "mock-env": {
            "command": mock_bin.name,
            "args": [],
            "cwd": "{session_worktree}",
            "env": {"OUTPUT_FILE": str(output_file)},
            "initial_prompt": {"enabled": True, "method": "env", "env_var": "PROMPT_TEXT"},
        }
    }
    _write_orchestrator_config(tmp_path, profiles, default="mock-env")

    launcher = OrchestratorLauncher(
        OrchestratorConfig(repo_root=tmp_path, validate=True),
        _session_context("sess-env", tmp_path, tmp_path / "wt-env"),
    )

    prompt = "Environment prompt"
    process = launcher.launch("mock-env", initial_prompt=prompt)
    process.wait(timeout=5)
    assert output_file.read_text(encoding="utf-8") == prompt
    launcher.cleanup_temp_files()


def test_launch_missing_binary_raises_error(tmp_path: Path, isolated_project_env) -> None:
    profiles = {
        "missing": {
            "command": "definitely-not-a-real-binary-xyz",
            "args": [],
            "cwd": "{session_worktree}",
            "initial_prompt": {"enabled": False},
        }
    }
    _write_orchestrator_config(tmp_path, profiles, default="missing")

    launcher = OrchestratorLauncher(
        OrchestratorConfig(repo_root=tmp_path, validate=True),
        _session_context("sess-missing", tmp_path, tmp_path / "wt-missing"),
    )

    with pytest.raises(OrchestratorNotFoundError):
        launcher.launch("missing", initial_prompt="should fail")


def test_template_variable_expansion(tmp_path: Path, isolated_project_env) -> None:
    profiles = {
        "mock": {
            "command": "echo",
            "args": ["{session_id}", "{session_worktree}", "{project_root}", "{timestamp}", "{shortid}"],
            "cwd": "{session_worktree}",
            "initial_prompt": {"enabled": False},
        }
    }
    _write_orchestrator_config(tmp_path, profiles, default="mock")
    worktree = tmp_path / "wt-template"
    launcher = OrchestratorLauncher(
        OrchestratorConfig(repo_root=tmp_path, validate=True),
        _session_context("sess-template", tmp_path, worktree),
    )

    template = (
        "wt:{session_worktree} root:{project_root} id:{session_id} ts:{timestamp} sid:{shortid}"
    )
    expanded = launcher._expand_template_vars(template)
    assert "{" not in expanded
    assert str(worktree) in expanded
    assert "sess-template" in expanded
    assert str(tmp_path) in expanded
    assert "ts:" in expanded and "sid:" in expanded


def test_cleanup_temp_files(tmp_path: Path, isolated_project_env, monkeypatch) -> None:
    bin_dir = tmp_path / "bin"
    output_file = tmp_path / "received-cleanup.txt"
    script = (
        "#!/bin/bash\n"
        "if [[ \"$1\" == \"--prompt-file\" ]]; then\n"
        "  cat \"$2\" > \"$OUTPUT_FILE\"\n"
        "fi\n"
    )
    mock_bin = _make_mock_bin(bin_dir, "mock-cleanup", script)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")

    profiles = {
        "mock-cleanup": {
            "command": mock_bin.name,
            "args": [],
            "cwd": "{session_worktree}",
            "env": {"OUTPUT_FILE": str(output_file)},
            "initial_prompt": {"enabled": True, "method": "file", "arg_flag": "--prompt-file"},
        }
    }
    _write_orchestrator_config(tmp_path, profiles, default="mock-cleanup")

    launcher = OrchestratorLauncher(
        OrchestratorConfig(repo_root=tmp_path, validate=True),
        _session_context("sess-cleanup", tmp_path, tmp_path / "wt-cleanup"),
    )

    prompt = "Cleanup prompt"
    process = launcher.launch("mock-cleanup", initial_prompt=prompt)
    process.wait(timeout=5)

    # Ensure temp files created by launcher are removed
    launcher.cleanup_temp_files()
    remaining_temp = [p for p in getattr(launcher, "_temp_files", []) if p.exists()]
    assert remaining_temp == []
    assert output_file.read_text(encoding="utf-8") == prompt
