"""Config token interpolation helpers.

Edison uses two distinct templating syntaxes:
- Edison composition templates use double braces: `{{...}}`
- Runtime config may use single-brace tokens: `{PROJECT_ROOT}`, `{PROJECT_CONFIG_DIR}`, etc.

This module expands only *single-brace* tokens (not preceded/followed by `{`/`}`)
so it never mutates `{{...}}` composition variables.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping


_SINGLE_BRACE_TOKEN = re.compile(r"(?<!\{)\{([A-Z][A-Z0-9_]+)\}(?!\})")


def _get_nested(cfg: Mapping[str, Any], path: str) -> Any:
    cur: Any = cfg
    for part in path.split("."):
        if not isinstance(cur, Mapping):
            return None
        cur = cur.get(part)
    return cur


def build_tokens(repo_root: Path, cfg: Mapping[str, Any] | None = None) -> dict[str, str]:
    """Build a standard token set for config interpolation."""
    repo_root = Path(repo_root).expanduser().resolve()
    config = dict(cfg) if cfg is not None else {}

    # Project config dir name (.edison by default), resolved via canonical helper
    # (respects env overrides).
    try:
        from edison.core.utils.paths import get_project_config_dir

        project_cfg_dir_name = get_project_config_dir(repo_root, create=False).name
    except Exception:
        project_cfg_dir_name = ".edison"

    # Project management root dir (.project by default), resolved from merged config
    # with a safe fallback.
    paths_section = config.get("paths") if isinstance(config.get("paths"), dict) else {}
    mgmt_dir = config.get("project_management_dir") or config.get("management_dir") or (
        paths_section.get("management_dir") if isinstance(paths_section, dict) else None
    )
    project_mgmt_dir_name = str(mgmt_dir).strip() if mgmt_dir else ".project"

    # Project name: use configured name unless it is the placeholder "project".
    raw_name = _get_nested(config, "project.name")
    project_name = str(raw_name).strip() if raw_name is not None else ""
    if not project_name or project_name == "project":
        project_name = repo_root.name

    project_cfg_path = (repo_root / project_cfg_dir_name).resolve()
    project_mgmt_path = (repo_root / project_mgmt_dir_name).resolve()

    bundle_file = _get_nested(config, "validation.artifactPaths.bundleSummaryFile")
    bundle_filename = str(bundle_file).strip() if bundle_file else "validation-summary.md"

    return {
        "PROJECT_ROOT": str(repo_root),
        "PROJECT_NAME": project_name,
        "PROJECT_CONFIG_DIR": project_cfg_dir_name,
        "PROJECT_CONFIG_PATH": str(project_cfg_path),
        "PROJECT_MANAGEMENT_DIR": project_mgmt_dir_name,
        "PROJECT_MANAGEMENT_PATH": str(project_mgmt_path),
        "BUNDLE_SUMMARY_FILE": bundle_filename,
    }


def expand_tokens(text: str, tokens: Mapping[str, str]) -> str:
    """Expand known single-brace tokens in a string.

    - Only expands tokens that appear as `{TOKEN}` (single braces).
    - Unknown tokens are preserved.
    - Does not affect `{{...}}` strings.
    """

    if not isinstance(text, str) or "{" not in text:
        return str(text)

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return tokens.get(key, "{" + key + "}")

    return _SINGLE_BRACE_TOKEN.sub(repl, text)


def interpolate(obj: Any, tokens: Mapping[str, str]) -> Any:
    """Recursively expand tokens throughout a config structure.

    Mutates dicts/lists in-place (for performance), returning the same object.
    """
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            obj[k] = interpolate(v, tokens)
        return obj
    if isinstance(obj, list):
        for i, v in enumerate(list(obj)):
            obj[i] = interpolate(v, tokens)
        return obj
    if isinstance(obj, str):
        return expand_tokens(obj, tokens)
    return obj


__all__ = ["build_tokens", "expand_tokens", "interpolate"]
