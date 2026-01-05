from __future__ import annotations

from pathlib import Path

import yaml

from edison.core.config import ConfigManager


def test_config_manager_save_prefers_existing_validation_yaml(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)

    # Simulate a project that already uses the canonical filename.
    (cfg_dir / "validation.yaml").write_text(yaml.safe_dump({"validation": {}}, sort_keys=False), encoding="utf-8")

    mgr = ConfigManager(repo_root=repo)
    mgr.set("validation.evidence.requiredFiles", ["command-test.txt"])
    written = mgr.save()

    assert written.name == "validation.yaml"
    assert (cfg_dir / "validation.yml").exists() is False

    data = yaml.safe_load((cfg_dir / "validation.yaml").read_text(encoding="utf-8")) or {}
    assert data["validation"]["evidence"]["requiredFiles"] == ["command-test.txt"]

