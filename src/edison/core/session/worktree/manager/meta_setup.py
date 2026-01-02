"""Meta/shared-state worktree setup helpers (excludes + commit guard)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from edison.core.utils.io import ensure_directory

from .shared_config import parse_shared_paths, shared_state_cfg


def ensure_checkout_git_excludes(*, checkout_path: Path, cfg: Dict[str, Any], scope: str) -> None:
    """Best-effort: ensure worktree-local git excludes for a checkout."""
    try:
        ss = shared_state_cfg(cfg)
        ge = ss.get("gitExcludes")
        if not isinstance(ge, dict):
            return
        patterns = ge.get(scope)
        if not isinstance(patterns, list):
            return

        from edison.core.utils.git.excludes import cleanup_repo_info_exclude, ensure_worktree_excludes

        final: list[str] = []
        for raw in patterns:
            pat = str(raw).strip()
            if not pat:
                continue
            final.append(pat)

            # If the user provides a directory-style exclude (`foo/`), also ignore the
            # path itself (`foo`) so that symlinks at that path don't show as untracked.
            if pat.endswith("/") and not any(ch in pat for ch in "*?["):
                final.append(pat.rstrip("/"))

        # Automatically ignore configured shared paths in non-meta checkouts to avoid
        # untracked symlink noise (tracked changes are never ignored by excludes).
        if scope in {"primary", "session"}:
            for item in parse_shared_paths(cfg):
                if scope not in set(item.get("scopes") or []):
                    continue
                p = str(item.get("path") or "").strip()
                if not p:
                    continue
                item_type = str(item.get("type") or "dir").strip().lower()
                if item_type == "dir":
                    base = p.rstrip("/")
                    final.append(base)
                    final.append(base + "/")
                else:
                    final.append(p.strip())

        # Preserve order while removing duplicates.
        deduped: list[str] = []
        seen: set[str] = set()
        for pat in final:
            if pat in seen:
                continue
            seen.add(pat)
            deduped.append(pat)

        ensure_worktree_excludes(checkout_path, deduped)

        # Migration: legacy Edison patterns in repo-wide `.git/info/exclude` affect ALL
        # worktrees and can prevent the meta branch from tracking meta-managed shared
        # paths. Now that per-worktree excludes are configured, remove those legacy lines.
        legacy_remove: list[str] = []
        legacy_remove.extend([".project", ".project/"])
        for item in parse_shared_paths(cfg):
            p = str(item.get("path") or "").strip()
            if not p:
                continue
            item_type = str(item.get("type") or "dir").strip().lower()
            if item_type == "dir":
                base = p.rstrip("/")
                legacy_remove.extend([base, base + "/"])
            else:
                legacy_remove.append(p)
        legacy_remove.extend([".zen", ".zen/"])
        legacy_remove.extend([".edison/_generated", ".edison/_generated/", ".edison/_generated.__tmp__*"])
        cleanup_repo_info_exclude(checkout_path, legacy_remove)
    except Exception:
        return


def ensure_meta_commit_guard(*, meta_path: Path, cfg: Dict[str, Any]) -> None:
    """Best-effort: install a pre-commit hook in the meta worktree to keep it clean."""
    try:
        ss = shared_state_cfg(cfg)
        guard = ss.get("commitGuard")
        if not isinstance(guard, dict):
            return
        if guard.get("enabled") is False:
            return

        allow: list[str] = []
        raw_allow = guard.get("allowPrefixes")
        if isinstance(raw_allow, list):
            allow = [str(p).strip() for p in raw_allow if str(p).strip()]

        for item in parse_shared_paths(cfg):
            if str(item.get("targetRoot") or "shared").strip().lower() != "shared":
                continue
            p = str(item.get("path") or "").strip()
            if not p:
                continue

            if item.get("commitAllowed") is not False:
                item_type = str(item.get("type") or "dir").strip().lower()
                if item_type == "dir":
                    allow.append(p.rstrip("/") + "/")
                else:
                    allow.append(p.strip())

            cap = item.get("commitAllowPrefixes")
            if isinstance(cap, list):
                for sub in cap:
                    s = str(sub).strip()
                    if not s:
                        continue
                    allow.append(s)

        if not allow:
            return

        def _bash_escape(s: str) -> str:
            return s.replace("\\", "\\\\").replace('"', '\\"')

        allow_prefixes_raw = [str(p).strip() for p in allow if str(p).strip()]
        allow_prefixes: list[str] = []
        seen: set[str] = set()
        for p in allow_prefixes_raw:
            if p in seen:
                continue
            seen.add(p)
            allow_prefixes.append(p)
        allow_block = "\n".join([f'  "{_bash_escape(p)}"' for p in allow_prefixes])

        meta_branch = str(ss.get("metaBranch") or "edison-meta").strip()
        meta_toplevel = str(meta_path.resolve())

        script = (
            "#!/usr/bin/env bash\n"
            "# Generated by Edison (worktrees.sharedState.commitGuard)\n"
            "set -euo pipefail\n"
            "\n"
            f'META_TOPLEVEL="{_bash_escape(meta_toplevel)}"\n'
            f'META_BRANCH="{_bash_escape(meta_branch)}"\n'
            "ALLOW_PREFIXES=(\n"
            f"{allow_block}\n"
            ")\n"
            "\n"
            "toplevel=$(git rev-parse --show-toplevel 2>/dev/null || true)\n"
            "if [[ -z \"$toplevel\" ]]; then\n"
            "  exit 0\n"
            "fi\n"
            "\n"
            "if [[ \"$toplevel\" != \"$META_TOPLEVEL\" ]]; then\n"
            "  exit 0\n"
            "fi\n"
            "\n"
            "branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)\n"
            "if [[ \"$branch\" != \"$META_BRANCH\" ]]; then\n"
            "  exit 0\n"
            "fi\n"
            "\n"
            "bad=0\n"
            "while IFS= read -r path; do\n"
            "  [[ -z \"$path\" ]] && continue\n"
            "  ok=0\n"
            "  for prefix in \"${ALLOW_PREFIXES[@]}\"; do\n"
            "    if [[ \"$path\" == \"$prefix\"* ]]; then\n"
            "      ok=1\n"
            "      break\n"
            "    fi\n"
            "  done\n"
            "  if [[ $ok -eq 0 ]]; then\n"
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

        from edison.core.utils.subprocess import run_with_timeout
        from ..config_helpers import _config

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

        ensure_directory(hook_path.parent)
        hook_path.write_text(script, encoding="utf-8")
        try:
            hook_path.chmod(0o755)
        except Exception:
            pass
    except Exception:
        return


def ensure_meta_worktree_setup(*, meta_path: Path, cfg: Dict[str, Any]) -> None:
    """Best-effort: apply meta worktree-only config (excludes + commit guard)."""
    ensure_checkout_git_excludes(checkout_path=meta_path, cfg=cfg, scope="meta")
    ensure_meta_commit_guard(meta_path=meta_path, cfg=cfg)


__all__ = [
    "ensure_checkout_git_excludes",
    "ensure_meta_commit_guard",
    "ensure_meta_worktree_setup",
]

