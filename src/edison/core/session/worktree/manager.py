"""Worktree creation and management operations."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from edison.core.utils.io import ensure_directory
from edison.core.utils.subprocess import run_with_timeout
from .config_helpers import _config, _resolve_worktree_target, _resolve_archive_directory
from .._utils import get_repo_dir
from edison.core.config.domains.project import ProjectConfig
from edison.core.utils.git.worktree import get_existing_worktree_path, get_worktree_parent, is_worktree_registered
import re as _re


def _shared_state_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    raw = cfg.get("sharedState")
    return raw if isinstance(raw, dict) else {}


def _parse_shared_paths(cfg: Dict[str, Any]) -> list[Dict[str, Any]]:
    """Parse `worktrees.sharedState.sharedPaths` into a normalized list of dicts."""
    ss = _shared_state_cfg(cfg)
    raw = ss.get("sharedPaths")
    if raw is None:
        return []
    if not isinstance(raw, list):
        return []

    out: list[Dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            path = item.strip()
            if not path:
                continue
            out.append(
                {
                    "path": path,
                    "scopes": ["session"],
                    "mergeExisting": True,
                    "targetRoot": "shared",
                    "type": "dir",
                }
            )
            continue

        if isinstance(item, dict):
            path = str(item.get("path") or "").strip()
            if not path:
                continue

            scopes_raw = item.get("scopes")
            if isinstance(scopes_raw, list) and scopes_raw:
                scopes = [str(s).strip().lower() for s in scopes_raw if str(s).strip()]
            else:
                scopes = ["session"]

            merge_existing = item.get("mergeExisting")
            if merge_existing is None:
                merge_existing = True
            merge_existing = bool(merge_existing)

            target_root = str(item.get("targetRoot") or "shared").strip().lower()
            if target_root not in {"shared", "primary"}:
                target_root = "shared"

            item_type = str(item.get("type") or "dir").strip().lower()
            if item_type not in {"dir", "file"}:
                item_type = "dir"

            out.append(
                {
                    "path": path,
                    "scopes": scopes,
                    "mergeExisting": merge_existing,
                    "targetRoot": target_root,
                    "type": item_type,
                }
            )
            continue

    return out


def _path_is_tracked(*, checkout_path: Path, rel_path: str) -> bool:
    """Return True if `rel_path` is tracked in the checkout's index."""
    try:
        cp = run_with_timeout(
            ["git", "ls-files", "-z", "--", rel_path],
            cwd=checkout_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=int(_config().get_worktree_timeout("health_check", 10)),
        )
        return bool((cp.stdout or "").strip())
    except Exception:
        return False


def _ensure_symlink_with_merge(
    *,
    link: Path,
    target: Path,
    item_type: str,
    merge_existing: bool,
) -> bool:
    """Ensure `link` is a symlink to `target`, optionally merging existing content."""
    try:
        if item_type == "dir":
            ensure_directory(target)
        else:
            ensure_directory(target.parent)

        if link.is_symlink():
            try:
                if link.resolve() == target.resolve():
                    return False
            except Exception:
                pass
            try:
                link.unlink()
            except Exception:
                return False

        if link.exists() and not link.is_symlink():
            if item_type == "dir" and link.is_dir():
                if merge_existing:
                    try:
                        for child in link.iterdir():
                            dest = target / child.name
                            if dest.exists():
                                continue
                            shutil.move(str(child), str(dest))
                    except Exception:
                        return False
                try:
                    shutil.rmtree(link, ignore_errors=True)
                except Exception:
                    return False
            elif item_type == "file" and link.is_file():
                if merge_existing and not target.exists():
                    try:
                        shutil.move(str(link), str(target))
                    except Exception:
                        return False
                else:
                    return False
            else:
                return False

        if not link.exists():
            link.parent.mkdir(parents=True, exist_ok=True)
            try:
                link.symlink_to(target, target_is_directory=(item_type == "dir"))
            except Exception:
                if item_type == "dir":
                    ensure_directory(link)
                return False
            return True
    except Exception:
        return False
    return False

def _ensure_checkout_git_excludes(*, checkout_path: Path, cfg: Dict[str, Any], scope: str) -> None:
    """Best-effort: ensure worktree-local git excludes for a checkout."""
    try:
        ss = _shared_state_cfg(cfg)
        ge = ss.get("gitExcludes")
        if not isinstance(ge, dict):
            return
        patterns = ge.get(scope)
        if not isinstance(patterns, list):
            return
        from edison.core.utils.git.excludes import ensure_worktree_excludes

        final: list[str] = [str(p) for p in patterns]

        # Automatically ignore configured shared paths in non-meta checkouts to avoid
        # untracked symlink noise (tracked changes are never ignored by excludes).
        if scope in {"primary", "session"}:
            for item in _parse_shared_paths(cfg):
                if scope not in set(item.get("scopes") or []):
                    continue
                p = str(item.get("path") or "").strip()
                if not p:
                    continue
                if str(item.get("type") or "dir").strip().lower() == "dir":
                    final.append(p.rstrip("/") + "/")
                else:
                    final.append(p)

        ensure_worktree_excludes(checkout_path, final)
    except Exception:
        # Avoid blocking worktree creation due to git exclude helpers.
        return


