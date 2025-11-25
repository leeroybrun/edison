from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
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


def _seed_incomplete_validation_tx(root: Path, session_id: str, tx_id: str = "tx-incomplete-1") -> Path:
    """Create a minimal incomplete validation transaction tree under root."""
    base = root / ".project" / "sessions" / "_tx" / session_id / "validation" / tx_id
    staging = base / "staging"
    snapshot = base / "snapshot"
    staging.mkdir(parents=True, exist_ok=True)
    snapshot.mkdir(parents=True, exist_ok=True)
    meta = {
        "txId": tx_id,
        "sessionId": session_id,
        "startedAt": "2025-01-01T00:00:00Z",
        "finalizedAt": None,
        "abortedAt": None,
    }
    (base / "meta.json").write_text(json.dumps(meta), encoding="utf-8")
    # Marker file to prove cleanup
    (staging / "_marker").write_text("x", encoding="utf-8")
    return base


@pytest.mark.fast
def test_detect_incomplete_transactions_reports_pending(tmp_path: Path) -> None:
    """detect_incomplete_transactions() should list incomplete tx metadata."""
    project_root = tmp_path
    (project_root / ".project" / "sessions" / "draft").mkdir(parents=True, exist_ok=True)
    (project_root / ".project" / "sessions" / "draft" / "sess-det").mkdir(parents=True, exist_ok=True)
    (project_root / ".project" / "sessions" / "draft" / "sess-det" / "session.json").write_text(
        json.dumps({"id": "sess-det", "status": "wip"}), encoding="utf-8"
    )
    tx_dir = _seed_incomplete_validation_tx(project_root, "sess-det")

    repo_root = _repo_root()

    env = os.environ.copy()
    env.update(
        {
            "AGENTS_PROJECT_ROOT": str(project_root),
        }
    )

    code = r"""
from __future__ import annotations
import json
import os
import sys
from pathlib import Path

# Add src to path so we can import edison
repo_root = Path(__file__).resolve().parents[2] if "__file__" in dir() else Path.cwd()

from edison.core.session.recovery import detect_incomplete_transactions

entries = detect_incomplete_transactions()
payload = []
for e in entries:
    payload.append({
        "sessionId": e.get("sessionId"),
        "txDir": str(e.get("txDir")),
    })
print(json.dumps(payload))
"""

    res = run_with_timeout(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, res.stderr
    data = json.loads(res.stdout or "[]")
    assert any(entry["txDir"] == str(tx_dir) for entry in data), data


@pytest.mark.fast
def test_recover_validation_tx_cli_cleans_staging_and_is_idempotent(tmp_path: Path) -> None:
    """recover_incomplete_validation_transactions() should clean incomplete tx directories."""
    project_root = tmp_path
    (project_root / ".project" / "sessions" / "wip").mkdir(parents=True, exist_ok=True)
    tx_dir = _seed_incomplete_validation_tx(project_root, "sess-cli", tx_id="tx-cli-1")

    repo_root = _repo_root()

    env = os.environ.copy()
    env.update({"AGENTS_PROJECT_ROOT": str(project_root)})

    code = r"""
from __future__ import annotations
import sys
from pathlib import Path

# Add src to path so we can import edison
repo_root = Path(__file__).resolve().parents[2] if "__file__" in dir() else Path.cwd()

from edison.core.session.recovery import recover_incomplete_validation_transactions

# First run: should recover at least one transaction
count1 = recover_incomplete_validation_transactions("sess-cli")
print(f"Recovered: {count1}")
assert count1 > 0, "Should recover at least one transaction"

# Second run: idempotent, nothing to recover and no error
count2 = recover_incomplete_validation_transactions("sess-cli")
print(f"Second run recovered: {count2}")
assert count2 == 0, "Second run should find nothing to recover"
"""

    res = run_with_timeout(
        [sys.executable, "-c", code],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Recovery failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"

    # Staging/snapshot should be removed
    assert not (tx_dir / "staging").exists()
    assert not (tx_dir / "snapshot").exists()
