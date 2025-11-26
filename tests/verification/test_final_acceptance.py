"""
Final acceptance tests verifying all requirements met for the auto-start system.
"""
from __future__ import annotations

import os
from pathlib import Path
import sys
import pytest

from tests.integration.test_session_autostart import AutoStartEnv
from edison.core.session.autostart import SessionAutoStart, SessionAutoStartError
from edison.core.session.manager import SessionManager
from edison.core.session.naming import generate_session_id, reset_session_naming_counter
from edison.core.config.domains import OrchestratorConfig
from edison.core.process.inspector import infer_session_id


@pytest.fixture
def acceptance_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Provision isolated environment with three orchestrator profiles."""
    env = AutoStartEnv(tmp_path, monkeypatch)
    env.write_defaults()
    env.write_session_config()

    script, _ = env.make_orchestrator_script("mock")
    profiles = {
        "claude": {
            "command": str(script),
            "cwd": "{session_worktree}",
            "env": {"KEEP_ALIVE": "1"},
            "initial_prompt": {"enabled": False, "method": "stdin"},
        },
        "codex": {
            "command": str(script),
            "cwd": "{session_worktree}",
            "initial_prompt": {"enabled": False},
        },
        "gemini": {
            "command": str(script),
            "cwd": "{session_worktree}",
            "initial_prompt": {"enabled": False},
        },
    }
    env.write_orchestrator_config(profiles, default="claude")
    return env


class TestFinalAcceptance:
    """Verify all original requirements met."""

    def test_requirement_1_session_creation(self, acceptance_env: AutoStartEnv):
        autostart = acceptance_env.build_autostart()
        result = autostart.start(process="REQ-1", orchestrator_profile="claude")

        session = SessionManager(project_root=acceptance_env.root).get_session(result["session_id"])
        assert session["meta"].get("autoStarted") is True
        assert session["meta"].get("orchestratorProfile") == "claude"

    def test_requirement_2_worktree_creation(self, acceptance_env: AutoStartEnv):
        autostart = acceptance_env.build_autostart()
        result = autostart.start(process="REQ-2", orchestrator_profile="claude")
        worktree_path = Path(result["worktree_path"])

        assert worktree_path.exists()
        assert (worktree_path / ".git").exists()

    def test_requirement_3_orchestrator_launch(self, acceptance_env: AutoStartEnv):
        autostart = acceptance_env.build_autostart()
        result = autostart.start(process="REQ-3", orchestrator_profile="claude")

        proc = result.get("process")
        assert proc is not None
        assert proc.poll() is None
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    def test_requirement_4_prompt_delivery(self, acceptance_env: AutoStartEnv):
        autostart = acceptance_env.build_autostart()
        prompt_file = acceptance_env.root / "prompt.md"
        marker = "PROMPT-MARKER"
        prompt_file.write_text(marker, encoding="utf-8")

        result = autostart.start(
            process="REQ-4",
            orchestrator_profile="claude",
            prompt_path=prompt_file,
        )
        log_path = acceptance_env.root / ".project" / "sessions" / "wip" / result["session_id"] / "orchestrator.log"
        assert log_path.exists()
        assert marker in log_path.read_text()

        proc = result.get("process")
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()

    def test_requirement_5_multi_orchestrator_support(self, acceptance_env: AutoStartEnv):
        autostart = acceptance_env.build_autostart()
        sessions = []
        for profile in ("claude", "codex", "gemini"):
            res = autostart.start(
                process=f"REQ-5-{profile}",
                orchestrator_profile=profile,
                dry_run=True,
                launch_orchestrator=False,
                persist_dry_run=True,
            )
            sessions.append(res["session_id"])
            session = SessionManager(project_root=acceptance_env.root).get_session(res["session_id"])
            assert session["meta"].get("orchestratorProfile") == profile
        assert len(sessions) == 3

    def test_requirement_6_pid_based_naming(self):
        reset_session_naming_counter()
        session_id = generate_session_id()

        assert session_id == infer_session_id()

    def test_requirement_7_atomic_rollback(self, acceptance_env: AutoStartEnv):
        bad_profiles = {
            "broken": {
                "command": "non-existent-binary",
                "cwd": "{session_worktree}",
                "initial_prompt": {"enabled": False},
            }
        }
        acceptance_env.write_orchestrator_config(bad_profiles, default="broken")
        autostart = acceptance_env.build_autostart()
        before = set((acceptance_env.root / ".project" / "sessions" / "wip").glob("*"))
        with pytest.raises(SessionAutoStartError):
            autostart.start(process="REQ-7", orchestrator_profile="broken")
        after = set((acceptance_env.root / ".project" / "sessions" / "wip").glob("*"))
        assert before == after

    def test_requirement_8_no_legacy_code(self):
        # Edison is now a standalone repository, check for legacy lib directly
        repo_root = Path(__file__).resolve().parents[2]
        # Legacy worktreelib.py should not exist in the edison.core.lib package
        assert not (repo_root / "edison" / "core" / "lib" / "worktreelib.py").exists()

    def test_requirement_9_configurable_via_yaml(self, acceptance_env: AutoStartEnv):
        cfg = OrchestratorConfig(acceptance_env.root, validate=False)
        profile = cfg.get_profile("claude", context={"session_worktree": "/tmp/wt", "project_root": acceptance_env.root}, expand=True)
        assert profile["cwd"] == "/tmp/wt"
        assert "profiles" in cfg._orchestrator_config  # type: ignore[attr-defined]

    def test_requirement_10_tdd_evidence(self):
        # Edison is now a standalone repository, tests are at repo_root/tests/
        repo_root = Path(__file__).resolve().parents[2]
        assert (repo_root / "tests" / "integration" / "test_session_autostart.py").exists()
        assert (repo_root / "tests" / "e2e" / "test_autostart_real_orchestrators.py").exists()
