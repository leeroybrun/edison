"""Shared fixtures for composition tests."""
from __future__ import annotations

from pathlib import Path


def create_minimal_project(tmp_path: Path) -> Path:
    """Create a minimal project structure for testing."""
    project_config_dir = tmp_path / ".edison"
    project_config_dir.mkdir(parents=True)
    return project_config_dir


def write_composition_yaml(project_config_dir: Path, content: str) -> Path:
    """Write a composition.yaml file to project config dir."""
    composition_path = project_config_dir / "composition.yaml"
    composition_path.write_text(content, encoding="utf-8")
    return composition_path
