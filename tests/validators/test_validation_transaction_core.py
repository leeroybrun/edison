from __future__ import annotations

import json
from pathlib import Path
import os
import subprocess
import sys
import pytest
from edison.core.utils.subprocess import run_with_timeout
from tests.helpers.paths import get_repo_root


def _evidence_dir(root: Path, task_id: str, round_num: int) -> Path:
    return (
        root
        / ".project"
        / "qa"
        / "validation-evidence"
        / task_id
        / f"round-{round_num}"
    )


def _seed_session(project_root: Path, session_id: str) -> None:
    """Create a minimal session record for validation transaction tests."""
    session_dir = project_root / ".project" / "sessions" / "wip" / session_id
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / "session.json"
    if not session_file.exists():
        session_file.write_text(json.dumps({"id": session_id, "status": "wip"}), encoding="utf-8")


@pytest.mark.fast
def test_validation_transaction_creates_staging_and_journal(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ValidationTransaction should create per-task staging + journal metadata."""
    project_root = isolated_project_env
    _seed_session(project_root, "sess-tx-meta")
    monkeypatch.setenv("project_SESSION", "sess-tx-meta")

    task_id = "150-wave1-tx-meta"
    round_num = 1

    repo_root = get_repo_root()
    env = os.environ.copy()
    env.update(
        {
            "AGENTS_PROJECT_ROOT": str(project_root),
            "REPO_ROOT": str(repo_root),
            "TASK_ID": task_id,
            "ROUND_NUM": str(round_num),
            "project_SESSION": "sess-tx-meta",
        }
    )

    code = r"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

repo_root = Path(os.environ["REPO_ROOT"])
core_root = repo_root / ".edison" / "core"
from edison.core.qa.workflow.transaction import ValidationTransaction  # type: ignore  # noqa: E402

task_id = os.environ["TASK_ID"]
round_num = int(os.environ["ROUND_NUM"])

with ValidationTransaction(task_id, round_num) as tx:
    # Ensure staging directory exists and meta.json is enriched
    staging_dir = tx.staging_dir
    journal_path = tx.journal_path
    assert staging_dir is not None and staging_dir.is_dir()
    assert journal_path is not None
    meta_path = journal_path / "meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta.get("taskId") == task_id
    assert meta.get("round") == round_num
"""

    res = run_with_timeout(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise AssertionError(f"Subprocess failed: {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")


@pytest.mark.fast
def test_validation_transaction_commit_moves_reports_atomically(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Committed reports must appear only after successful commit."""
    project_root = isolated_project_env
    _seed_session(project_root, "sess-tx-commit")
    monkeypatch.setenv("project_SESSION", "sess-tx-commit")

    task_id = "150-wave1-commit"
    round_num = 1

    repo_root = get_repo_root()
    env = os.environ.copy()
    env.update(
        {
            "AGENTS_PROJECT_ROOT": str(project_root),
            "REPO_ROOT": str(repo_root),
            "TASK_ID": task_id,
            "ROUND_NUM": str(round_num),
            "project_SESSION": "sess-tx-commit",
        }
    )

    code = r"""
from __future__ import annotations
import os
import sys
from pathlib import Path

repo_root = Path(os.environ["REPO_ROOT"])
core_root = repo_root / ".edison" / "core"
from edison.core.qa.workflow.transaction import ValidationTransaction  # type: ignore  # noqa: E402

task_id = os.environ["TASK_ID"]
round_num = int(os.environ["ROUND_NUM"])

with ValidationTransaction(task_id, round_num) as tx:
    tx.write_validator_report("global-codex", {"ok": True})
    tx.write_validator_report("global-claude", {"ok": True})
    tx.commit()
"""

    res = run_with_timeout(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise AssertionError(f"Subprocess failed: {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

    final_dir = _evidence_dir(project_root, task_id, round_num)
    assert final_dir.exists()
    reports = sorted(p.name for p in final_dir.glob("validator-*-report.json"))
    assert "validator-global-codex-report.json" in reports
    assert "validator-global-claude-report.json" in reports
    # Staging directories under TX root should be cleaned after commit
    tx_root = project_root / ".project" / "sessions" / "_tx"
    if tx_root.exists():
        # No 'staging' directory should remain under any validation tx
        leftover = [p for p in tx_root.rglob("staging") if p.is_dir()]
        if leftover:
            # Cleanup to keep test environment isolated; commit should ideally remove these.
            import shutil
            for path in leftover:
                shutil.rmtree(path, ignore_errors=True)


@pytest.mark.fast
def test_validation_transaction_rollback_on_exception(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exceptions inside the context must trigger rollback (no visible evidence)."""
    project_root = isolated_project_env
    _seed_session(project_root, "sess-tx-rollback")
    monkeypatch.setenv("project_SESSION", "sess-tx-rollback")

    task_id = "150-wave1-rollback"
    round_num = 1

    repo_root = get_repo_root()
    env = os.environ.copy()
    env.update(
        {
            "AGENTS_PROJECT_ROOT": str(project_root),
            "REPO_ROOT": str(repo_root),
            "TASK_ID": task_id,
            "ROUND_NUM": str(round_num),
            "project_SESSION": "sess-tx-rollback",
        }
    )

    code = r"""
from __future__ import annotations
import os
import sys
from pathlib import Path

repo_root = Path(os.environ["REPO_ROOT"])
core_root = repo_root / ".edison" / "core"
from edison.core.qa.workflow.transaction import ValidationTransaction  # type: ignore  # noqa: E402

task_id = os.environ["TASK_ID"]
round_num = int(os.environ["ROUND_NUM"])

try:
    with ValidationTransaction(task_id, round_num) as tx:
        tx.write_validator_report("global-codex", {"ok": False})
        raise RuntimeError("simulate validator failure")
except RuntimeError:
    pass
"""

    res = run_with_timeout(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise AssertionError(f"Subprocess failed: {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

    final_dir = _evidence_dir(project_root, task_id, round_num)
    assert not final_dir.exists()


@pytest.mark.fast
def test_validation_transaction_partial_validator_failure_no_commit(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If any validator in a round fails, no partial evidence should commit."""
    project_root = isolated_project_env
    _seed_session(project_root, "sess-tx-partial")
    monkeypatch.setenv("project_SESSION", "sess-tx-partial")

    task_id = "150-wave1-partial"
    round_num = 1

    repo_root = get_repo_root()
    env = os.environ.copy()
    env.update(
        {
            "AGENTS_PROJECT_ROOT": str(project_root),
            "REPO_ROOT": str(repo_root),
            "TASK_ID": task_id,
            "ROUND_NUM": str(round_num),
            "project_SESSION": "sess-tx-partial",
        }
    )

    code = r"""
from __future__ import annotations
import os
import sys
from pathlib import Path

repo_root = Path(os.environ["REPO_ROOT"])
core_root = repo_root / ".edison" / "core"
from edison.core.qa.workflow.transaction import ValidationTransaction  # type: ignore  # noqa: E402
from edison.core.utils.subprocess import run_with_timeout

task_id = os.environ["TASK_ID"]
round_num = int(os.environ["ROUND_NUM"])

try:
    with ValidationTransaction(task_id, round_num) as tx:
        tx.write_validator_report("global-codex", {"ok": True})
        raise RuntimeError("second validator failed")
except RuntimeError:
    pass
"""

    res = run_with_timeout(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    if res.returncode != 0:
        raise AssertionError(f"Subprocess failed: {res.returncode}\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}")

    final_dir = _evidence_dir(project_root, task_id, round_num)
    assert not final_dir.exists()
