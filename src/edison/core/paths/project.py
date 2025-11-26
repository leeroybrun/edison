"""Project configuration path resolution.

This module centralizes detection of the project-level configuration
directory. Edison prefers ``.edison`` when it represents project state,
then auto-detects any other dot-directories that look like project
configuration (e.g., contain ``config/`` or ``config.yml``).

Configuration precedence (highest to lowest):
1. Environment variable: EDISON_paths__project_config_dir
2. Project overrides: {repo_root}/.edison/config/*.yml
3. Bundled defaults: edison.data package
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from edison.core.file_io.utils import ensure_dir

try:
    import yaml  # type: ignore
except Exception as err:  # pragma: no cover - surfaced in tests
    raise RuntimeError("PyYAML is required for project path resolution") from err

# Primary preference remains .edison to align with current convention.
DEFAULT_PROJECT_CONFIG_PRIMARY = ".edison"


def _load_project_dir_from_yaml(path: Path) -> str | None:
    """Extract ``paths.project_config_dir`` from a YAML file when present."""

    from edison.core.file_io.utils import read_yaml_safe

    if not path.exists() or not path.is_file():
        return None

    data = read_yaml_safe(path, default={})
    if not isinstance(data, dict):
        return None

    paths_section = data.get("paths")
    if isinstance(paths_section, dict):
        value = paths_section.get("project_config_dir")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _resolve_project_dir_from_configs(repo_root: Path) -> str | None:
    """Resolve project config dir using configuration precedence.

    Precedence (highest to lowest):
    1. Environment variable: EDISON_paths__project_config_dir
    2. Project overrides: {repo_root}/.edison/config/*.yml
    3. Bundled defaults: edison.data package

    Falls back to ``DEFAULT_PROJECT_CONFIG_PRIMARY`` when no config provides a value.
    """
    # Priority 1: Environment override
    env_override = os.environ.get("EDISON_paths__project_config_dir")
    if isinstance(env_override, str) and env_override.strip():
        return env_override.strip()

    value: str | None = None

    # Priority 2: Bundled defaults from edison.data package
    try:
        from edison.data import get_data_path

        bundled_defaults = get_data_path("config", "defaults.yaml")
        if bundled_defaults.exists():
            value = _load_project_dir_from_yaml(bundled_defaults) or value
    except Exception:
        pass  # Bundled data not available, continue with project config

    # Priority 3: Project overrides (.edison/config/)
    config_dir = repo_root / ".edison" / "config"
    if config_dir.exists():
        yaml_files = sorted(config_dir.glob("*.yml")) + sorted(config_dir.glob("*.yaml"))
        for yaml_path in yaml_files:
            found = _load_project_dir_from_yaml(yaml_path)
            if found is not None:
                value = found

    return value or DEFAULT_PROJECT_CONFIG_PRIMARY


def get_project_config_dir(
    repo_root: Path, candidates: Iterable[str] | None = None, create: bool = True
) -> Path:
    """Return the project config directory using configuration.

    Args:
        repo_root: Repository root path.
        candidates: Ignored (legacy compatibility).
        create: If True, create the resolved directory when it does not exist.

    Returns:
        Path: Project configuration directory resolved via config.
    """

    project_dir_name = _resolve_project_dir_from_configs(repo_root) or DEFAULT_PROJECT_CONFIG_PRIMARY

    project_dir = repo_root / project_dir_name

    if create:
        ensure_dir(project_dir)
    return project_dir