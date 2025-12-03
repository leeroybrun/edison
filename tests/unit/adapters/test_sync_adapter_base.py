"""Tests for enhanced SyncAdapter base class.

TDD: Tests for SyncAdapter enhancements:
- Inherits from CompositionBase
- adapters_config property
- output_config property
- validate_structure() method
- sync_agents_from_generated() method
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest


class TestSyncAdapterInheritance:
    """Tests that SyncAdapter inherits from CompositionBase."""

    def test_inherits_from_composition_base(self, isolated_project_env: Path) -> None:
        """SyncAdapter should inherit from CompositionBase."""
        from edison.core.adapters.sync.base import SyncAdapter
        from edison.core.composition.core.base import CompositionBase

        assert issubclass(SyncAdapter, CompositionBase)

    def test_has_path_resolution(self, isolated_project_env: Path) -> None:
        """SyncAdapter should have path resolution from CompositionBase."""
        from edison.core.adapters.sync.base import SyncAdapter

        class TestSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                return {}

        adapter = TestSync()

        assert hasattr(adapter, "project_root")
        assert hasattr(adapter, "project_dir")
        assert hasattr(adapter, "core_dir")

    def test_has_config_management(self, isolated_project_env: Path) -> None:
        """SyncAdapter should have config management from CompositionBase."""
        from edison.core.adapters.sync.base import SyncAdapter

        class TestSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                return {}

        adapter = TestSync()

        assert hasattr(adapter, "cfg_mgr")
        assert hasattr(adapter, "config")
        assert isinstance(adapter.config, dict)

    def test_has_writer_property(self, isolated_project_env: Path) -> None:
        """SyncAdapter should have writer property from CompositionBase."""
        from edison.core.adapters.sync.base import SyncAdapter
        from edison.core.composition.output.writer import CompositionFileWriter

        class TestSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                return {}

        adapter = TestSync()

        assert hasattr(adapter, "writer")
        assert isinstance(adapter.writer, CompositionFileWriter)


class TestSyncAdapterConfigProperties:
    """Tests for adapters_config and output_config properties."""

    def test_adapters_config_property(self, isolated_project_env: Path) -> None:
        """SyncAdapter should have lazy adapters_config property."""
        from edison.core.adapters.sync.base import SyncAdapter

        class TestSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                return {}

        adapter = TestSync()

        # Should be lazy - not loaded until accessed
        assert adapter._adapters_config is None

        # Access the property
        config = adapter.adapters_config

        # Should return AdaptersConfig
        from edison.core.config.domains import AdaptersConfig

        assert isinstance(config, AdaptersConfig)

        # Should be cached after access
        assert adapter._adapters_config is not None

    def test_output_config_property(self, isolated_project_env: Path) -> None:
        """SyncAdapter should have lazy output_config property."""
        from edison.core.adapters.sync.base import SyncAdapter

        class TestSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                return {}

        adapter = TestSync()

        # Should be lazy
        assert adapter._output_config is None

        # Access the property
        config = adapter.output_config

        # Should return OutputConfigLoader
        from edison.core.composition.output.config import OutputConfigLoader

        assert isinstance(config, OutputConfigLoader)


class TestSyncAdapterValidateStructure:
    """Tests for validate_structure() method."""

    def test_validate_structure_creates_missing_dir(
        self, isolated_project_env: Path
    ) -> None:
        """validate_structure creates missing directories by default."""
        from edison.core.adapters.sync.base import SyncAdapter

        class TestSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                return {}

        adapter = TestSync()

        target_dir = isolated_project_env / "new" / "nested" / "dir"
        assert not target_dir.exists()

        result = adapter.validate_structure(target_dir)

        assert result == target_dir
        assert target_dir.exists()

    def test_validate_structure_raises_when_create_disabled(
        self, isolated_project_env: Path
    ) -> None:
        """validate_structure raises when create_missing=False."""
        from edison.core.adapters.sync.base import SyncAdapter

        class TestSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                return {}

        adapter = TestSync()

        target_dir = isolated_project_env / "nonexistent"

        with pytest.raises(RuntimeError, match="Missing directory"):
            adapter.validate_structure(target_dir, create_missing=False)

    def test_validate_structure_returns_existing_dir(
        self, isolated_project_env: Path
    ) -> None:
        """validate_structure returns existing directory without error."""
        from edison.core.adapters.sync.base import SyncAdapter

        class TestSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                return {}

        adapter = TestSync()

        target_dir = isolated_project_env / ".edison"
        target_dir.mkdir(parents=True, exist_ok=True)

        result = adapter.validate_structure(target_dir)

        assert result == target_dir


class TestSyncAdapterSyncAgentsFromGenerated:
    """Tests for sync_agents_from_generated() method."""

    def test_sync_agents_copies_files(self, isolated_project_env: Path) -> None:
        """sync_agents_from_generated copies agent files to target."""
        from edison.core.adapters.sync.base import SyncAdapter

        class TestSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                return {}

        adapter = TestSync()

        # Create _generated/agents/ with some files
        gen_agents = isolated_project_env / ".edison" / "_generated" / "agents"
        gen_agents.mkdir(parents=True, exist_ok=True)
        (gen_agents / "api-builder.md").write_text("# API Builder\n\nContent.")
        (gen_agents / "code-reviewer.md").write_text("# Code Reviewer\n\nContent.")

        # Target directory
        target_dir = isolated_project_env / "target" / "agents"

        # Sync
        result = adapter.sync_agents_from_generated(target_dir)

        # Should return list of created paths
        assert len(result) == 2
        assert (target_dir / "api-builder.md").exists()
        assert (target_dir / "code-reviewer.md").exists()

    def test_sync_agents_returns_empty_when_no_agents(
        self, isolated_project_env: Path
    ) -> None:
        """sync_agents_from_generated returns empty list when no agents."""
        from edison.core.adapters.sync.base import SyncAdapter

        class TestSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                return {}

        adapter = TestSync()

        target_dir = isolated_project_env / "target" / "agents"

        result = adapter.sync_agents_from_generated(target_dir)

        assert result == []


class TestSyncAdapterBackwardCompatibility:
    """Tests for backward compatibility with existing sync adapters."""

    def test_sync_all_abstract(self, isolated_project_env: Path) -> None:
        """sync_all is abstract and must be implemented."""
        from edison.core.adapters.sync.base import SyncAdapter

        with pytest.raises(TypeError):
            SyncAdapter()  # type: ignore[abstract]

    def test_create_factory_method(self, isolated_project_env: Path) -> None:
        """create() factory method still works."""
        from edison.core.adapters.sync.base import SyncAdapter

        class TestSync(SyncAdapter):
            def sync_all(self) -> Dict[str, Any]:
                return {"test": True}

        adapter = TestSync.create()

        assert isinstance(adapter, TestSync)