def _ensure_meta_commit_guard(*, meta_path: Path, cfg: Dict[str, Any]) -> None:
    """Best-effort: install a pre-commit hook in the meta worktree to keep it clean."""
    try:
        ss = _shared_state_cfg(cfg)
        guard = ss.get("commitGuard")
        if not isinstance(guard, dict):
            return
        if guard.get("enabled") is False:
            return
        allow = guard.get("allowPrefixes")
        if not isinstance(allow, list) or not [p for p in allow if str(p).strip()]:
            return

        def _bash_escape(s: str) -> str:
            return s.replace("\\", "\\\\").replace('"', '\\"')

        allow_prefixes = [str(p).strip() for p in allow if str(p).strip()]
        allow_block = "\n".join([f'  "{_bash_escape(p)}"' for p in allow_prefixes])

        meta_branch = str(ss.get("metaBranch") or "edison-meta").strip()
        meta_toplevel = str(meta_path.resolve())

        script = (
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "# EDISON_META_COMMIT_GUARD\n"
            f'META_BRANCH="{_bash_escape(meta_branch)}"\n'
            f'META_TOPLEVEL="{_bash_escape(meta_toplevel)}"\n'
            "\n"
            "current_branch=\"$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)\"\n"
            "current_toplevel=\"$(git rev-parse --show-toplevel 2>/dev/null || true)\"\n"
            "if [[ \"$current_branch\" != \"$META_BRANCH\" && \"$current_toplevel\" != \"$META_TOPLEVEL\" ]]; then\n"
            "  exit 0\n"
            "fi\n"
            "\n"
            "ALLOW_PREFIXES=(\n"
            f"{allow_block}\n"
            ")\n"
            "\n"
            "if ! command -v git >/dev/null 2>&1; then\n"
            "  exit 0\n"
            "fi\n"
            "\n"
            "bad=0\n"
            "while IFS= read -r path; do\n"
            "  [ -z \"$path\" ] && continue\n"
            "  allowed=0\n"
            "  for prefix in \"${ALLOW_PREFIXES[@]}\"; do\n"
            "    if [[ \"$path\" == \"$prefix\"* ]]; then\n"
            "      allowed=1\n"
            "      break\n"
            "    fi\n"
            "  done\n"
            "  if [[ $allowed -eq 0 ]]; then\n"
            "    echo \"Edison meta commit guard: refusing to commit '$path' outside allowed prefixes.\" >&2\n"
            "    bad=1\n"
            "  fi\n"
            "done < <(git diff --cached --name-only)\n"
            "\n"
            "if [[ $bad -ne 0 ]]; then\n"
            "  echo \"Allowed prefixes:\" >&2\n"
            "  for prefix in \"${ALLOW_PREFIXES[@]}\"; do\n"
            "    echo \"  - $prefix\" >&2\n"
            "  done\n"
            "  exit 1\n"
            "fi\n"
        )

        timeout = _config().get_worktree_timeout("health_check", 10)
        hook_cp = run_with_timeout(
            ["git", "rev-parse", "--path-format=absolute", "--git-path", "hooks/pre-commit"],
            cwd=meta_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        hook_path = Path((hook_cp.stdout or "").strip())
        if not hook_path.is_absolute():
            hook_path = (meta_path / hook_path).resolve()
        hook_path.parent.mkdir(parents=True, exist_ok=True)

        if hook_path.exists():
            try:
                existing = hook_path.read_text(encoding="utf-8", errors="ignore")
                if existing == script:
                    return
            except Exception:
                pass

        hook_path.write_text(script, encoding="utf-8")
        try:
            hook_path.chmod(0o755)
        except Exception:
            pass
    except Exception:
        return


def _ensure_meta_worktree_setup(*, meta_path: Path, cfg: Dict[str, Any]) -> None:
    """Best-effort: apply meta worktree-only config (excludes + commit guard)."""
    _ensure_checkout_git_excludes(checkout_path=meta_path, cfg=cfg, scope="meta")
    _ensure_meta_commit_guard(meta_path=meta_path, cfg=cfg)


def _create_orphan_branch(*, repo_dir: Path, branch: str, timeout: int) -> str:
    """Create an orphan branch with a single empty root commit, without checking it out."""
    empty_tree = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    cp = run_with_timeout(
        ["git", "commit-tree", empty_tree, "-m", "Initialize Edison meta branch"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
    )
    sha = (cp.stdout or "").strip()
    if not sha:
        raise RuntimeError(f"Failed to create orphan commit for branch {branch}")
    run_with_timeout(
        ["git", "update-ref", f"refs/heads/{branch}", sha],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
        timeout=timeout,
    )
    return sha


def _resolve_meta_worktree_path(*, cfg: Dict[str, Any], repo_dir: Path) -> Path:
    """Resolve meta worktree path from config.

    Anchoring matches other worktree paths: relative paths are anchored to the repo root.
    """
    ss = _shared_state_cfg(cfg)
    raw = ss.get("metaPathTemplate") or "../{PROJECT_NAME}-worktrees/_meta"
    substituted = ProjectConfig(repo_root=repo_dir).substitute_project_tokens(str(raw))
    p = Path(substituted)
    if p.is_absolute():
        return p
    return (repo_dir / p).resolve()


def _ensure_meta_worktree(*, repo_dir: Path, cfg: Dict[str, Any], dry_run: bool = False) -> tuple[Path, str, bool]:
    """Ensure the shared-state meta worktree exists and return (path, branch, created)."""
    ss = _shared_state_cfg(cfg)
    branch = str(ss.get("metaBranch") or "edison-meta")

    primary_repo_dir = get_worktree_parent(repo_dir) or repo_dir
    meta_path = _resolve_meta_worktree_path(cfg=cfg, repo_dir=primary_repo_dir)

    # If we're already inside the meta worktree, treat it as existing.
    try:
        if meta_path.resolve() == Path(repo_dir).resolve():
            return meta_path, branch, False
    except Exception:
        pass

    if dry_run:
        return meta_path, branch, False

    timeout_add = int(_config().get_worktree_timeout("worktree_add", 30))
    timeout_health = int(_config().get_worktree_timeout("health_check", 10))

    # If the path exists, require it to be a git checkout (avoid clobbering).
    if meta_path.exists():
        try:
            if is_worktree_registered(meta_path, repo_root=primary_repo_dir):
                return meta_path, branch, False
        except Exception:
            pass
        try:
            cp = run_with_timeout(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=meta_path,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout_health,
            )
            if (cp.stdout or "").strip() != "true":
                raise RuntimeError(f"Meta worktree path exists but is not a git worktree: {meta_path}")
        except Exception as e:
            raise RuntimeError(f"Meta worktree path exists but is not usable: {meta_path} ({e})")
        raise RuntimeError(
            "Meta worktree path exists but is not registered for this repository. "
            f"Path: {meta_path}. "
            "Set worktrees.sharedState.metaPathTemplate to a repo-unique location."
        )

    # Create (or attach) meta worktree without switching the primary checkout.
    created = False
    try:
        # If branch exists, attach it; else create it at the configured base ref.
        show = run_with_timeout(
            ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
            cwd=primary_repo_dir,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_health,
        )
        if show.returncode == 0:
            run_with_timeout(
                ["git", "worktree", "add", str(meta_path), branch],
                cwd=primary_repo_dir,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout_add,
            )
        else:
            _create_orphan_branch(repo_dir=primary_repo_dir, branch=branch, timeout=timeout_health)
            run_with_timeout(
                ["git", "worktree", "add", str(meta_path), branch],
                cwd=primary_repo_dir,
                capture_output=True,
                text=True,
                check=True,
                timeout=timeout_add,
            )
            created = True
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        stdout = (exc.stdout or "").strip()
        # Idempotency: if it's already registered, treat as success.
        if "already exists" in stderr or "already exists" in stdout or "is already checked out" in stderr:
            try:
                if is_worktree_registered(meta_path, repo_root=primary_repo_dir):
                    return meta_path, branch, False
            except Exception:
                pass
            raise RuntimeError(
                "Meta worktree path already exists but is not registered for this repository. "
                f"Path: {meta_path}. "
                "Set worktrees.sharedState.metaPathTemplate to a repo-unique location."
            ) from exc
        raise RuntimeError(f"Failed to create meta worktree at {meta_path}: {stderr or stdout}") from exc

    return meta_path, branch, created


def _resolve_shared_root(*, repo_dir: Path, cfg: Dict[str, Any]) -> Path:
    """Resolve the filesystem root used for shared Edison state."""
    ss = _shared_state_cfg(cfg)
    mode = str(ss.get("mode") or "meta").strip().lower()

    if mode == "primary":
        return get_worktree_parent(repo_dir) or repo_dir

    if mode == "external":
        raw = ss.get("externalPath")
        if not raw:
            raise RuntimeError("worktrees.sharedState.mode=external requires worktrees.sharedState.externalPath")
        p = Path(str(raw))
        if not p.is_absolute():
            p = ((get_worktree_parent(repo_dir) or repo_dir) / p).resolve()
        return p

    # Default: meta
    meta_path, _, _ = _ensure_meta_worktree(repo_dir=repo_dir, cfg=cfg, dry_run=False)
    _ensure_meta_worktree_setup(meta_path=meta_path, cfg=cfg)
    return meta_path


def get_meta_worktree_status(*, repo_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Return computed status for the shared-state meta worktree without creating it."""
    root = repo_dir or get_repo_dir()
    cfg = _config().get_worktree_config()
    ss = _shared_state_cfg(cfg)
    mode = str(ss.get("mode") or "meta").strip().lower()

    primary_repo_dir = get_worktree_parent(root) or root
    meta_path = _resolve_meta_worktree_path(cfg=cfg, repo_dir=primary_repo_dir)
    branch = str(ss.get("metaBranch") or "edison-meta")

    exists = meta_path.exists()
    registered = False
    if exists:
        try:
            registered = is_worktree_registered(meta_path, repo_root=primary_repo_dir)
        except Exception:
            registered = False

    return {
        "mode": mode,
        "primary_repo_dir": str(primary_repo_dir),
        "meta_path": str(meta_path),
        "meta_branch": branch,
        "exists": exists,
        "registered": registered,
    }


def ensure_meta_worktree(*, repo_dir: Optional[Path] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Ensure the shared-state meta worktree exists (when mode=meta) and return status."""
    root = repo_dir or get_repo_dir()
    cfg = _config().get_worktree_config()
    ss = _shared_state_cfg(cfg)
    mode = str(ss.get("mode") or "meta").strip().lower()

    status = get_meta_worktree_status(repo_dir=root)
    if mode != "meta":
        status["created"] = False
        return status

    meta_path, branch, created = _ensure_meta_worktree(repo_dir=root, cfg=cfg, dry_run=dry_run)
    if not dry_run:
        _ensure_meta_worktree_setup(meta_path=meta_path, cfg=cfg)
    status.update(
        {
            "meta_path": str(meta_path),
            "meta_branch": str(branch),
            "created": bool(created),
            "exists": meta_path.exists(),
            "registered": is_worktree_registered(meta_path, repo_root=get_worktree_parent(root) or root)
            if meta_path.exists()
            else False,
        }
    )
    return status


def initialize_meta_shared_state(*, repo_dir: Optional[Path] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Initialize meta-shared state for primary + existing worktrees.

    Ensures:
    - meta worktree exists (mode=meta)
    - primary checkout `.project/*` management subdirs are symlinked to the shared root
    - worktree-local git excludes are written for primary + session worktrees
    """
    root = repo_dir or get_repo_dir()
    cfg = _config().get_worktree_config()
    ss = _shared_state_cfg(cfg)
    mode = str(ss.get("mode") or "meta").strip().lower()

    status = ensure_meta_worktree(repo_dir=root, dry_run=dry_run)
    status["mode"] = mode
    if mode != "meta":
        return status

    primary_repo_dir = Path(status["primary_repo_dir"])
    meta_path = Path(status["meta_path"])

    if dry_run:
        status.update(
            {
                "primary_links_updated": 0,
                "shared_paths_primary_updated": 0,
                "shared_paths_primary_skipped_tracked": 0,
                "shared_paths_session_updated": 0,
                "shared_paths_session_skipped_tracked": 0,
                "session_worktrees_updated": 0,
                "primary_excludes_updated": False,
            }
        )
        return status

    # Link primary management dirs into the shared root.
    subdirs = ss.get("managementSubdirs")
    if not isinstance(subdirs, list) or not subdirs:
        subdirs = ["sessions", "tasks", "qa", "logs", "archive"]
    primary_links_updated = 0
    for subdir in [str(s) for s in subdirs if str(s).strip()]:
        before = (primary_repo_dir / ".project" / subdir)
        was_link = before.is_symlink()
        _ensure_shared_management_subdir(worktree_path=primary_repo_dir, repo_dir=primary_repo_dir, subdir=subdir)
        after = (primary_repo_dir / ".project" / subdir)
        if after.is_symlink() and (not was_link or after.resolve() == (meta_path / ".project" / subdir).resolve()):
            primary_links_updated += 1

    primary_shared_updated, primary_shared_skipped_tracked = _ensure_shared_paths_in_checkout(
        checkout_path=primary_repo_dir,
        repo_dir=primary_repo_dir,
        cfg=cfg,
        scope="primary",
    )

    _ensure_checkout_git_excludes(checkout_path=primary_repo_dir, cfg=cfg, scope="primary")

    # Apply excludes to all non-primary/non-meta worktrees as "session" checkouts.
    session_updated = 0
    session_shared_updated = 0
    session_shared_skipped_tracked = 0
    try:
        cp = run_with_timeout(
            ["git", "worktree", "list", "--porcelain"],
            cwd=primary_repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=_config().get_worktree_timeout("health_check", 10),
        )
        current: Optional[Path] = None
        for line in (cp.stdout or "").splitlines():
            if line.startswith("worktree "):
                current = Path(line.split(" ", 1)[1].strip())
                continue
            if not line.strip():
                current = None
                continue
            if current is None:
                continue
            # Only act once per worktree stanza.
            if line.startswith("HEAD "):
                p = current.resolve()
                if p == primary_repo_dir.resolve() or p == meta_path.resolve():
                    continue
                su, ss_tracked = _ensure_shared_paths_in_checkout(
                    checkout_path=p,
                    repo_dir=p,
                    cfg=cfg,
                    scope="session",
                )
                session_shared_updated += su
                session_shared_skipped_tracked += ss_tracked
                _ensure_checkout_git_excludes(checkout_path=p, cfg=cfg, scope="session")
                session_updated += 1
    except Exception:
        session_updated = 0

    status.update(
        {
            "primary_links_updated": int(primary_links_updated),
            "shared_paths_primary_updated": int(primary_shared_updated),
            "shared_paths_primary_skipped_tracked": int(primary_shared_skipped_tracked),
            "shared_paths_session_updated": int(session_shared_updated),
            "shared_paths_session_skipped_tracked": int(session_shared_skipped_tracked),
            "session_worktrees_updated": int(session_updated),
            "primary_excludes_updated": True,
        }
    )
    return status


def recreate_meta_shared_state(
    *,
    repo_dir: Optional[Path] = None,
    force: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Recreate the meta branch/worktree as an orphan branch, preserving configured shared state."""
    root = repo_dir or get_repo_dir()
    cfg = _config().get_worktree_config()
    ss = _shared_state_cfg(cfg)
    mode = str(ss.get("mode") or "meta").strip().lower()

    status = get_meta_worktree_status(repo_dir=root)
    status["mode"] = mode
    if mode != "meta":
        return status

    primary_repo_dir = Path(status["primary_repo_dir"])
    meta_path = Path(status["meta_path"])
    branch = str(status["meta_branch"])

    if dry_run:
        status["recreated"] = True
        return status

    subdirs = ss.get("managementSubdirs")
    if not isinstance(subdirs, list) or not subdirs:
        subdirs = ["sessions", "tasks", "qa", "logs", "archive"]
    subdirs = [str(s).strip() for s in subdirs if str(s).strip()]

    shared_paths = [p for p in _parse_shared_paths(cfg) if str(p.get("targetRoot") or "shared").lower() == "shared"]

    # Refuse to recreate if the meta branch is checked out in other worktrees.
    cp = run_with_timeout(
        ["git", "worktree", "list", "--porcelain"],
        cwd=primary_repo_dir,
        capture_output=True,
        text=True,
        check=True,
        timeout=int(_config().get_worktree_timeout("health_check", 10)),
    )
    current: Optional[Path] = None
    current_branch: Optional[str] = None
    for line in (cp.stdout or "").splitlines():
        if line.startswith("worktree "):
            current = Path(line.split(" ", 1)[1].strip())
            current_branch = None
            continue
        if line.startswith("branch "):
            current_branch = line.split(" ", 1)[1].strip()
            continue
        if not line.strip():
            if current is not None and current_branch == f"refs/heads/{branch}":
                p = current.resolve()
                if p != meta_path.resolve():
                    raise RuntimeError(f"Refusing to recreate meta branch; it is checked out elsewhere: {p}")
            current = None
            current_branch = None

    snapshot_dir: Optional[Path] = None

    if meta_path.exists():
        if not is_worktree_registered(meta_path, repo_root=primary_repo_dir):
            raise RuntimeError(
                "Meta path exists but is not a registered worktree; refusing to recreate. "
                f"Path: {meta_path}"
            )

        # Fail closed if the meta branch currently tracks files outside the preserved prefixes.
        tracked_allowed = [".project/"]
        for item in shared_paths:
            raw = str(item.get("path") or "").strip()
            if not raw:
                continue
            tracked_allowed.append(raw.rstrip("/") + "/")
            tracked_allowed.append(raw.rstrip("/"))
        try:
            ls = run_with_timeout(
                ["git", "ls-tree", "-r", "--name-only", "HEAD"],
                cwd=meta_path,
                capture_output=True,
                text=True,
                check=True,
                timeout=int(_config().get_worktree_timeout("health_check", 10)),
            )
            tracked_files = [p.strip() for p in (ls.stdout or "").splitlines() if p.strip()]
            unexpected = [
                p
                for p in tracked_files
                if not any(p.startswith(prefix) for prefix in tracked_allowed)
            ]
            if unexpected and not force:
                sample = ", ".join(unexpected[:10])
                raise RuntimeError(
                    "Refusing to recreate meta branch because it tracks files outside the preserved prefixes. "
                    f"Count={len(unexpected)}. Sample: {sample}. "
                    "Add paths to worktrees.sharedState.sharedPaths or re-run with --force to discard."
                )
        except RuntimeError:
            raise
        except Exception:
            # If we can't reliably inspect tracked files, fail closed.
            raise RuntimeError("Failed to inspect tracked files in meta worktree; refusing to recreate.")

        # Fail closed if there are local changes outside of the shared state we will preserve.
        allowed_prefixes = [".project/", ".edison/_generated/"]
        for item in shared_paths:
            raw = str(item.get("path") or "").strip()
            if not raw:
                continue
            allowed_prefixes.append(raw.rstrip("/") + "/")
            allowed_prefixes.append(raw.rstrip("/"))

        st = run_with_timeout(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=meta_path,
            capture_output=True,
            text=True,
            check=True,
            timeout=int(_config().get_worktree_timeout("health_check", 10)),
        )
        unsafe: list[str] = []
        for line in (st.stdout or "").splitlines():
            if not line.strip():
                continue
            path_part = line[3:].strip()
            for part in [p.strip() for p in path_part.split(" -> ") if p.strip()]:
                if not any(part.startswith(prefix) for prefix in allowed_prefixes):
                    unsafe.append(part)
        if unsafe and not force:
            raise RuntimeError(
                "Refusing to recreate meta worktree with local changes outside shared state. "
                f"Re-run with --force to discard: {', '.join(sorted(set(unsafe)))}"
            )

        # Snapshot shared state before removal to avoid data loss.
        snapshot_dir = Path(tempfile.mkdtemp(prefix="edison-meta-shared-state-"))
        try:
            for subdir in subdirs:
                src = meta_path / ".project" / subdir
                if not src.exists():
                    continue
                dest = snapshot_dir / ".project" / subdir
                if src.is_dir():
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)

            for item in shared_paths:
                raw = str(item.get("path") or "").strip()
                if not raw:
                    continue
                p = Path(raw)
                if p.is_absolute() or ".." in p.parts:
                    continue
                src = meta_path / str(p)
                if not src.exists():
                    continue
                dest = snapshot_dir / str(p)
                if src.is_dir():
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                else:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dest)
        except Exception:
            shutil.rmtree(snapshot_dir, ignore_errors=True)
            raise

        run_with_timeout(
            ["git", "worktree", "remove", "--force", str(meta_path)],
            cwd=primary_repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=int(_config().get_worktree_timeout("worktree_add", 30)),
        )

    show = run_with_timeout(
        ["git", "show-ref", "--verify", f"refs/heads/{branch}"],
        cwd=primary_repo_dir,
        capture_output=True,
        text=True,
        check=False,
        timeout=int(_config().get_worktree_timeout("health_check", 10)),
    )
    if show.returncode == 0:
        run_with_timeout(
            ["git", "update-ref", "-d", f"refs/heads/{branch}"],
            cwd=primary_repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=int(_config().get_worktree_timeout("health_check", 10)),
        )

    _create_orphan_branch(repo_dir=primary_repo_dir, branch=branch, timeout=int(_config().get_worktree_timeout("health_check", 10)))
    run_with_timeout(
        ["git", "worktree", "add", str(meta_path), branch],
        cwd=primary_repo_dir,
        capture_output=True,
        text=True,
        check=True,
        timeout=int(_config().get_worktree_timeout("worktree_add", 30)),
    )
    _ensure_meta_worktree_setup(meta_path=meta_path, cfg=cfg)

    if snapshot_dir is not None:
        try:
            shutil.copytree(snapshot_dir, meta_path, dirs_exist_ok=True)
        finally:
            shutil.rmtree(snapshot_dir, ignore_errors=True)

    init = initialize_meta_shared_state(repo_dir=primary_repo_dir, dry_run=False)
    init["recreated"] = True
    return init


def _ensure_shared_paths_in_checkout(
    *,
    checkout_path: Path,
    repo_dir: Path,
    cfg: Dict[str, Any],
    scope: str,
) -> tuple[int, int]:
    """Ensure configured shared paths exist as symlinks in the checkout.

    Returns (updated_count, skipped_tracked_count).
    """
    updated = 0
    skipped_tracked = 0

    for item in _parse_shared_paths(cfg):
        scopes = set(item.get("scopes") or [])
        if scope not in scopes:
            continue

        raw = str(item.get("path") or "").strip()
        if not raw:
            continue
        p = Path(raw)
        if p.is_absolute() or ".." in p.parts:
            continue
        rel = str(p)

        if _path_is_tracked(checkout_path=checkout_path, rel_path=rel):
            skipped_tracked += 1
            continue

        item_type = str(item.get("type") or "dir").strip().lower()
        merge_existing = bool(item.get("mergeExisting", True))
        target_root = str(item.get("targetRoot") or "shared").strip().lower()
        if target_root == "primary":
            shared_root = get_worktree_parent(repo_dir) or repo_dir
        else:
            shared_root = _resolve_shared_root(repo_dir=repo_dir, cfg=cfg)

        link = checkout_path / rel
        target = Path(shared_root) / rel
        if _ensure_symlink_with_merge(link=link, target=target, item_type=item_type, merge_existing=merge_existing):
            updated += 1

    return updated, skipped_tracked


def _ensure_shared_management_subdir(
    *,
    worktree_path: Path,
    repo_dir: Path,
    subdir: str,
) -> None:
    """Ensure a management subdirectory is shared across git worktrees.

    Git worktrees do not share untracked files. Edison stores local-first management state
    under `<project-management-dir>/*` (sessions, tasks, QA, logs, archive). Each session worktree
    therefore gets a symlink pointing to the primary checkout's directory.

    Best-effort behavior:
    - If a real directory exists in the worktree, attempt to merge its children into the shared
      directory, then replace it with a symlink.
    - Never raise; worktree creation must not be blocked by linking failures.
    """
    try:
        from edison.core.utils.paths.management import ProjectManagementPaths

        cfg = _config().get_worktree_config()
        shared_root = _resolve_shared_root(repo_dir=repo_dir, cfg=cfg)
        mgmt_dir_name = ProjectManagementPaths(shared_root).get_management_root().name
        shared = (shared_root / mgmt_dir_name / subdir).resolve()
        ensure_directory(shared)

        project_dir = worktree_path / mgmt_dir_name
        ensure_directory(project_dir)

        link = project_dir / subdir
        _ensure_symlink_with_merge(link=link, target=shared, item_type="dir", merge_existing=True)
    except Exception:
        # Never block worktree creation on best-effort linking.
        return


def _ensure_shared_project_management_dirs(*, worktree_path: Path, repo_dir: Path) -> None:
    """Ensure project management state is shared across git worktrees."""
    cfg = _config().get_worktree_config()
    ss = _shared_state_cfg(cfg)
    subdirs = ss.get("managementSubdirs")
    if not isinstance(subdirs, list) or not subdirs:
        subdirs = ["sessions", "tasks", "qa", "logs", "archive"]
    for subdir in [str(s) for s in subdirs if str(s).strip()]:
        _ensure_shared_management_subdir(worktree_path=worktree_path, repo_dir=repo_dir, subdir=subdir)


def _ensure_shared_project_generated_dir(*, worktree_path: Path, repo_dir: Path) -> None:
    """Ensure `<project-config-dir>/_generated` is shared across git worktrees.

    Start prompts and constitutions reference composed artifacts under `_generated`. Git worktrees
    do not share untracked files, so worktrees must link to the primary checkout's generated dir.
    """
    try:
        from edison.core.utils.paths.project import get_project_config_dir

        cfg = _config().get_worktree_config()
        ss = _shared_state_cfg(cfg)
        if ss.get("shareGenerated") is False:
            return

        gen_source = str(ss.get("generatedSource") or "primary").strip().lower()
        if gen_source == "shared":
            shared_root = _resolve_shared_root(repo_dir=repo_dir, cfg=cfg)
        else:
            # Default: keep composed artifacts centralized in the primary checkout.
            shared_root = get_worktree_parent(repo_dir) or repo_dir
        cfg_dir = get_project_config_dir(shared_root, create=True)
        shared = (cfg_dir / "_generated").resolve()
        ensure_directory(shared)

        worktree_cfg_dir = worktree_path / cfg_dir.name
        ensure_directory(worktree_cfg_dir)

        link = worktree_cfg_dir / "_generated"
        _ensure_symlink_with_merge(link=link, target=shared, item_type="dir", merge_existing=True)
    except Exception:
        return


def _ensure_worktree_session_id_file(*, worktree_path: Path, session_id: str) -> None:
    """Ensure `<project-management-dir>/.session-id` exists inside the worktree.

    This enables worktree-local session auto-resolution (e.g. `edison session status`
    without passing `--session` or setting env vars) by allowing the canonical resolver
    to read the session id from the worktree's management root.
    """
    try:
        from edison.core.utils.paths import PathResolver
        from edison.core.utils.paths.management import ProjectManagementPaths

        repo_root = PathResolver.resolve_project_root()
        mgmt_dir_name = ProjectManagementPaths(repo_root).get_management_root().name
        project_dir = worktree_path / mgmt_dir_name
        ensure_directory(project_dir)
        target = project_dir / ".session-id"
        try:
            if target.exists() and target.read_text(encoding="utf-8").strip() == session_id:
                return
        except Exception:
            pass
        target.write_text(session_id + "\n", encoding="utf-8")
    except Exception:
        # Never block worktree creation on best-effort session id persistence.
        return


def _primary_head_marker(repo_dir: Path) -> str:
    """Return a stable marker for the primary worktree HEAD.

    Worktree operations must never switch the branch (or detached HEAD) of the
    primary worktree. This marker is used to assert that invariant.
    """
    timeout = _config().get_worktree_timeout("branch_check", 10)
    try:
        cp = run_with_timeout(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        ref = (cp.stdout or "").strip()
        if ref and ref != "HEAD":
            return ref
    except Exception:
        pass
    try:
        cp2 = run_with_timeout(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        sha = (cp2.stdout or "").strip()
        return f"DETACHED@{sha}" if sha else "DETACHED"
    except Exception:
        return "UNKNOWN"


def _resolve_current_base_ref(repo_dir: Path) -> str:
    """Resolve the base ref for baseBranchMode=current without mutating git state."""
    marker = _primary_head_marker(repo_dir)
    if marker.startswith("DETACHED@"):
        return marker.split("@", 1)[1]
    if marker in {"UNKNOWN", "DETACHED"}:
        return "HEAD"
    return marker


def _resolve_start_ref(repo_dir: Path, base_ref: str, *, timeout: int) -> str:
    """Resolve a start ref that can be passed to `git worktree add`.

    Accepts branch names, remote branches, SHAs, and HEAD.
    """

    def _rev_parse_ok(ref: str) -> bool:
        rr = run_with_timeout(
            ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
            cwd=repo_dir,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return rr.returncode == 0

    if _rev_parse_ok(base_ref):
        return base_ref

    # Try origin/<ref> without requiring a local checkout.
    if base_ref not in {"HEAD"} and not base_ref.startswith(("origin/", "refs/")):
        candidate = f"origin/{base_ref}"
        if _rev_parse_ok(candidate):
            return candidate

    raise RuntimeError(f"Base ref not found: {base_ref}")


def resolve_worktree_base_ref(*, repo_dir: Path, cfg: Dict[str, Any], override: Optional[str] = None) -> str:
    """Resolve the logical base ref for session worktree creation.

    - If override is provided, it wins.
    - If cfg.baseBranchMode == "fixed", baseBranch is used (fallback: "main").
    - Otherwise, the current primary worktree HEAD ref is used.

    The returned ref is the value that should be recorded into session git metadata
    as `baseBranch` for stable downstream diffs and evidence.
    """
    if override:
        return str(override)
    mode_raw = cfg.get("baseBranchMode")
    if mode_raw:
        base_mode = str(mode_raw)
    else:
        # Backward-compatible inference:
        # - if a baseBranch is explicitly configured, treat it as fixed
        # - otherwise default to current primary HEAD
        base_mode = "fixed" if cfg.get("baseBranch") not in (None, "") else "current"
    if base_mode == "fixed":
        return str(cfg.get("baseBranch") or "main")
    return _resolve_current_base_ref(repo_dir)


def resolve_worktree_target(session_id: str) -> tuple[Path, str]:
    """Public helper to compute target path/branch using current config."""
    cfg = _config().get_worktree_config()
    return _resolve_worktree_target(session_id, cfg)


def create_worktree(
    session_id: str,
    base_branch: Optional[str] = None,
    install_deps: Optional[bool] = None,
    dry_run: bool = False,
) -> tuple[Optional[Path], Optional[str]]:
    """Create git worktree for session.

    When ``dry_run`` is True, only compute the target path/branch and return
    without mutating git state.
    """
    repo_dir = get_repo_dir()
    config_obj = _config()
    config = config_obj.get_worktree_config()
    if not config.get("enabled", False):
        return (None, None)

    def _maybe_align_primary_shared_state() -> None:
        try:
            ss = _shared_state_cfg(config)
            mode = str(ss.get("mode") or "meta").strip().lower()
            if mode != "meta":
                return
            primary_repo_dir = get_worktree_parent(repo_dir) or repo_dir
            _ensure_shared_project_management_dirs(worktree_path=primary_repo_dir, repo_dir=primary_repo_dir)
            _ensure_shared_paths_in_checkout(
                checkout_path=primary_repo_dir,
                repo_dir=primary_repo_dir,
                cfg=config,
                scope="primary",
            )
            _ensure_checkout_git_excludes(checkout_path=primary_repo_dir, cfg=config, scope="primary")
        except Exception:
            return

    worktree_path, branch_name = _resolve_worktree_target(session_id, config)
    base_branch_value = resolve_worktree_base_ref(repo_dir=repo_dir, cfg=config, override=base_branch)

    existing_wt = get_existing_worktree_path(branch_name)
    if existing_wt is not None:
        resolved = existing_wt.resolve()
        if not dry_run:
            _ensure_shared_project_management_dirs(worktree_path=resolved, repo_dir=repo_dir)
            _ensure_shared_project_generated_dir(worktree_path=resolved, repo_dir=repo_dir)
            _ensure_shared_paths_in_checkout(checkout_path=resolved, repo_dir=repo_dir, cfg=config, scope="session")
            _ensure_worktree_session_id_file(worktree_path=resolved, session_id=session_id)
            _ensure_checkout_git_excludes(checkout_path=resolved, cfg=config, scope="session")
            _maybe_align_primary_shared_state()
        return (resolved, branch_name)

    # Fail fast when repo has no commits (unborn HEAD) to avoid claiming metadata
    try:
        hc = run_with_timeout(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
            timeout=config_obj.get_worktree_timeout("health_check", 10),
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("Repository has no commits; cannot create worktree") from exc

    if dry_run:
        return (worktree_path, branch_name)

    try:
        # If the configured target exists and is non-empty, choose a sibling path
        # (never fall back to hardcoded directories).
        if worktree_path.exists() and any(worktree_path.iterdir()):
            suffix_length = config_obj.get_worktree_uuid_suffix_length()
            base_parent = worktree_path.parent
            base_name = worktree_path.name
            # Avoid infinite loops if collisions persist
            for _ in range(5):
                candidate = base_parent / f"{base_name}-{uuid.uuid4().hex[:suffix_length]}"
                if not candidate.exists():
                    worktree_path = candidate
                    break
                if not any(candidate.iterdir()):
                    worktree_path = candidate
                    break
    except Exception:
        # Best effort only; the subsequent git command will fail with a clear error.
        pass

    base_dir_full = worktree_path.parent
    ensure_directory(base_dir_full)

    last_err: Optional[Exception] = None

    # Timeouts
    t_fetch = config_obj.get_worktree_timeout("fetch", 60)
    t_add = config_obj.get_worktree_timeout("worktree_add", 30)
    t_install = config_obj.get_worktree_timeout("install", 300)
    t_health = config_obj.get_worktree_timeout("health_check", 10)
    t_branch = config_obj.get_worktree_timeout("branch_check", 10)

    primary_before = _primary_head_marker(repo_dir)

    def _ref_exists(ref: str) -> bool:
        rr = run_with_timeout(
            ["git", "show-ref", "--verify", ref],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=config_obj.get_worktree_timeout("branch_check", 10),
        )
        return rr.returncode == 0

    # Resolve the base ref without mutating the primary checkout (do not checkout/pull).
    start_ref = _resolve_start_ref(repo_dir, base_branch_value, timeout=t_branch)

    for attempt in range(2):
        try:
            run_with_timeout(["git", "fetch", "--all", "--prune"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=t_fetch)

            branch_ref = f"refs/heads/{branch_name}"
            if _ref_exists(branch_ref):
                run_with_timeout(
                    ["git", "worktree", "add", "--", str(worktree_path), branch_name],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=t_add,
                )
            else:
                run_with_timeout(
                    ["git", "worktree", "add", "-b", branch_name, "--", str(worktree_path), start_ref],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=t_add,
                )
            break
        except subprocess.CalledProcessError as e:
            last_err = e
            run_with_timeout(["git", "worktree", "prune"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=config_obj.get_worktree_timeout("prune", 10))
            run_with_timeout(["git", "fetch", "--all", "--prune"], cwd=repo_dir, check=False, capture_output=True, text=True, timeout=t_fetch)
    if last_err is not None:
        raise RuntimeError(f"Failed to create worktree after retries: {last_err}")

    install_flag = config.get("installDeps", False) if install_deps is None else bool(install_deps)
    if install_flag:
        def _resolve_install_cmd(cwd: Path) -> list[str]:
            """Pick an install command that avoids mutating lockfiles.

            Session worktrees are meant to isolate code changes. A plain
            package-manager install can normalize or rewrite lockfiles, creating
            noisy diffs and triggering unrelated security/audit validation.
            """
            if (cwd / "pnpm-lock.yaml").exists():
                return ["pnpm", "install", "--frozen-lockfile"]
            if (cwd / "package-lock.json").exists():
                return ["npm", "ci"]
            if (cwd / "yarn.lock").exists():
                return ["yarn", "install", "--immutable"]
            if (cwd / "bun.lockb").exists() or (cwd / "bun.lock").exists():
                return ["bun", "install", "--frozen-lockfile"]
            # Best-effort fallback: keep previous behavior.
            return ["pnpm", "install"]

        def _resolve_fallback_install_cmd(cwd: Path) -> list[str] | None:
            """Fallback install command when immutable install is insufficient.

            Used when post-install commands fail due to missing binaries/build artefacts.
            """
            if (cwd / "pnpm-lock.yaml").exists():
                return ["pnpm", "install"]
            if (cwd / "package-lock.json").exists():
                return ["npm", "install"]
            if (cwd / "yarn.lock").exists():
                return ["yarn", "install"]
            if (cwd / "bun.lockb").exists() or (cwd / "bun.lock").exists():
                return ["bun", "install"]
            return None

        def _run_install(cmd: list[str]) -> subprocess.CompletedProcess[str] | None:
            try:
                return run_with_timeout(
                    cmd,
                    cwd=worktree_path,
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=t_install,
                )
            except Exception:
                return None

        install_cmd = _resolve_install_cmd(worktree_path)
        fallback_cmd = _resolve_fallback_install_cmd(worktree_path)
        used_fallback = False

        result = _run_install(install_cmd)
        if fallback_cmd and (result is None or getattr(result, "returncode", 1) != 0):
            used_fallback = True
            _run_install(fallback_cmd)

        post_install = config.get("postInstallCommands", []) or []
        if isinstance(post_install, list) and post_install:
            commands = [str(c) for c in post_install if str(c).strip()]
            try:
                _run_post_install_commands(
                    worktree_path=worktree_path,
                    commands=commands,
                    timeout=t_install,
                )
            except Exception:
                # If immutable install didn't materialize enough for post-install steps,
                # retry once with a best-effort install command.
                if fallback_cmd and not used_fallback and fallback_cmd != install_cmd:
                    used_fallback = True
                    _run_install(fallback_cmd)
                    _run_post_install_commands(
                        worktree_path=worktree_path,
                        commands=commands,
                        timeout=t_install,
                    )
                else:
                    raise

    try:
        hc1 = run_with_timeout(["git", "rev-parse", "--is-inside-work-tree"], cwd=worktree_path, capture_output=True, text=True, check=True, timeout=t_health)
        hc2 = run_with_timeout(["git", "branch", "--show-current"], cwd=worktree_path, capture_output=True, text=True, check=True, timeout=t_health)
        if (hc1.stdout or "").strip() != "true" or (hc2.stdout or "").strip() != branch_name:
            raise RuntimeError("Worktree health check failed")

        git_file = worktree_path / ".git"
        if not git_file.exists():
            raise RuntimeError("Worktree missing .git metadata")
        if not git_file.is_file():
            raise RuntimeError("Expected a git worktree (.git must be a file), but got a non-worktree checkout")

        content = git_file.read_text(encoding="utf-8", errors="ignore")
        if "gitdir:" not in content:
            raise RuntimeError("Worktree .git file is missing gitdir pointer")
        target_raw = content.split("gitdir:", 1)[1].strip()
        target_path = Path(target_raw)
        if not target_path.is_absolute():
            target_path = (worktree_path / target_path).resolve()
        if not target_path.exists():
            raise RuntimeError(f"Worktree .git pointer is invalid: {target_raw}")
    except Exception as e:
        raise RuntimeError(f"Worktree health checks failed: {e}")

    _ensure_shared_project_management_dirs(worktree_path=worktree_path, repo_dir=repo_dir)
    _ensure_shared_project_generated_dir(worktree_path=worktree_path, repo_dir=repo_dir)
    _ensure_shared_paths_in_checkout(checkout_path=worktree_path, repo_dir=repo_dir, cfg=config, scope="session")
    _ensure_worktree_session_id_file(worktree_path=worktree_path, session_id=session_id)
    _ensure_checkout_git_excludes(checkout_path=worktree_path, cfg=config, scope="session")
    _maybe_align_primary_shared_state()

    primary_after = _primary_head_marker(repo_dir)
    if primary_before != primary_after:
        raise RuntimeError(
            f"Primary worktree HEAD changed during worktree creation: {primary_before} -> {primary_after}"
        )

    return (worktree_path, branch_name)


def _run_post_install_commands(*, worktree_path: Path, commands: list[str], timeout: int) -> None:
    """Run project-configured post-install commands inside the worktree.

    This is a project-specific extension point (e.g., Prisma generation) that must
    be configuration-driven to keep Edison core generic.
    """
    for cmd in commands:
        result = run_with_timeout(
            ["bash", "-lc", cmd],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
        if result.returncode != 0:
            tail_out = "\n".join((result.stdout or "").splitlines()[-25:])
            tail_err = "\n".join((result.stderr or "").splitlines()[-25:])
            raise RuntimeError(
                "Post-install command failed in worktree:\n"
                f"  cwd: {worktree_path}\n"
                f"  cmd: {cmd}\n"
                f"  exit: {result.returncode}\n"
                f"  stdout (tail):\n{tail_out}\n"
                f"  stderr (tail):\n{tail_err}"
            )


def restore_worktree(session_id: str, *, base_branch: Optional[str] = None, dry_run: bool = False) -> Path:
    """Restore a worktree from archive directory back to active worktrees.

    Note: Since archive_worktree removes the worktree from git's tracking,
    we need to delete the archived directory and re-create the worktree
    using create_worktree. This ensures proper git registration.
    """
    repo_dir = get_repo_dir()
    config_obj = _config()
    cfg = config_obj.get_worktree_config()

    worktree_path, branch_name = _resolve_worktree_target(session_id, cfg)
    archive_full = _resolve_archive_directory(cfg, repo_dir)
    src = archive_full / session_id
    if not src.exists():
        raise RuntimeError(f"Archived worktree not found: {src}")

    if dry_run:
        return worktree_path

    # Remove the archived directory - we'll recreate the worktree fresh
    # This is necessary because archive_worktree calls git worktree remove,
    # which destroys the git metadata in the parent repo
    shutil.rmtree(src, ignore_errors=True)

    # Re-create the worktree using the standard creation flow
    # This ensures it's properly registered with git
    created_path, created_branch = create_worktree(
        session_id=session_id,
        base_branch=base_branch,
        dry_run=False
    )

    if created_path != worktree_path:
        raise RuntimeError(f"Restored worktree path mismatch: expected {worktree_path}, got {created_path}")

    return worktree_path


def update_worktree_env(worktree_path: Path, database_url: str) -> None:
    """Update .env file in worktree with session database URL."""
    env_path = worktree_path / ".env"
    if env_path.exists():
        env_content = env_path.read_text()
    else:
        example_path = worktree_path / ".env.example"
        env_content = example_path.read_text() if example_path.exists() else ""

    if _re.search(r"^DATABASE_URL=", env_content, _re.MULTILINE):
        env_content = _re.sub(r"^DATABASE_URL=.*$", f"DATABASE_URL=\"{database_url}\"", env_content, flags=_re.MULTILINE)
    else:
        env_content += f"\nDATABASE_URL=\"{database_url}\"\n"
    env_path.write_text(env_content)


def ensure_worktree_materialized(session_id: str) -> Dict[str, Any]:
    """Ensure worktree exists for session and return git metadata."""
    # This reconstructs the git metadata expected by the session
    path, branch = create_worktree(session_id)
    if path and branch:
        return {
            "worktreePath": str(path),
            "branchName": branch,
            # baseBranch is not returned by create_worktree, but we can infer or it's in session
            # For this return value, we just provide what we know.
            # The caller might merge this with existing session git meta.
        }
    return {}


def prepare_session_git_metadata(
    session_id: str,
    worktree_path: Optional[Path] = None,
    branch_name: Optional[str] = None,
    *,
    base_branch: Optional[str] = None,
) -> Dict[str, Any]:
    """Prepare git metadata dict for session from worktree information.

    This centralizes git metadata construction to avoid duplication across
    manager.py and autostart.py.

    Args:
        session_id: Session identifier
        worktree_path: Path to worktree (if None, will be computed)
        branch_name: Branch name (if None, will be computed)

    Returns:
        Dict with worktreePath, branchName, and baseBranch from config
    """
    cfg = _config().get_worktree_config()

    # Compute path and branch if not provided
    if worktree_path is None or branch_name is None:
        computed_path, computed_branch = resolve_worktree_target(session_id)
        worktree_path = worktree_path or computed_path
        branch_name = branch_name or computed_branch

    git_meta: Dict[str, Any] = {}

    if worktree_path:
        git_meta["worktreePath"] = str(worktree_path)

    if branch_name:
        git_meta["branchName"] = branch_name

    resolved_base = base_branch or cfg.get("baseBranch")
    if resolved_base is not None:
        git_meta["baseBranch"] = resolved_base

    return git_meta
