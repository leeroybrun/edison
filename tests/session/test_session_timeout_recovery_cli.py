from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from edison.core.utils.subprocess import run_with_timeout


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    candidate: Path | None = None
    while cur != cur.parent:
        if (cur / ".git").exists():
            candidate = cur
        cur = cur.parent
    if candidate is None:
        raise RuntimeError("git root not found")
    if candidate.name == ".edison" and (candidate.parent / ".git").exists():
        return candidate.parent
    return candidate


REPO_ROOT = _repo_root()
CORE_ROOT = REPO_ROOT / ".edison" / "core"
SCRIPTS_DIR = CORE_ROOT / "scripts"


def _write(ts: str) -> str:
    # Normalize ISO string with Z suffix
    return ts.replace("+00:00", "Z")


def _seed_timeout_project() -> tuple[Path, dict[str, str]]:
    """Create a minimal project tree mirroring SessionTimeoutTests.setUp."""
    tmp = Path(tempfile.mkdtemp(prefix="project-timeout-recovery-"))
    for d in [
        ".project/tasks/todo",
        ".project/tasks/wip",
        ".project/tasks/blocked",
        ".project/tasks/done",
        ".project/tasks/validated",
        ".project/qa/waiting",
        ".project/qa/todo",
        ".project/qa/wip",
        ".project/qa/done",
        ".project/qa/validated",
        ".project/qa/validation-evidence",
        ".project/sessions/wip",
        ".project/sessions/done",
        ".project/sessions/validated",
        ".agents/sessions",
    ]:
        (tmp / d).mkdir(parents=True, exist_ok=True)

    # Copy templates referenced by scripts
    shutil.copyfile(
        REPO_ROOT / ".agents" / "sessions" / "TEMPLATE.json",
        tmp / ".agents" / "sessions" / "TEMPLATE.json",
    )
    shutil.copyfile(
        REPO_ROOT / ".project" / "qa" / "TEMPLATE.md",
        tmp / ".project" / "qa" / "TEMPLATE.md",
    )
    shutil.copyfile(
        REPO_ROOT / ".project" / "tasks" / "TEMPLATE.md",
        tmp / ".project" / "tasks" / "TEMPLATE.md",
    )

    env = os.environ.copy()
    env.update(
        {
            "project_ROOT": str(tmp),
            "AGENTS_PROJECT_ROOT": str(tmp),
            "project_OWNER": "codex-pid-9999",
            "PYTHONUNBUFFERED": "1",
        }
    )
    return tmp, env


def _run_cli(*argv: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    cmd = ["python3", *[str(a) for a in argv]]
    return run_with_timeout(cmd, cwd=cwd, env=env, capture_output=True, text=True)


def _write_session_age(root: Path, env: dict[str, str], session_id: str, hours_old: float) -> None:
    """Ensure a session exists and stamp createdAt/lastActive to hours_old in the past."""
    session_cli = SCRIPTS_DIR / "session"
    # Session is created in 'wip' state by default now, but recovery checks 'active'
    # So we must ensure it is active.
    sess_path = root / ".project" / "sessions" / "active" / session_id / "session.json"
    if not sess_path.exists():
        # Create (wip)
        res_new = _run_cli(session_cli, "new", "--owner", "tester", "--session-id", session_id, cwd=SCRIPTS_DIR, env=env)
        if res_new.returncode != 0:
            raise AssertionError(f"session new failed:\\nSTDERR: {res_new.stderr}\\nSTDOUT: {res_new.stdout}")
        # Start (wip -> active)
        res_start = _run_cli(session_cli, "start", session_id, cwd=SCRIPTS_DIR, env=env)
        if res_start.returncode != 0:
             raise AssertionError(f"session start failed:\\nSTDERR: {res_start.stderr}\\nSTDOUT: {res_start.stdout}")
            
    data = json.loads(sess_path.read_text())
    now = datetime.now(timezone.utc)
    past = now - timedelta(hours=hours_old)
    ts = _write(past.isoformat(timespec="seconds"))
    data.setdefault("meta", {})
    data["meta"]["createdAt"] = ts
    data["meta"]["lastActive"] = ts
    data["meta"].pop("claimedAt", None)
    sess_path.write_text(json.dumps(data, indent=2))


def test_recover_timed_out_sessions_cli_matches_session_detect_stale() -> None:
    """recover-timed-out-sessions --json reports and cleans expired sessions."""
    root, env = _seed_timeout_project()

    try:
        sid = "s-timeout-recover"
        _write_session_age(root, env, sid, hours_old=12.0)

        recover_cli = SCRIPTS_DIR / "recovery" / "recover-timed-out-sessions"

        # Run recovery wrapper (delegates to session detect-stale under the hood)
        res_rec = _run_cli(recover_cli, "--json", cwd=SCRIPTS_DIR, env=env)
        assert res_rec.returncode == 0, res_rec.stderr
        rec_payload = json.loads(res_rec.stdout or "{}")

        assert sid in rec_payload.get("expiredSessions", []), rec_payload
        assert sid in rec_payload.get("cleanedSessions", []), rec_payload
    finally:
        shutil.rmtree(root, ignore_errors=True)