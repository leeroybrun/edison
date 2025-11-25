from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

CORE_ROOT = Path(__file__).resolve().parents[2]
module_path = CORE_ROOT / "lib" / "paths" / "project.py"
spec = importlib.util.spec_from_file_location("lib.paths.project", module_path)
assert spec and spec.loader, "Unable to load lib.paths.project module spec"
project_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(project_module)
get_project_config_dir = project_module.get_project_config_dir  # type: ignore[attr-defined]


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data))


def test_uses_project_config_dir_from_project_overrides(tmp_path: Path) -> None:
    """Project overlays should determine project_config_dir (e.g., .agents)."""
    core_defaults = tmp_path / ".edison" / "core" / "config" / "defaults.yaml"
    _write_yaml(core_defaults, {"paths": {"project_config_dir": ".edison"}})

    # Simulate existing .edison/config (current resolver wrongly prefers this)
    edison_config_defaults = tmp_path / ".edison" / "config" / "defaults.yaml"
    _write_yaml(edison_config_defaults, {"paths": {"project_config_dir": ".edison"}})

    project_defaults = tmp_path / ".agents" / "config" / "defaults.yaml"
    _write_yaml(project_defaults, {"paths": {"project_config_dir": ".agents"}})

    # Presence of framework checkout should not override explicit config
    (tmp_path / ".edison" / "core").mkdir(parents=True, exist_ok=True)

    chosen = get_project_config_dir(tmp_path)
    assert chosen == tmp_path / ".agents"


def test_falls_back_to_core_default_when_no_project_override(tmp_path: Path) -> None:
    """Core defaults remain the fallback when project config lacks an override."""
    core_defaults = tmp_path / ".edison" / "core" / "config" / "defaults.yaml"
    _write_yaml(core_defaults, {"paths": {"project_config_dir": ".edison"}})

    chosen = get_project_config_dir(tmp_path)
    assert chosen == tmp_path / ".edison"


def test_creates_default_edison_when_missing(tmp_path: Path) -> None:
    """When no config is available, fall back to the global default and create it."""
    chosen = get_project_config_dir(tmp_path)
    assert chosen == tmp_path / ".agents"
    assert chosen.exists()
