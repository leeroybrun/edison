"""
End-to-end integration tests with REAL orchestrators.

These tests verify the complete auto-start flow with actual LLM CLIs:
- claude (Claude Code)
- codex (OpenAI Codex CLI)
- gemini (Google Gemini CLI)

Tests are skipped gracefully if orchestrator binaries are not installed.
"""

from __future__ import annotations

import inspect
import json
import os
import shutil
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Dict, Optional

import pytest

from edison.core.utils.subprocess import run_with_timeout
from helpers.env import TestGitRepo, TestProjectDir
from tests.helpers.timeouts import PROCESS_WAIT_TIMEOUT

try:  # Will fail RED phase until autostart is implemented (expected)
    from edison.core.session.autostart import SessionAutoStart
except Exception as exc:  # pragma: no cover - explicit RED failure path
    SessionAutoStart = None
    AUTOSTART_IMPORT_ERROR = exc
else:
    AUTOSTART_IMPORT_ERROR = None


# Helper: Check if orchestrator binary exists
def has_orchestrator(name: str) -> bool:
    """Check if orchestrator binary is in PATH."""

    return shutil.which(name) is not None


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    while cur != cur.parent:
        if (cur / ".git").exists():
            return cur
        cur = cur.parent
    raise RuntimeError("Repository root with .git not found")


REPO_ROOT = _repo_root()


def require_autostart() -> None:
    """Fail fast when SessionAutoStart is missing (RED expectation)."""

    if SessionAutoStart is None:
        pytest.fail(f"SessionAutoStart not implemented yet: {AUTOSTART_IMPORT_ERROR}")


def _extract(result: Any, key: str, default: Any = None) -> Any:
    if result is None:
        return default
    if isinstance(result, dict):
        return result.get(key, default)
    return getattr(result, key, default)


