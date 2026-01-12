"""Repo-state command evidence snapshot store.

Command evidence (tests/lint/build/type-check outputs) is primarily a property of
the repository state, not a specific task round. Edison stores this evidence in
snapshot directories keyed by a deterministic git fingerprint.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from edison.core.config.domains.ci import CIConfig
from edison.core.utils.git.fingerprint import compute_repo_fingerprint, compute_workspace_fingerprint
from edison.core.utils.paths.management import get_management_paths

from .command_evidence import parse_command_evidence


@dataclass(frozen=True, slots=True)
class SnapshotKey:
    git_head: str
    diff_hash: str
    git_dirty: bool

    @classmethod
    def from_fingerprint(cls, fp: dict[str, Any]) -> "SnapshotKey":
        return cls(
            git_head=str(fp.get("gitHead") or "").strip() or "unknown-head",
            diff_hash=str(fp.get("diffHash") or "").strip() or "unknown-diff",
            git_dirty=bool(fp.get("gitDirty", False)),
        )

    def as_dict(self) -> dict[str, Any]:
        return {"gitHead": self.git_head, "diffHash": self.diff_hash, "gitDirty": bool(self.git_dirty)}


def snapshot_root(*, project_root: Path) -> Path:
    qa_root = get_management_paths(project_root).get_qa_root()
    return qa_root / "evidence-snapshots"


def snapshot_dir(*, project_root: Path, key: SnapshotKey) -> Path:
    cleanliness = "dirty" if key.git_dirty else "clean"
    return snapshot_root(project_root=project_root) / key.git_head / key.diff_hash / cleanliness


def current_snapshot_key(*, project_root: Path) -> SnapshotKey:
    return SnapshotKey.from_fingerprint(current_snapshot_fingerprint(project_root=project_root))


def current_snapshot_fingerprint(*, project_root: Path) -> dict[str, Any]:
    """Compute the fingerprint used for command-evidence snapshots.

    Default behavior is single-repo git fingerprinting. Projects can opt into
    multi-repo workspace fingerprinting via:

      ci:
        fingerprint:
          git_roots: [...]
          extra_files: [...]
    """
    cfg = CIConfig(repo_root=project_root)
    roots = cfg.resolve_fingerprint_git_roots()
    extra_files = cfg.resolve_fingerprint_extra_files()

    # Fail-closed default: if misconfigured (empty lists), fall back to repo-only fingerprint.
    if roots or extra_files:
        if not roots:
            roots = [project_root]
        return compute_workspace_fingerprint(git_roots=roots, extra_files=extra_files)

    return compute_repo_fingerprint(project_root)


def snapshot_file(*, project_root: Path, key: SnapshotKey, filename: str) -> Path:
    return snapshot_dir(project_root=project_root, key=key) / str(filename)


def is_snapshot_file_passed(path: Path) -> tuple[bool, str]:
    """Return (passed, reason) for a command evidence file."""
    parsed = parse_command_evidence(path)
    if parsed is None:
        return False, "unparseable"
    try:
        exit_code = parsed.get("exitCode")
        if exit_code is None:
            return False, "missing_exit_code"
        return (int(exit_code) == 0), f"exit:{int(exit_code)}"
    except Exception:
        return False, "invalid_exit_code"


def snapshot_status(
    *,
    project_root: Path,
    key: SnapshotKey,
    required_files: list[str],
) -> dict[str, Any]:
    """Return snapshot completeness status for required command evidence files."""
    present: list[str] = []
    missing: list[str] = []
    invalid: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []

    snap_dir = snapshot_dir(project_root=project_root, key=key)
    for filename in required_files:
        name = str(filename).strip()
        if not name:
            continue
        p = snap_dir / name
        if not p.exists():
            missing.append(name)
            continue
        present.append(name)
        ok, reason = is_snapshot_file_passed(p)
        if reason == "unparseable":
            invalid.append({"file": name, "reason": reason})
        elif not ok:
            failed.append({"file": name, "reason": reason})

    return {
        "snapshotDir": str(snap_dir),
        "present": present,
        "missing": missing,
        "invalid": invalid,
        "failed": failed,
        "complete": len(missing) == 0,
        "passed": len(failed) == 0,
        "valid": len(invalid) == 0,
    }


__all__ = [
    "SnapshotKey",
    "current_snapshot_fingerprint",
    "current_snapshot_key",
    "snapshot_dir",
    "snapshot_file",
    "snapshot_root",
    "snapshot_status",
]

