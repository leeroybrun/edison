"""Tests for YamlLayerMixin.

Tests YAML file and directory loading utilities for registries.
"""
from pathlib import Path
from typing import Any, Dict

import pytest

from edison.core.composition.core.yaml_layer import YamlLayerMixin
from edison.core.config import ConfigManager


class MockRegistry(YamlLayerMixin):
    """Mock registry for testing YamlLayerMixin."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.cfg_mgr = ConfigManager(project_root)


class TestYamlLayerMixin:
    """Test YamlLayerMixin methods."""

    def test_load_yaml_file_exists(self, tmp_path: Path) -> None:
        """Test loading an existing YAML file."""
        # Create test YAML file
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("key: value\nlist:\n  - item1\n  - item2\n")

        registry = MockRegistry(tmp_path)
        result = registry._load_yaml_file(yaml_file)

        assert result == {"key": "value", "list": ["item1", "item2"]}

    def test_load_yaml_file_not_exists_optional(self, tmp_path: Path) -> None:
        """Test loading non-existent YAML file (optional)."""
        yaml_file = tmp_path / "nonexistent.yaml"

        registry = MockRegistry(tmp_path)
        result = registry._load_yaml_file(yaml_file, required=False)

        assert result == {}

    def test_load_yaml_file_not_exists_required(self, tmp_path: Path) -> None:
        """Test loading non-existent YAML file (required) raises error."""
        yaml_file = tmp_path / "nonexistent.yaml"

        registry = MockRegistry(tmp_path)
        with pytest.raises(FileNotFoundError, match="Required YAML not found"):
            registry._load_yaml_file(yaml_file, required=True)

    def test_load_yaml_file_empty(self, tmp_path: Path) -> None:
        """Test loading empty YAML file returns empty dict."""
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("")

        registry = MockRegistry(tmp_path)
        result = registry._load_yaml_file(yaml_file)

        assert result == {}

    def test_load_yaml_dir_exists(self, tmp_path: Path) -> None:
        """Test loading all YAML files from a directory."""
        # Create test directory with YAML files
        yaml_dir = tmp_path / "yamls"
        yaml_dir.mkdir()

        file1 = yaml_dir / "file1.yaml"
        file1.write_text("name: file1\nvalue: 1\n")

        file2 = yaml_dir / "file2.yaml"
        file2.write_text("name: file2\nvalue: 2\n")

        registry = MockRegistry(tmp_path)
        results = registry._load_yaml_dir(yaml_dir, "test-origin")

        assert len(results) == 2
        # Results should be sorted by filename
        assert results[0]["name"] == "file1"
        assert results[0]["value"] == 1
        assert results[0]["_path"] == str(file1)
        assert results[0]["_origin"] == "test-origin"

        assert results[1]["name"] == "file2"
        assert results[1]["value"] == 2
        assert results[1]["_path"] == str(file2)
        assert results[1]["_origin"] == "test-origin"

    def test_load_yaml_dir_not_exists(self, tmp_path: Path) -> None:
        """Test loading from non-existent directory returns empty list."""
        yaml_dir = tmp_path / "nonexistent"

        registry = MockRegistry(tmp_path)
        results = registry._load_yaml_dir(yaml_dir, "test-origin")

        assert results == []

    def test_load_yaml_dir_empty(self, tmp_path: Path) -> None:
        """Test loading from empty directory returns empty list."""
        yaml_dir = tmp_path / "empty"
        yaml_dir.mkdir()

        registry = MockRegistry(tmp_path)
        results = registry._load_yaml_dir(yaml_dir, "test-origin")

        assert results == []

    def test_load_yaml_dir_ignores_non_yaml(self, tmp_path: Path) -> None:
        """Test loading directory ignores non-YAML files."""
        yaml_dir = tmp_path / "mixed"
        yaml_dir.mkdir()

        # Create YAML and non-YAML files
        yaml_file = yaml_dir / "data.yaml"
        yaml_file.write_text("name: data\n")

        txt_file = yaml_dir / "readme.txt"
        txt_file.write_text("This is not YAML")

        registry = MockRegistry(tmp_path)
        results = registry._load_yaml_dir(yaml_dir, "test-origin")

        assert len(results) == 1
        assert results[0]["name"] == "data"

    def test_load_yaml_dir_sorted_order(self, tmp_path: Path) -> None:
        """Test files are loaded in sorted order."""
        yaml_dir = tmp_path / "sorted"
        yaml_dir.mkdir()

        # Create files in non-alphabetical order
        (yaml_dir / "c.yaml").write_text("name: c\n")
        (yaml_dir / "a.yaml").write_text("name: a\n")
        (yaml_dir / "b.yaml").write_text("name: b\n")

        registry = MockRegistry(tmp_path)
        results = registry._load_yaml_dir(yaml_dir, "test-origin")

        # Should be sorted: a, b, c
        assert len(results) == 3
        assert results[0]["name"] == "a"
        assert results[1]["name"] == "b"
        assert results[2]["name"] == "c"


class TestYamlLayerMixinIntegration:
    """Test YamlLayerMixin with realistic registry scenarios."""

    def test_load_layered_config(self, tmp_path: Path) -> None:
        """Test loading config from multiple layers (core, pack, project)."""
        # Simulate layered structure
        core_dir = tmp_path / "core"
        core_dir.mkdir()
        (core_dir / "rules.yaml").write_text("id: core-rule\npriority: 10\n")

        pack_dir = tmp_path / "pack"
        pack_dir.mkdir()
        (pack_dir / "rules.yaml").write_text("id: pack-rule\npriority: 20\n")

        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / "rules.yaml").write_text("id: project-rule\npriority: 30\n")

        registry = MockRegistry(tmp_path)

        core_rules = registry._load_yaml_dir(core_dir, "core")
        pack_rules = registry._load_yaml_dir(pack_dir, "pack:python")
        project_rules = registry._load_yaml_dir(project_dir, "project")

        assert len(core_rules) == 1
        assert core_rules[0]["_origin"] == "core"
        assert len(pack_rules) == 1
        assert pack_rules[0]["_origin"] == "pack:python"
        assert len(project_rules) == 1
        assert project_rules[0]["_origin"] == "project"
