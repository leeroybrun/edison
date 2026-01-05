"""Tests for OpenCode platform adapter.

The OpenCode adapter generates OpenCode artifacts (.opencode/ directory)
via Edison's composition system.
"""
from __future__ import annotations

from pathlib import Path

import pytest


class TestOpenCodeAdapterRegistration:
    """Test OpenCode adapter registration in composition system."""

    def test_opencode_adapter_importable(self) -> None:
        """OpenCodeAdapter should be importable from platforms module."""
        from edison.core.adapters.platforms.opencode import OpenCodeAdapter

        assert OpenCodeAdapter is not None

    def test_opencode_adapter_has_platform_name(self) -> None:
        """OpenCodeAdapter should have platform_name property."""
        from edison.core.adapters.platforms.opencode import OpenCodeAdapter

        adapter = OpenCodeAdapter()
        assert adapter.platform_name == "opencode"

    def test_opencode_adapter_inherits_from_platform_adapter(self) -> None:
        """OpenCodeAdapter should inherit from PlatformAdapter."""
        from edison.core.adapters.base import PlatformAdapter
        from edison.core.adapters.platforms.opencode import OpenCodeAdapter

        assert issubclass(OpenCodeAdapter, PlatformAdapter)

    def test_adapter_loader_can_load_opencode(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AdapterLoader should be able to load the OpenCode adapter."""
        from edison.core.adapters.loader import AdapterLoader

        # Set up minimal project
        (tmp_path / ".edison" / "config").mkdir(parents=True)

        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        loader = AdapterLoader(project_root=tmp_path)

        # OpenCode should be in the list of all adapters
        all_adapters = loader.get_all_adapter_names()
        assert "opencode" in all_adapters


class TestOpenCodeAdapterSyncAll:
    """Test OpenCode adapter sync_all method."""

    def test_sync_all_returns_dict_with_files_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """sync_all should return a dict with 'files' key."""
        from edison.core.adapters.platforms.opencode import OpenCodeAdapter

        # Set up Edison project
        (tmp_path / ".edison" / "config").mkdir(parents=True)

        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        adapter = OpenCodeAdapter(project_root=tmp_path)
        result = adapter.sync_all()

        assert isinstance(result, dict)
        assert "files" in result

    def test_sync_all_creates_opencode_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """sync_all should create .opencode/ directory structure."""
        from edison.core.adapters.platforms.opencode import OpenCodeAdapter

        # Set up Edison project
        (tmp_path / ".edison" / "config").mkdir(parents=True)

        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        adapter = OpenCodeAdapter(project_root=tmp_path)
        adapter.sync_all()

        # .opencode directory should be created
        assert (tmp_path / ".opencode").exists()

    def test_sync_all_generates_plugin_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """sync_all should generate .opencode/plugin/edison.ts."""
        from edison.core.adapters.platforms.opencode import OpenCodeAdapter

        # Set up Edison project
        (tmp_path / ".edison" / "config").mkdir(parents=True)

        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        adapter = OpenCodeAdapter(project_root=tmp_path)
        result = adapter.sync_all()

        plugin_path = tmp_path / ".opencode" / "plugin" / "edison.ts"
        assert plugin_path.exists()
        assert plugin_path in result["files"]

    def test_sync_all_generates_agent_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """sync_all should generate agent definition files."""
        from edison.core.adapters.platforms.opencode import OpenCodeAdapter

        # Set up Edison project
        (tmp_path / ".edison" / "config").mkdir(parents=True)

        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        adapter = OpenCodeAdapter(project_root=tmp_path)
        result = adapter.sync_all()

        # At least one agent file should be generated
        agent_dir = tmp_path / ".opencode" / "agent"
        assert agent_dir.exists()
        agent_files = list(agent_dir.glob("*.md"))
        assert len(agent_files) > 0

    def test_sync_all_generates_command_files(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """sync_all should generate command definition files."""
        from edison.core.adapters.platforms.opencode import OpenCodeAdapter

        # Set up Edison project
        (tmp_path / ".edison" / "config").mkdir(parents=True)

        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        adapter = OpenCodeAdapter(project_root=tmp_path)
        result = adapter.sync_all()

        # At least one command file should be generated
        cmd_dir = tmp_path / ".opencode" / "command"
        assert cmd_dir.exists()
        cmd_files = list(cmd_dir.glob("*.md"))
        assert len(cmd_files) > 0


class TestOpenCodeAdapterIdempotent:
    """Test that OpenCode adapter is idempotent."""

    def test_sync_all_is_idempotent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Running sync_all twice should produce identical results."""
        from edison.core.adapters.platforms.opencode import OpenCodeAdapter

        # Set up Edison project
        (tmp_path / ".edison" / "config").mkdir(parents=True)

        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        adapter = OpenCodeAdapter(project_root=tmp_path)

        # First run
        result1 = adapter.sync_all()
        files1 = [f.resolve() for f in result1["files"]]
        files1_contents = {str(f): f.read_text(encoding="utf-8") for f in files1}

        # Second run
        result2 = adapter.sync_all()
        files2 = [f.resolve() for f in result2["files"]]

        assert set(files1) == set(files2)

        # Content should be identical
        for f in files2:
            assert f.read_text(encoding="utf-8") == files1_contents[str(f)]


class TestOpenCodeAdapterDisabled:
    """Test adapter behavior when disabled."""

    def test_adapter_disabled_by_default_in_composition(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """OpenCode adapter should be disabled by default (opt-in)."""
        from edison.core.adapters.loader import AdapterLoader

        # Set up minimal project
        (tmp_path / ".edison" / "config").mkdir(parents=True)

        monkeypatch.setattr(
            "edison.core.utils.paths.PathResolver.resolve_project_root",
            lambda: tmp_path,
        )

        loader = AdapterLoader(project_root=tmp_path)

        # OpenCode should NOT be in enabled adapters by default
        enabled = loader.get_enabled_adapter_names()
        assert "opencode" not in enabled
