"""Shared-state configuration parsing for worktree management."""

from __future__ import annotations

from typing import Any, Dict, List


def shared_state_cfg(cfg: Dict[str, Any]) -> Dict[str, Any]:
    raw = cfg.get("sharedState")
    return raw if isinstance(raw, dict) else {}


def parse_shared_paths(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse `worktrees.sharedState.sharedPaths` into a normalized list of dicts."""
    ss = shared_state_cfg(cfg)
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
                    "enabled": True,
                    "commitAllowed": True,
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

            enabled = item.get("enabled")
            if enabled is None:
                enabled = True
            enabled = bool(enabled)

            commit_allowed = item.get("commitAllowed")
            if commit_allowed is None:
                commit_allowed = True
            commit_allowed = bool(commit_allowed)

            commit_allow_prefixes_raw = item.get("commitAllowPrefixes")
            commit_allow_prefixes: list[str] = []
            if isinstance(commit_allow_prefixes_raw, list):
                commit_allow_prefixes = [
                    str(p).strip() for p in commit_allow_prefixes_raw if str(p).strip()
                ]

            only_if_target_exists = item.get("onlyIfTargetExists")
            if only_if_target_exists is None:
                only_if_target_exists = item.get("only_if_target_exists")
            if only_if_target_exists is None:
                only_if_target_exists = False
            only_if_target_exists = bool(only_if_target_exists)

            out.append(
                {
                    "path": path,
                    "scopes": scopes,
                    "mergeExisting": merge_existing,
                    "targetRoot": target_root,
                    "type": item_type,
                    "enabled": enabled,
                    "commitAllowed": commit_allowed,
                    "commitAllowPrefixes": commit_allow_prefixes,
                    "onlyIfTargetExists": only_if_target_exists,
                }
            )
            continue

    # Normalize duplicates by path: last occurrence wins.
    by_path: dict[str, Dict[str, Any]] = {}
    order: list[str] = []
    for entry in out:
        p = str(entry.get("path") or "").strip()
        if not p:
            continue
        if p in by_path:
            try:
                order.remove(p)
            except ValueError:
                pass
        by_path[p] = entry
        order.append(p)

    normalized: list[Dict[str, Any]] = []
    for p in order:
        e = by_path.get(p)
        if not e:
            continue
        if e.get("enabled") is False:
            continue
        normalized.append(e)
    return normalized


__all__ = ["shared_state_cfg", "parse_shared_paths"]
