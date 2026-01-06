"""Helpers for repo-state command evidence snapshots in tests.

Edison stores command evidence (lint/test/build/type-check outputs) in a snapshot
directory keyed by a deterministic git fingerprint. E2E tests often use a
non-git temp project; in that case the snapshot key deterministically resolves
to `unknown-head/<sha256(empty)>/clean`.
"""

from __future__ import annotations

from pathlib import Path

from edison.core.qa.evidence.command_evidence import write_command_evidence
from edison.core.qa.evidence.snapshots import SnapshotKey, snapshot_dir
from edison.core.utils.git.fingerprint import compute_repo_fingerprint


def get_current_snapshot_dir(*, repo_root: Path) -> Path:
    fp = compute_repo_fingerprint(repo_root)
    key = SnapshotKey.from_fingerprint(fp)
    return snapshot_dir(project_root=repo_root, key=key)


def write_passing_snapshot_command(
    *,
    repo_root: Path,
    filename: str,
    task_id: str = "snapshot",
    command_name: str | None = None,
    command: str = "echo ok",
    output: str = "ok\n",
    hmac_key: str | None = None,
) -> Path:
    """Write a schema-compliant command evidence file into the current snapshot."""
    snap = get_current_snapshot_dir(repo_root=repo_root)
    path = snap / str(filename)
    write_command_evidence(
        path=path,
        task_id=task_id,
        round_num=0,
        command_name=command_name or str(filename).replace("command-", "").replace(".txt", ""),
        command=command,
        cwd=str(repo_root),
        exit_code=0,
        output=output,
        fingerprint=compute_repo_fingerprint(repo_root),
        hmac_key=hmac_key,
    )
    return path
