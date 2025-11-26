"""Project configuration path resolution.

This module centralizes detection of the project-level configuration
directory. Edison prefers ``.edison`` when it represents project state,
then auto-detects any other dot-directories that look like project
configuration (e.g., contain ``config/`` or ``config.yml``). It avoids
mistaking a framework checkout at ``.edison/core`` for a project config
directory.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

try:
    import yaml  # type: ignore
except Exception as err:  # pragma: no cover - surfaced in tests
    raise RuntimeError("PyYAML is required for project path resolution") from err

# Primary preference remains .edison to align with current convention.
DEFAULT_PROJECT_CONFIG_PRIMARY = ".edison"


def _load_project_dir_from_yaml(path: Path) -> str | None:
    """Extract ``paths.project_config_dir`` from a YAML file when present."""

    if not path.exists() or not path.is_file():
        return None

    data = yaml.safe_load(path.read_text()) or {}
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

    Precedence: environment override → project overlays (.edison)
    → core defaults. Falls back to ``DEFAULT_PROJECT_CONFIG_PRIMARY`` when no
    config provides a value.
    """

    env_override = os.environ.get("EDISON_paths__project_config_dir")
    if isinstance(env_override, str) and env_override.strip():
        return env_override.strip()

    value: str | None = None

    core_config_dir = repo_root / ".edison" / "core" / "config"
    defaults_path = core_config_dir / "defaults.yaml"
    value = _load_project_dir_from_yaml(defaults_path) or value

    for path in sorted(core_config_dir.glob("*.yaml")):
        if path.name == "defaults.yaml":
            continue
        found = _load_project_dir_from_yaml(path)
        value = found or value

    # Process project overrides (.edison)
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
        project_dir.mkdir(parents=True, exist_ok=True)
    return project_dir