def _find_log(repo_root: Path, session_id: str) -> Optional[Path]:
    candidates = [
        repo_root / ".project" / "sessions" / "wip" / session_id / "orchestrator.log",
        repo_root / ".project" / "sessions" / "wip" / session_id / "logs" / "orchestrator.log",
        repo_root / ".edison" / "logs" / "sessions" / session_id / "orchestrator.log",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    # Last resort: shallow search to avoid excessive IO
    for path in (repo_root / ".project").rglob("orchestrator.log"):
        if session_id in str(path):
            return path
    return None


def _load_session(repo_root: Path, session_id: str) -> Dict[str, Any]:
    candidates = [
        repo_root / ".project" / "sessions" / "wip" / f"{session_id}.json",
        repo_root / ".project" / "sessions" / "active" / f"{session_id}.json",
        repo_root / ".project" / "sessions" / "done" / f"{session_id}.json",
    ]
    session_path = next((p for p in candidates if p.exists()), None)
    assert session_path is not None, f"session.json not found for {session_id}"
    return json.loads(session_path.read_text())


@pytest.fixture
def autostart_env(tmp_path: Path) -> Dict[str, Any]:
    """Provision isolated repo + config for auto-start tests."""

    project_dir = TestProjectDir(tmp_path, REPO_ROOT)
    git_repo = TestGitRepo(tmp_path)

    # Copy core config + guides so SessionConfig/OrchestratorConfig resolve under tmp repo
    core_src = REPO_ROOT / ".edison" / "core"
    core_dst = tmp_path / ".edison" / "core"
    for sub in ("config", "guides", "templates"):
        src = core_src / sub
        if src.exists():
            shutil.copytree(src, core_dst / sub, dirs_exist_ok=True)

    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(tmp_path)
    env["project_ROOT"] = str(tmp_path)
    env.setdefault("PROJECT_NAME", "edison-autostart-test")

    return {
        "root": tmp_path,
        "env": env,
        "project_dir": project_dir,
        "git_repo": git_repo,
    }


def start_session(
    env: Dict[str, Any],
    *,
    process: str,
    orchestrator: str,
    prompt_path: Optional[Path] = None,
    dry_run: bool = False,
) -> Any:
    """Invoke SessionAutoStart.start with signature-inspection to stay forward-compatible."""

    require_autostart()
    starter = SessionAutoStart(project_root=env["root"], env=env.get("env"))
    start_fn = getattr(starter, "start", None) or getattr(starter, "run", None)
    assert callable(start_fn), "SessionAutoStart missing start() entrypoint"

    base_kwargs: Dict[str, Any] = {
        "process": process,
        "orchestrator_profile": orchestrator,
        "prompt_path": str(prompt_path) if prompt_path else None,
        "dry_run": dry_run,
        "launch_orchestrator": not dry_run,
        "persist_dry_run": True,
    }

    sig = inspect.signature(start_fn)
    filtered = {k: v for k, v in base_kwargs.items() if k in sig.parameters and v is not None}
    return start_fn(**filtered)


class TestRealOrchestratorIntegration:
    """E2E tests with real orchestrator binaries."""

    @pytest.mark.skipif(not has_orchestrator("claude"), reason="Claude not installed")
    def test_autostart_with_real_claude(self, autostart_env):
        """Test auto-start with real Claude Code."""

        prompt_file = autostart_env["root"] / "prompt-claude.md"
        prompt_file.write_text("CLAUDE PROMPT: hello from integration test\n")

        result = start_session(
            autostart_env,
            process="proc-claude",
            orchestrator="claude",
            prompt_path=prompt_file,
            dry_run=False,
        )

        session_id = _extract(result, "session_id") or _extract(result, "id")
        assert session_id, "auto-start must return session_id"

        session_data = _load_session(autostart_env["root"], session_id)
        assert session_data["meta"].get("orchestratorProfile") == "claude"

        wt_path = Path(_extract(result, "worktree_path") or session_data["git"].get("worktreePath"))
        autostart_env["git_repo"].assert_worktree_exists(wt_path)

        proc: subprocess.Popen | None = _extract(result, "process") or _extract(result, "orchestrator_process")
        assert proc is not None, "orchestrator process handle not returned"
        assert proc.poll() is None, "orchestrator terminated prematurely"
        proc.terminate()
        try:
            proc.wait(timeout=PROCESS_WAIT_TIMEOUT)
        except Exception:
            proc.kill()

    @pytest.mark.skipif(not has_orchestrator("codex"), reason="Codex not installed")
    def test_autostart_with_real_codex(self, autostart_env):
        """Test auto-start with real Codex CLI."""

        prompt_file = autostart_env["root"] / "prompt-codex.md"
        prompt_file.write_text("CODEX PROMPT: hello from integration test\n")

        result = start_session(
            autostart_env,
            process="proc-codex",
            orchestrator="codex",
            prompt_path=prompt_file,
            dry_run=False,
        )

        session_id = _extract(result, "session_id") or _extract(result, "id")
        assert session_id

        session_data = _load_session(autostart_env["root"], session_id)
        assert session_data["meta"].get("orchestratorProfile") == "codex"

        wt_path = Path(_extract(result, "worktree_path") or session_data["git"].get("worktreePath"))
        autostart_env["git_repo"].assert_worktree_exists(wt_path)

        proc: subprocess.Popen | None = _extract(result, "process") or _extract(result, "orchestrator_process")
        assert proc is not None
        assert proc.poll() is None
        proc.terminate()
        try:
            proc.wait(timeout=PROCESS_WAIT_TIMEOUT)
        except Exception:
            proc.kill()

    @pytest.mark.skipif(not has_orchestrator("gemini"), reason="Gemini not installed")
    def test_autostart_with_real_gemini(self, autostart_env):
        """Test auto-start with real Gemini CLI."""

        prompt_file = autostart_env["root"] / "prompt-gemini.md"
        prompt_file.write_text("GEMINI PROMPT: hello from integration test\n")

        result = start_session(
            autostart_env,
            process="proc-gemini",
            orchestrator="gemini",
            prompt_path=prompt_file,
            dry_run=False,
        )

        session_id = _extract(result, "session_id") or _extract(result, "id")
        assert session_id

        session_data = _load_session(autostart_env["root"], session_id)
        assert session_data["meta"].get("orchestratorProfile") == "gemini"

        wt_path = Path(_extract(result, "worktree_path") or session_data["git"].get("worktreePath"))
        autostart_env["git_repo"].assert_worktree_exists(wt_path)

        proc: subprocess.Popen | None = _extract(result, "process") or _extract(result, "orchestrator_process")
        assert proc is not None
        assert proc.poll() is None
        proc.terminate()
        try:
            proc.wait(timeout=PROCESS_WAIT_TIMEOUT)
        except Exception:
            proc.kill()

    def test_multi_session_isolation(self, autostart_env):
        """Test multiple sessions can run in parallel with worktree isolation."""

        available = [name for name in ("claude", "codex", "gemini") if has_orchestrator(name)]
        if not available:
            pytest.skip("No orchestrator binaries available for isolation test")

        orchestrator = available[0]

        def _start(idx: int):
            return start_session(
                autostart_env,
                process=f"parallel-{idx}",
                orchestrator=orchestrator,
                prompt_path=None,
                dry_run=True,
            )

        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(_start, range(3)))

        session_ids = []
        worktrees = []
        for res in results:
            sid = _extract(res, "session_id") or _extract(res, "id")
            assert sid
            session_ids.append(sid)
            session_data = _load_session(autostart_env["root"], sid)
            wt_path = Path(_extract(res, "worktree_path") or session_data["git"].get("worktreePath"))
            worktrees.append(wt_path)
            autostart_env["git_repo"].assert_worktree_exists(wt_path)

        assert len(set(session_ids)) == 3, f"Session IDs not unique: {session_ids}"
        assert len(set([p.resolve() for p in worktrees])) == 3, "Worktrees should be isolated"

    def test_session_naming_uniqueness(self, autostart_env):
        """Rapid-fire create sessions to ensure unique IDs are generated."""

        available = [name for name in ("claude", "codex", "gemini") if has_orchestrator(name)]
        if not available:
            pytest.skip("No orchestrator binaries available for naming test")

        orchestrator = available[0]
        ids = []
        for i in range(10):
            res = start_session(
                autostart_env,
                process=f"burst-{i}",
                orchestrator=orchestrator,
                dry_run=True,
            )
            sid = _extract(res, "session_id") or _extract(res, "id")
            ids.append(sid)

        assert len(ids) == len(set(ids)), f"Duplicate session IDs detected: {ids}"

    def test_prompt_delivery_to_real_orchestrator(self, autostart_env):
        """Test that initial prompt is delivered and logged for auditability."""

        available = [name for name in ("claude", "codex", "gemini") if has_orchestrator(name)]
        if not available:
            pytest.skip("No orchestrator binaries available for prompt delivery test")

        orchestrator = available[0]

        prompt_file = autostart_env["root"] / "prompt-delivery.md"
        marker = f"PROMPT-MARKER-{int(time.time())}"
        prompt_file.write_text(f"Verify prompt delivery {marker}\n")

        result = start_session(
            autostart_env,
            process="prompt-delivery",
            orchestrator=orchestrator,
            prompt_path=prompt_file,
            dry_run=False,
        )

        session_id = _extract(result, "session_id") or _extract(result, "id")
        assert session_id

        log_path = _find_log(autostart_env["root"], session_id)
        assert log_path is not None, "Orchestrator log file not found"
        log_body = log_path.read_text()
        assert marker in log_body, "Prompt marker not found in orchestrator log"

        proc: subprocess.Popen | None = _extract(result, "process") or _extract(result, "orchestrator_process")
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=PROCESS_WAIT_TIMEOUT)
            except Exception:
                proc.kill()
