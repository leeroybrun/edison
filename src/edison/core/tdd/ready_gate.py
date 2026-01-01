"""TDD readiness gate checks used by `edison task ready`.

This module is intentionally small and deterministic:
- No network access
- Reads evidence files and local repo state
- Runs an optional project-provided verification script
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterable, Sequence

from edison.core.qa.evidence.command_evidence import parse_exit_code
from edison.core.session.paths import get_session_bases


def _should_skip_path(path: Path) -> bool:
    parts = set(path.parts)
    return bool(parts & {".git", ".edison", ".project", ".worktrees", "node_modules", "__pycache__"})


def scan_for_blocked_test_tokens(
    *,
    roots: Sequence[Path],
    file_globs: Sequence[str],
    blocked_tokens: Sequence[str],
) -> list[tuple[Path, str]]:
    """Return a list of (path, token) occurrences for blocked tokens in test files."""
    if not blocked_tokens:
        return []

    hits: list[tuple[Path, str]] = []
    seen: set[Path] = set()

    for root in roots:
        if not root or not root.exists():
            continue
        for pat in file_globs:
            for path in root.glob(pat):
                try:
                    p = path.resolve()
                except Exception:
                    p = path
                if p in seen:
                    continue
                seen.add(p)
                if not p.is_file() or _should_skip_path(p):
                    continue
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                for tok in blocked_tokens:
                    if tok and tok in text:
                        hits.append((p, tok))
    return hits


def run_verification_script(script_path: Path, *, cwd: Path) -> subprocess.CompletedProcess:
    """Run an optional project-provided verification script (e.g., coverage gate)."""
    return subprocess.run(
        [str(script_path)],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _find_tdd_round_dir(project_root: Path, session_id: str, task_id: str, round_num: int = 1) -> Path | None:
    for base in get_session_bases(session_id=session_id, project_root=project_root):
        cand = base / "tasks" / task_id / "evidence" / "tdd" / f"round-{round_num}"
        if cand.exists():
            return cand
    return None


def validate_tdd_evidence(
    *,
    project_root: Path,
    session_id: str,
    task_id: str,
    enforce_red_green_refactor: bool,
    worktree_path: Path | None,
) -> None:
    """Validate TDD evidence for a task/session.

    This is best-effort and only enforces when evidence exists.
    """
    rd = _find_tdd_round_dir(project_root, session_id, task_id, round_num=1)
    if rd is None:
        return

    required = {
        "red-timestamp.txt": "RED timestamp",
        "green-timestamp.txt": "GREEN timestamp",
        "test-commit.txt": "test commit",
        "impl-commit.txt": "implementation commit",
    }
    for name, label in required.items():
        if not (rd / name).exists():
            raise ValueError(f"TDD evidence missing: {label} ({rd / name})")

    red_ts = float((rd / "red-timestamp.txt").read_text().strip())
    green_ts = float((rd / "green-timestamp.txt").read_text().strip())
    if not (red_ts < green_ts):
        raise ValueError("TDD evidence invalid: RED timestamp must be before GREEN timestamp")

    test_commit = (rd / "test-commit.txt").read_text().strip()
    impl_commit = (rd / "impl-commit.txt").read_text().strip()
    if not test_commit or not impl_commit or test_commit == impl_commit:
        raise ValueError("TDD evidence invalid: test and implementation commits must be present and distinct")

    refactor_commit_path = rd / "refactor-commit.txt"
    refactor_ts_path = rd / "refactor-timestamp.txt"

    if enforce_red_green_refactor:
        if not (refactor_commit_path.exists() and refactor_ts_path.exists()):
            raise ValueError("REFACTOR evidence required: provide a [REFACTOR] commit and timestamps")

    if refactor_commit_path.exists() and refactor_ts_path.exists():
        refactor_ts = float(refactor_ts_path.read_text().strip())
        if not (green_ts < refactor_ts):
            raise ValueError("TDD evidence invalid: GREEN timestamp must be before REFACTOR timestamp")

    # Optional: verify commit message tags when git is available via a worktree.
    if worktree_path and worktree_path.exists():
        def _subject(commit: str) -> str:
            cp = subprocess.run(
                ["git", "show", "-s", "--format=%s", commit],
                cwd=worktree_path,
                capture_output=True,
                text=True,
                check=False,
            )
            return (cp.stdout or "").strip()

        subj_test = _subject(test_commit)
        subj_impl = _subject(impl_commit)
        if "[RED]" not in subj_test:
            raise ValueError("TDD evidence invalid: test commit subject must include [RED]")
        if "[GREEN]" not in subj_impl:
            raise ValueError("TDD evidence invalid: implementation commit subject must include [GREEN]")

        if refactor_commit_path.exists():
            ref_commit = refactor_commit_path.read_text().strip()
            if ref_commit:
                subj_ref = _subject(ref_commit)
                if "[REFACTOR]" not in subj_ref:
                    raise ValueError("TDD evidence invalid: refactor commit subject must include [REFACTOR]")


def validate_command_evidence_exit_codes(round_dir: Path, *, required_files: Iterable[str]) -> None:
    """Ensure required command evidence files report success exit codes when present."""
    for name in required_files:
        path = round_dir / str(name)
        if not path.exists():
            continue
        try:
            code = parse_exit_code(path.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if code is not None and int(code) != 0:
            raise ValueError(f"Command evidence indicates failure: {path} (EXIT_CODE={code})")


__all__ = [
    "scan_for_blocked_test_tokens",
    "run_verification_script",
    "validate_tdd_evidence",
    "validate_command_evidence_exit_codes",
]

