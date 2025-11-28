"""Integration tests for SessionAutoStart and CLI start command.

All tests run against real filesystem + git operations (no mocks).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from edison.core.session.manager import SessionManager
from edison.core.session.id import validate_session_id
from edison.core.session.repository import SessionRepository
from edison.core.session import worktree
from edison.core.session.naming import reset_session_naming_counter
from edison.core.config.domains import OrchestratorConfig
from edison.core.utils.subprocess import run_with_timeout
from edison.core.utils.process.inspector import infer_session_id
from tests.helpers.timeouts import wait_for_file, medium_sleep


# Import target under test (implementation added in this task)
from edison.core.session.autostart import SessionAutoStart, SessionAutoStartError


class AutoStartEnv:
    """Helper to bootstrap isolated project + config for auto-start tests."""

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root = root
        self.monkeypatch = monkeypatch
        self.monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(self.root))
        self.monkeypatch.setenv("PROJECT_NAME", "autostart")
        self.monkeypatch.chdir(self.root)

        # Minimal project layout
        for state in [
            "wip",
            "active",
            "done",
            "validated",
            "closing",
            "recovery",
            "archived",
        ]:
            (self.root / ".project" / "sessions" / state).mkdir(parents=True, exist_ok=True)

        # Initialize git repo with initial commit
        run_with_timeout(["git", "init", "-b", "main"], cwd=self.root, check=True)
        run_with_timeout(["git", "config", "user.email", "test@example.com"], cwd=self.root, check=True)
        run_with_timeout(["git", "config", "user.name", "Test User"], cwd=self.root, check=True)
        (self.root / "README.md").write_text("Autostart fixture\n", encoding="utf-8")
        run_with_timeout(["git", "add", "README.md"], cwd=self.root, check=True)
        run_with_timeout(["git", "commit", "-m", "init"], cwd=self.root, check=True)

        self.config_dir = self.root / ".edison" / "core" / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.schemas_dir = self.root / ".edison" / "core" / "schemas"
        self.schemas_dir.mkdir(parents=True, exist_ok=True)

        # Create guides directory and START.SESSION.md for autostart tests
        guides_dir = self.root / ".edison" / "core" / "guides"
        guides_dir.mkdir(parents=True, exist_ok=True)

        # Copy START_NEW_SESSION.md as START.SESSION.md (required by orchestrator.yaml)
        from edison.data import get_data_path
        start_session_src = get_data_path("start", "START_NEW_SESSION.md")
        start_session_dst = guides_dir / "START.SESSION.md"

        if start_session_src.exists():
            start_session_dst.write_text(start_session_src.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            # Fallback: minimal session start template
            start_session_dst.write_text(
                "# Start Session\n\n"
                "## Session Initialization\n\n"
                "Run the session start command:\n"
                "```bash\n"
                "edison session start\n"
                "```\n\n"
                "## Begin Work\n\n"
                "1. Claim task\n"
                "2. Implement following TDD\n"
                "3. Mark ready\n"
                "4. Run validators\n"
                "5. Complete task\n",
                encoding="utf-8",
            )

    # --- Config + script helpers -------------------------------------------------
    def write_defaults(self, *, base_directory: Path | None = None, worktrees_enabled: bool = True) -> None:
        base_dir = base_directory or (self.root / "worktrees")
        defaults = {
            "edison": {"version": "1.0.0"},
            "worktrees": {
                "enabled": worktrees_enabled,
                "baseBranch": "main",
                "baseDirectory": str(base_dir),
                "archiveDirectory": str(base_dir.parent / "_archived"),
                "branchPrefix": "session/",
                "installDeps": False,
            },
            "paths": {"project_config_dir": ".edison"},
            "file_locking": {
                "timeout_seconds": 10.0,
                "poll_interval_seconds": 0.1,
                "fail_open": False,
            },
            "timeouts": {
                "git_operations_seconds": 10,
                "db_operations_seconds": 5,
                "json_io_lock_seconds": 5
            }
        }
        (self.config_dir / "defaults.yaml").write_text(yaml.safe_dump(defaults), encoding="utf-8")

    def write_session_config(self, *, naming_strategy: str = "edison") -> None:
        session_cfg = {
            "session": {
                "paths": {
                    "root": ".project/sessions",
                    "archive": ".project/archive",
                    "tx": ".project/sessions/_tx",
                },
                "validation": {"idRegex": r"^[a-zA-Z0-9_-]+$", "maxLength": 64},
                "defaults": {"initialState": "active"},
                "lookupOrder": ["wip", "active", "done", "validated", "closing"],
                "naming": {"strategy": naming_strategy, "ensure_unique": True, "max_length": 64},
                "worktree": {
                    "timeouts": {
                        "health_check": 3,
                        "fetch": 10,
                        "checkout": 10,
                        "worktree_add": 10,
                        "clone": 15,
                        "install": 15,
                    }
                },
            }
        }
        (self.config_dir / "session.yaml").write_text(yaml.safe_dump(session_cfg), encoding="utf-8")

    def write_orchestrator_config(self, profiles: dict, default: str) -> None:
        payload = {"orchestrators": {"default": default, "profiles": profiles}}
        (self.config_dir / "orchestrator.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")

    def make_orchestrator_script(self, name: str, *, keep_alive: bool = False) -> tuple[Path, Path]:
        script = self.root / "bin" / name
        script.parent.mkdir(parents=True, exist_ok=True)
        log = self.root / f"{name}.log"
        content = dedent(
            f"""#!/usr/bin/env bash
            set -euo pipefail
            LOG={log!s}
            PROMPT=""
            if [ ! -t 0 ]; then
              PROMPT="$(cat || true)"
            fi
            echo "pid=$$" >> "$LOG"
            echo "args:$*" >> "$LOG"
            echo "prompt:${{PROMPT}}" >> "$LOG"
            if [ "${{KEEP_ALIVE:-0}}" = "1" ]; then
              sleep 5
            fi
            """
        ).strip() + "\n"
        script.write_text(content, encoding="utf-8")
        script.chmod(0o755)
        return script, log

    def reload_configs(self) -> None:
        """Reset module-level SessionConfig singletons to this repo root."""
        from edison.core.session import manager as session_manager
        from edison.core.config.domains import SessionConfig
        from edison.core.session._config import reset_config_cache
        
        # Reset config cache to pick up new project root
        reset_config_cache()
        
        # Create new configs for this test root
        new_config = SessionConfig(repo_root=self.root)
        session_manager._CONFIG = new_config
        session_manager._WT_CFG = new_config.get_worktree_config()

    def build_autostart(self) -> SessionAutoStart:
        self.reload_configs()
        mgr = SessionManager(project_root=self.root)
        orch_cfg = OrchestratorConfig(repo_root=self.root)
        return SessionAutoStart(mgr, orch_cfg)


@pytest.fixture(autouse=True)
def reset_naming_counter():
    """Reset session naming counter before and after each test.

    This fixture prevents global state mutation from affecting other tests.
    """
    reset_session_naming_counter()
    yield
    reset_session_naming_counter()


@pytest.fixture
def autostart_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AutoStartEnv:
    env = AutoStartEnv(tmp_path, monkeypatch)
    env.write_defaults()
    env.write_session_config()
    return env


# --- Tests ---------------------------------------------------------------


def test_autostart_creates_session_metadata(autostart_env: AutoStartEnv) -> None:
    script, log = autostart_env.make_orchestrator_script("mock")
    profiles = {
        "mock": {
            "command": str(script),
            "cwd": "{session_worktree}",
            "initial_prompt": {"enabled": False},
        }
    }
    autostart_env.write_orchestrator_config(profiles, default="mock")
    autostart = autostart_env.build_autostart()

    result = autostart.start(process="TASK-123", orchestrator_profile="mock")

    session = SessionManager(project_root=autostart_env.root).get_session(result["session_id"])
    assert session["meta"].get("autoStarted") is True
    assert session["meta"].get("orchestratorProfile") == "mock"
    assert session["meta"].get("process") == "TASK-123"


def test_autostart_creates_worktree(autostart_env: AutoStartEnv) -> None:
    script, _ = autostart_env.make_orchestrator_script("mock")
    autostart_env.write_orchestrator_config(
        {
            "mock": {
                "command": str(script),
                "cwd": "{session_worktree}",
                "initial_prompt": {"enabled": False},
            }
        },
        default="mock",
    )
    autostart = autostart_env.build_autostart()

    result = autostart.start(process="TASK-123", orchestrator_profile="mock")

    worktree_path = Path(result["worktree_path"])
    assert worktree_path.exists()
    assert (worktree_path / ".git").exists()


def test_autostart_launches_orchestrator(autostart_env: AutoStartEnv) -> None:
    script, log = autostart_env.make_orchestrator_script("mock")
    autostart_env.write_orchestrator_config(
        {
            "mock": {
                "command": str(script),
                "cwd": "{session_worktree}",
                "initial_prompt": {"enabled": False},
            }
        },
        default="mock",
    )
    autostart = autostart_env.build_autostart()

    result = autostart.start(process="TASK-123", orchestrator_profile="mock")

    assert result["orchestrator_pid"] > 0
    assert wait_for_file(log)
    assert "pid=" in log.read_text()


def test_autostart_with_initial_prompt(autostart_env: AutoStartEnv, tmp_path: Path) -> None:
    script, log = autostart_env.make_orchestrator_script("mock")
    autostart_env.write_orchestrator_config(
        {
            "mock": {
                "command": str(script),
                "cwd": "{session_worktree}",
                "initial_prompt": {"enabled": True, "method": "stdin"},
            }
        },
        default="mock",
    )
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("HELLO WORLD", encoding="utf-8")
    autostart = autostart_env.build_autostart()

    autostart.start(
        process="TASK-123",
        orchestrator_profile="mock",
        initial_prompt_path=prompt_file,
    )

    assert wait_for_file(log)
    log_text = log.read_text()
    assert "prompt:HELLO WORLD" in log_text


def test_autostart_with_detach(autostart_env: AutoStartEnv) -> None:
    script, log = autostart_env.make_orchestrator_script("mock")
    profiles = {
        "mock": {
            "command": str(script),
            "cwd": "{session_worktree}",
            "env": {"KEEP_ALIVE": "1"},
            "initial_prompt": {"enabled": False},
        }
    }
    autostart_env.write_orchestrator_config(profiles, default="mock")
    autostart = autostart_env.build_autostart()

    result = autostart.start(process="TASK-DETACH", orchestrator_profile="mock", detach=True)

    assert result["orchestrator_pid"] is None
    medium_sleep()
    assert wait_for_file(log)


def test_autostart_with_no_worktree(autostart_env: AutoStartEnv) -> None:
    script, _ = autostart_env.make_orchestrator_script("mock")
    autostart_env.write_orchestrator_config(
        {
            "mock": {
                "command": str(script),
                "initial_prompt": {"enabled": False},
            }
        },
        default="mock",
    )
    autostart = autostart_env.build_autostart()

    result = autostart.start(process="TASK-123", orchestrator_profile="mock", no_worktree=True)

    assert result["worktree_path"] is None
    session = SessionManager(project_root=autostart_env.root).get_session(result["session_id"])
    git_meta = session.get("git", {})
    assert git_meta.get("worktreePath") in {None, ""}


def test_autostart_rollback_on_worktree_failure(autostart_env: AutoStartEnv) -> None:
    blocker = autostart_env.root / "blocked-worktrees"
    blocker.write_text("not-a-dir", encoding="utf-8")
    autostart_env.write_defaults(base_directory=blocker, worktrees_enabled=True)
    autostart_env.write_session_config()
    script, _ = autostart_env.make_orchestrator_script("mock")
    autostart_env.write_orchestrator_config(
        {"mock": {"command": str(script), "initial_prompt": {"enabled": False}}},
        default="mock",
    )
    autostart = autostart_env.build_autostart()

    with pytest.raises(SessionAutoStartError):
        autostart.start(process="FAIL-WT", orchestrator_profile="mock")

    session_jsons = list((autostart_env.root / ".project" / "sessions").rglob("session.json"))
    assert not session_jsons


def test_autostart_rollback_on_orchestrator_failure(autostart_env: AutoStartEnv) -> None:
    missing_cmd = autostart_env.root / "bin" / "missing-binary"
    autostart_env.write_orchestrator_config(
        {"missing": {"command": str(missing_cmd), "initial_prompt": {"enabled": False}}},
        default="missing",
    )
    autostart = autostart_env.build_autostart()

    with pytest.raises(SessionAutoStartError):
        autostart.start(process="FAIL-ORCH")

    sessions = list((autostart_env.root / ".project" / "sessions").rglob("session.json"))
    assert not sessions
    wt_root = autostart_env.root / "worktrees"
    assert not any(wt_root.glob("*"))


def test_autostart_uses_pid_based_naming(autostart_env: AutoStartEnv) -> None:
    # Note: reset_session_naming_counter is now called by autouse fixture
    autostart_env.write_session_config(naming_strategy="owner")
    script, _ = autostart_env.make_orchestrator_script("claude")
    autostart_env.write_orchestrator_config(
        {"claude": {"command": str(script), "initial_prompt": {"enabled": False}}},
        default="claude",
    )
    autostart = autostart_env.build_autostart()

    result = autostart.start(process="TASK-123", orchestrator_profile="claude")

    assert result["session_id"] == infer_session_id()


def test_autostart_uses_config_default_orchestrator(autostart_env: AutoStartEnv) -> None:
    script_default, log_default = autostart_env.make_orchestrator_script("default")
    script_other, _ = autostart_env.make_orchestrator_script("other")
    profiles = {
        "default": {"command": str(script_default), "initial_prompt": {"enabled": False}},
        "other": {"command": str(script_other), "initial_prompt": {"enabled": False}},
    }
    autostart_env.write_orchestrator_config(profiles, default="default")
    autostart = autostart_env.build_autostart()

    autostart.start(process="TASK-123")

    assert wait_for_file(log_default)
    assert "pid=" in log_default.read_text()


def test_autostart_override_orchestrator(autostart_env: AutoStartEnv) -> None:
    script_default, log_default = autostart_env.make_orchestrator_script("default")
    script_override, log_override = autostart_env.make_orchestrator_script("override")
    profiles = {
        "default": {"command": str(script_default), "initial_prompt": {"enabled": False}},
        "override": {"command": str(script_override), "initial_prompt": {"enabled": False}},
    }
    autostart_env.write_orchestrator_config(profiles, default="default")
    autostart = autostart_env.build_autostart()

    autostart.start(process="TASK-123", orchestrator_profile="override")

    assert wait_for_file(log_override)
    assert "pid=" in log_override.read_text()
    assert not log_default.exists()


def test_autostart_dry_run(autostart_env: AutoStartEnv) -> None:
    script, _ = autostart_env.make_orchestrator_script("mock")
    autostart_env.write_orchestrator_config(
        {"mock": {"command": str(script), "initial_prompt": {"enabled": False}}},
        default="mock",
    )
    autostart = autostart_env.build_autostart()

    result = autostart.start(process="TASK-DRY", dry_run=True)

    assert result["status"] == "dry_run"
    sessions = list((autostart_env.root / ".project" / "sessions").rglob("session.json"))
    assert not sessions


def test_autostart_cli_start_command(autostart_env: AutoStartEnv) -> None:
    script, log = autostart_env.make_orchestrator_script("cli")
    autostart_env.write_orchestrator_config(
        {"cli": {"command": str(script), "initial_prompt": {"enabled": False}}},
        default="cli",
    )
    autostart_env.reload_configs()

    cmd = [sys.executable, "-m", "edison", "session", "create", "--session-id", "TASK-CLI", "--no-worktree"]

    run_with_timeout(cmd, cwd=autostart_env.root, check=True)

    assert wait_for_file(log)
    sessions = list((autostart_env.root / ".project" / "sessions" / "wip").glob("*.json"))
    assert sessions
