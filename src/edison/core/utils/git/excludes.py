"""Git excludes utilities (per-worktree).

Edison wants different ignore noise policies for:
- primary checkout
- session worktrees
- meta worktree

Git's `.git/info/exclude` is repo-wide, so to get true per-worktree excludes we
use a per-worktree config value:

  git config --worktree core.excludesFile <path>

and write patterns into that file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Set

from edison.core.utils.io import ensure_lines_present
from edison.core.utils.subprocess import run_with_timeout


def _git_dir_for_checkout(checkout_path: Path) -> Path:
    """Return the absolute gitdir for this checkout.

    For worktrees, this resolves to `.git/worktrees/<name>`; for the primary
    checkout it is `.git`.
    """
    cp = run_with_timeout(
        ["git", "rev-parse", "--path-format=absolute", "--git-dir"],
        cwd=checkout_path,
        capture_output=True,
        text=True,
        check=True,
        timeout_type="git_operations",
    )
    return Path((cp.stdout or "").strip()).resolve()


def _ensure_core_excludes_file_configured(*, checkout_path: Path, excludes_file: Path) -> None:
    """Ensure `core.excludesFile` is set for this worktree checkout."""
    # Git requires `extensions.worktreeConfig=true` to use `git config --worktree` in
    # repos with multiple worktrees. Enable it (idempotent).
    run_with_timeout(
        ["git", "config", "--local", "extensions.worktreeConfig", "true"],
        cwd=checkout_path,
        capture_output=True,
        text=True,
        check=True,
        timeout_type="git_operations",
    )

    # Fail closed if git doesn't support --worktree config at all.
    probe = run_with_timeout(
        ["git", "config", "--worktree", "--get", "core.excludesFile"],
        cwd=checkout_path,
        capture_output=True,
        text=True,
        check=False,
        timeout_type="git_operations",
    )
    if probe.returncode not in (0, 1):
        raise RuntimeError(
            "git does not support --worktree config (required for per-worktree excludes): "
            f"rc={probe.returncode} err={(probe.stderr or '').strip()}"
        )

    current = (probe.stdout or "").strip()
    desired = str(excludes_file)
    if current == desired:
        return
    if current:
        # Fail closed: do not silently override user-managed per-worktree excludes.
        raise RuntimeError(
            "core.excludesFile is already set for this worktree; refusing to override. "
            f"Current={current} Desired={desired}"
        )
    run_with_timeout(
        ["git", "config", "--worktree", "core.excludesFile", desired],
        cwd=checkout_path,
        capture_output=True,
        text=True,
        check=True,
        timeout_type="git_operations",
    )


def ensure_worktree_excludes(checkout_path: Path, patterns: Iterable[str]) -> bool:
    """Ensure patterns exist in a per-worktree excludes file.

    Returns:
        True if the exclude file changed.
    """
    required: List[str] = [str(p).strip() for p in patterns if str(p).strip()]
    if not required:
        return False

    git_dir = _git_dir_for_checkout(checkout_path)
    exclude_path = git_dir / "info" / "exclude.edison"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_core_excludes_file_configured(checkout_path=checkout_path, excludes_file=exclude_path)

    return ensure_lines_present(
        exclude_path,
        required,
        create=True,
        ensure_blank_line_before=True,
        ensure_trailing_newline=True,
    )


def cleanup_repo_info_exclude(checkout_path: Path, patterns_to_remove: Iterable[str]) -> bool:
    """Remove patterns from the repo-wide `.git/info/exclude` file.

    Edison previously wrote shared-path ignore patterns into `.git/info/exclude`,
    which is repo-wide and affects ALL worktrees (including the meta worktree).
    With per-worktree excludes enabled, those legacy patterns can prevent the meta
    branch from tracking meta-managed shared paths (e.g. `.claude/`).

    This helper is intentionally conservative:
    - It removes only exact lines that match the provided patterns (after stripping).
    - It preserves comments and unrelated user patterns.

    Returns:
        True if the file changed.
    """
    remove: Set[str] = {str(p).strip() for p in patterns_to_remove if str(p).strip()}
    if not remove:
        return False

    # Resolve the canonical info/exclude path for this checkout.
    cp = run_with_timeout(
        ["git", "rev-parse", "--path-format=absolute", "--git-path", "info/exclude"],
        cwd=checkout_path,
        capture_output=True,
        text=True,
        check=True,
        timeout_type="git_operations",
    )
    raw = (cp.stdout or "").strip()
    if not raw:
        return False
    path = Path(raw)
    if not path.is_absolute():
        path = (checkout_path / path).resolve()
    if not path.exists():
        return False

    before = path.read_text(encoding="utf-8").splitlines()
    after: List[str] = []
    changed = False
    for line in before:
        s = line.strip()
        if s and not s.startswith("#") and s in remove:
            changed = True
            continue
        after.append(line)

    if not changed:
        return False

    # Preserve trailing newline (git prefers it; also matches ensure_lines_present style).
    text = "\n".join(after).rstrip("\n") + "\n"
    path.write_text(text, encoding="utf-8")
    return True


__all__ = ["ensure_worktree_excludes", "cleanup_repo_info_exclude"]

