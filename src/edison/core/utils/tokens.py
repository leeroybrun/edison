"""Token expansion utilities for config-driven templating.

This module provides:
- Safe format_map expansion that preserves unknown placeholders
- Standard token sets derived from merged config + repo root

It is intentionally small and dependency-light so it can be used from:
- config domain accessors
- utilities (file context, pack discovery, MCP config)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


class SafeDict(dict):
    """dict that preserves unknown placeholders instead of raising."""

    def __missing__(self, key: str) -> str:  # pragma: no cover
        return "{" + key + "}"


def build_standard_tokens(
    repo_root: Path, config: Mapping[str, Any] | None = None
) -> dict[str, str]:
    """Return a standard set of template tokens.

    Conventions:
    - `*_DIR` tokens are repo-root relative directory names (e.g. ".edison")
    - `*_PATH` tokens are absolute paths (e.g. "/repo/.edison")
    """
    repo_root = Path(repo_root).expanduser().resolve()
    cfg = dict(config) if config is not None else {}

    # Project config dir name (.edison by default), resolved via the canonical
    # detection helper (respects env + config overrides).
    try:
        from edison.core.utils.paths import get_project_config_dir

        project_cfg_dir_name = get_project_config_dir(repo_root, create=False).name
    except Exception:
        project_cfg_dir_name = ".edison"

    # Project management root directory (.project by default), resolved from
    # merged config with a safe fallback.
    paths_section = cfg.get("paths") if isinstance(cfg.get("paths"), dict) else {}
    mgmt_dir = cfg.get("project_management_dir") or cfg.get("management_dir") or (
        paths_section.get("management_dir") if isinstance(paths_section, dict) else None
    )
    project_mgmt_dir_name = str(mgmt_dir).strip() if mgmt_dir else ".project"

    project_cfg_path = (repo_root / project_cfg_dir_name).resolve()
    project_mgmt_path = (repo_root / project_mgmt_dir_name).resolve()

    return {
        "PROJECT_ROOT": str(repo_root),
        "PROJECT_CONFIG_DIR": project_cfg_dir_name,
        "PROJECT_CONFIG_PATH": str(project_cfg_path),
        "PROJECT_MANAGEMENT_DIR": project_mgmt_dir_name,
        "PROJECT_MANAGEMENT_PATH": str(project_mgmt_path),
    }


def expand_tokens(template: str, tokens: Mapping[str, str]) -> str:
    """Expand `{TOKEN}` placeholders using SafeDict (unknown tokens preserved)."""
    return str(template).format_map(SafeDict(tokens))


def expand_path_template(
    repo_root: Path, template: str, tokens: Mapping[str, str]
) -> Path:
    """Expand a path template and resolve it relative to repo_root when needed."""
    expanded = expand_tokens(template, tokens)
    path = Path(expanded)
    if not path.is_absolute():
        path = (Path(repo_root).expanduser().resolve() / path).resolve()
    return path


__all__ = [
    "SafeDict",
    "build_standard_tokens",
    "expand_tokens",
    "expand_path_template",
]

