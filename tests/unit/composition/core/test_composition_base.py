"""Tests for CompositionBase enhancements.

TDD: Tests for new helper methods in CompositionBase:
- _extract_definitions(): Extract definitions list from config data
- _merge_definitions_by_id(): Merge definitions by ID key
- writer property: Lazy-initialized CompositionFileWriter
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import pytest


class ConcreteCompositionBase:
    """Concrete implementation for testing CompositionBase."""

    # Created dynamically in tests to avoid circular imports


class TestCompositionBaseWriter:
    """Tests for the writer property."""

    def test_writer_property_exists(self, isolated_project_env: Path) -> None:
        """CompositionBase has a writer property."""
        from edison.core.composition.core.base import CompositionBase

        # Create concrete subclass
        class TestBase(CompositionBase):
            def _setup_composition_dirs(self) -> None:
                from edison.data import get_data_path

                self.core_dir = Path(get_data_path(""))
                self.bundled_packs_dir = Path(get_data_path("packs"))
                self.project_packs_dir = self.project_dir / "packs"
                self.packs_dir = self.bundled_packs_dir

        base = TestBase()

        assert hasattr(base, "writer")

    def test_writer_is_lazy_initialized(self, isolated_project_env: Path) -> None:
        """Writer is not created until accessed."""
        from edison.core.composition.core.base import CompositionBase

        class TestBase(CompositionBase):
            def _setup_composition_dirs(self) -> None:
                from edison.data import get_data_path

                self.core_dir = Path(get_data_path(""))
                self.bundled_packs_dir = Path(get_data_path("packs"))
                self.project_packs_dir = self.project_dir / "packs"
                self.packs_dir = self.bundled_packs_dir

        base = TestBase()

        # Before access, _writer should be None
        assert base._writer is None

        # After access, _writer should be set
        _ = base.writer
        assert base._writer is not None

    def test_writer_returns_composition_file_writer(
        self, isolated_project_env: Path
    ) -> None:
        """Writer property returns CompositionFileWriter instance."""
        from edison.core.composition.core.base import CompositionBase
        from edison.core.composition.output.writer import CompositionFileWriter

        class TestBase(CompositionBase):
            def _setup_composition_dirs(self) -> None:
                from edison.data import get_data_path

                self.core_dir = Path(get_data_path(""))
                self.bundled_packs_dir = Path(get_data_path("packs"))
                self.project_packs_dir = self.project_dir / "packs"
                self.packs_dir = self.bundled_packs_dir

        base = TestBase()

        assert isinstance(base.writer, CompositionFileWriter)


class TestExtractDefinitions:
    """Tests for _extract_definitions() helper."""

    def test_extract_definitions_simple_list(
        self, isolated_project_env: Path
    ) -> None:
        """Extract definitions list from simple config."""
        from edison.core.composition.core.base import CompositionBase

        class TestBase(CompositionBase):
            def _setup_composition_dirs(self) -> None:
                from edison.data import get_data_path

                self.core_dir = Path(get_data_path(""))
                self.bundled_packs_dir = Path(get_data_path("packs"))
                self.project_packs_dir = self.project_dir / "packs"
                self.packs_dir = self.bundled_packs_dir

        base = TestBase()

        data = {
            "commands": [
                {"id": "cmd1", "name": "Command 1"},
                {"id": "cmd2", "name": "Command 2"},
            ]
        }

        result = base._extract_definitions(data, "commands")

        assert len(result) == 2
        assert result[0]["id"] == "cmd1"
        assert result[1]["id"] == "cmd2"

    def test_extract_definitions_nested_key(
        self, isolated_project_env: Path
    ) -> None:
        """Extract definitions from nested path."""
        from edison.core.composition.core.base import CompositionBase

        class TestBase(CompositionBase):
            def _setup_composition_dirs(self) -> None:
                from edison.data import get_data_path

                self.core_dir = Path(get_data_path(""))
                self.bundled_packs_dir = Path(get_data_path("packs"))
                self.project_packs_dir = self.project_dir / "packs"
                self.packs_dir = self.bundled_packs_dir

        base = TestBase()

        data = {
            "ide": {
                "claude": {
                    "hooks": [
                        {"id": "hook1", "type": "pre"},
                        {"id": "hook2", "type": "post"},
                    ]
                }
            }
        }

        result = base._extract_definitions(data, "ide.claude.hooks")

        assert len(result) == 2
        assert result[0]["id"] == "hook1"
        assert result[1]["id"] == "hook2"

    def test_extract_definitions_missing_key(
        self, isolated_project_env: Path
    ) -> None:
        """Extract returns empty list for missing key."""
        from edison.core.composition.core.base import CompositionBase

        class TestBase(CompositionBase):
            def _setup_composition_dirs(self) -> None:
                from edison.data import get_data_path

                self.core_dir = Path(get_data_path(""))
                self.bundled_packs_dir = Path(get_data_path("packs"))
                self.project_packs_dir = self.project_dir / "packs"
                self.packs_dir = self.bundled_packs_dir

        base = TestBase()

        data = {"other": "value"}

        result = base._extract_definitions(data, "commands")

        assert result == []

    def test_extract_definitions_not_a_list(
        self, isolated_project_env: Path
    ) -> None:
        """Extract returns empty list if value is not a list."""
        from edison.core.composition.core.base import CompositionBase

        class TestBase(CompositionBase):
            def _setup_composition_dirs(self) -> None:
                from edison.data import get_data_path

                self.core_dir = Path(get_data_path(""))
                self.bundled_packs_dir = Path(get_data_path("packs"))
                self.project_packs_dir = self.project_dir / "packs"
                self.packs_dir = self.bundled_packs_dir

        base = TestBase()

        data = {"commands": "not-a-list"}

        result = base._extract_definitions(data, "commands")

        assert result == []


class TestMergeDefinitionsById:
    """Tests for _merge_definitions_by_id() helper."""

    def test_merge_adds_new_definitions(
        self, isolated_project_env: Path
    ) -> None:
        """Merge adds new definitions to base dict."""
        from edison.core.composition.core.base import CompositionBase

        class TestBase(CompositionBase):
            def _setup_composition_dirs(self) -> None:
                from edison.data import get_data_path

                self.core_dir = Path(get_data_path(""))
                self.bundled_packs_dir = Path(get_data_path("packs"))
                self.project_packs_dir = self.project_dir / "packs"
                self.packs_dir = self.bundled_packs_dir

        base = TestBase()

        existing: Dict[str, Dict[str, Any]] = {}
        new_defs = [
            {"id": "cmd1", "name": "Command 1"},
            {"id": "cmd2", "name": "Command 2"},
        ]

        result = base._merge_definitions_by_id(existing, new_defs)

        assert "cmd1" in result
        assert "cmd2" in result
        assert result["cmd1"]["name"] == "Command 1"

    def test_merge_updates_existing_definitions(
        self, isolated_project_env: Path
    ) -> None:
        """Merge updates existing definitions (overlay pattern)."""
        from edison.core.composition.core.base import CompositionBase

        class TestBase(CompositionBase):
            def _setup_composition_dirs(self) -> None:
                from edison.data import get_data_path

                self.core_dir = Path(get_data_path(""))
                self.bundled_packs_dir = Path(get_data_path("packs"))
                self.project_packs_dir = self.project_dir / "packs"
                self.packs_dir = self.bundled_packs_dir

        base = TestBase()

        existing = {
            "cmd1": {"id": "cmd1", "name": "Original", "extra": "keep-me"},
        }
        new_defs = [
            {"id": "cmd1", "name": "Updated"},  # Updates name, keeps extra
        ]

        result = base._merge_definitions_by_id(existing, new_defs)

        assert result["cmd1"]["name"] == "Updated"
        assert result["cmd1"]["extra"] == "keep-me"

    def test_merge_custom_id_key(
        self, isolated_project_env: Path
    ) -> None:
        """Merge supports custom ID key."""
        from edison.core.composition.core.base import CompositionBase

        class TestBase(CompositionBase):
            def _setup_composition_dirs(self) -> None:
                from edison.data import get_data_path

                self.core_dir = Path(get_data_path(""))
                self.bundled_packs_dir = Path(get_data_path("packs"))
                self.project_packs_dir = self.project_dir / "packs"
                self.packs_dir = self.bundled_packs_dir

        base = TestBase()

        existing: Dict[str, Dict[str, Any]] = {}
        new_defs = [
            {"name": "hook1", "type": "pre"},
            {"name": "hook2", "type": "post"},
        ]

        result = base._merge_definitions_by_id(existing, new_defs, id_key="name")

        assert "hook1" in result
        assert "hook2" in result
        assert result["hook1"]["type"] == "pre"

    def test_merge_skips_missing_id(
        self, isolated_project_env: Path
    ) -> None:
        """Merge skips definitions without ID key."""
        from edison.core.composition.core.base import CompositionBase

        class TestBase(CompositionBase):
            def _setup_composition_dirs(self) -> None:
                from edison.data import get_data_path

                self.core_dir = Path(get_data_path(""))
                self.bundled_packs_dir = Path(get_data_path("packs"))
                self.project_packs_dir = self.project_dir / "packs"
                self.packs_dir = self.bundled_packs_dir

        base = TestBase()

        existing: Dict[str, Dict[str, Any]] = {}
        new_defs = [
            {"id": "cmd1", "name": "Valid"},
            {"name": "No ID"},  # Missing id key
        ]

        result = base._merge_definitions_by_id(existing, new_defs)

        assert "cmd1" in result
        assert len(result) == 1  # Invalid definition skipped


# Backward compat aliases have been removed - use canonical method names:
# - get_active_packs() instead of _active_packs()
# - load_yaml_safe() instead of _load_yaml_safe()
# - merge_yaml() instead of _merge_from_file()
