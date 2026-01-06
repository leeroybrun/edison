"""Tests for vendor adapter interface (mount discovery).

RED Phase: These tests define expected behavior for vendor adapters.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest


def write_file(path: Path, content: str) -> None:
    """Helper to write content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


def write_yaml(path: Path, content: str) -> None:
    """Helper to write YAML content to a file."""
    write_file(path, content)


class TestVendorAdapter:
    """Test vendor adapter protocol and base implementation."""

    def test_adapter_protocol_defines_required_methods(self) -> None:
        """Vendor adapter protocol should define discover_mounts."""
        from edison.core.vendors.adapters import VendorAdapter, BaseVendorAdapter

        # Check protocol has required method
        assert hasattr(VendorAdapter, "discover_mounts")
        # vendor_name is defined on the base class, not the protocol
        assert hasattr(BaseVendorAdapter, "vendor_name")

    def test_adapter_discover_mounts_returns_mount_points(
        self, tmp_path: Path
    ) -> None:
        """Adapter should return list of mount points from vendor."""
        from edison.core.vendors.adapters import BaseVendorAdapter
        from edison.core.vendors.models import VendorMount

        class TestAdapter(BaseVendorAdapter):
            vendor_name = "test-vendor"

            def discover_mounts(self) -> list[VendorMount]:
                return [
                    VendorMount(
                        source_path="prompts/",
                        target_path=".codex/prompts/",
                        mount_type="symlink",
                    )
                ]

        adapter = TestAdapter(vendor_path=tmp_path / "vendors" / "test")
        mounts = adapter.discover_mounts()

        assert len(mounts) == 1
        assert mounts[0].source_path == "prompts/"
        assert mounts[0].target_path == ".codex/prompts/"


class TestOpencodeAdapter:
    """Test OpenCode-specific vendor adapter."""

    def test_opencode_adapter_discovers_prompts(self, tmp_path: Path) -> None:
        """OpenCode adapter should discover prompts mount."""
        from edison.core.vendors.adapters.opencode import OpencodeAdapter

        # Create vendor directory structure
        vendor_path = tmp_path / "vendors" / "opencode"
        vendor_path.mkdir(parents=True)

        # OpenCode has prompts at prompts/
        (vendor_path / "prompts").mkdir()
        (vendor_path / "prompts" / "default.md").write_text("# Prompt", encoding="utf-8")

        adapter = OpencodeAdapter(vendor_path=vendor_path)
        mounts = adapter.discover_mounts()

        # Should discover prompts
        prompt_mounts = [m for m in mounts if "prompts" in m.source_path]
        assert len(prompt_mounts) >= 1

    def test_opencode_adapter_discovers_configs(self, tmp_path: Path) -> None:
        """OpenCode adapter should discover config mounts."""
        from edison.core.vendors.adapters.opencode import OpencodeAdapter

        vendor_path = tmp_path / "vendors" / "opencode"
        vendor_path.mkdir(parents=True)

        # OpenCode has configs
        (vendor_path / "config").mkdir()
        (vendor_path / "config" / "defaults.yaml").write_text("key: value", encoding="utf-8")

        adapter = OpencodeAdapter(vendor_path=vendor_path)
        mounts = adapter.discover_mounts()

        # Should discover configs
        config_mounts = [m for m in mounts if "config" in m.source_path]
        assert len(config_mounts) >= 1


class TestAdapterRegistry:
    """Test vendor adapter registry."""

    def test_registry_returns_adapter_for_known_vendor(self) -> None:
        """Registry should return appropriate adapter for known vendors."""
        from edison.core.vendors.adapters import get_adapter_for_vendor

        adapter_class = get_adapter_for_vendor("opencode")
        assert adapter_class is not None
        assert adapter_class.vendor_name == "opencode"

    def test_registry_returns_generic_adapter_for_unknown(self) -> None:
        """Registry should return generic adapter for unknown vendors."""
        from edison.core.vendors.adapters import get_adapter_for_vendor, GenericVendorAdapter

        adapter_class = get_adapter_for_vendor("unknown-vendor")
        assert adapter_class == GenericVendorAdapter

    def test_registry_can_register_custom_adapter(self) -> None:
        """Registry should allow registering custom adapters."""
        from edison.core.vendors.adapters import (
            register_adapter,
            get_adapter_for_vendor,
            BaseVendorAdapter,
        )
        from edison.core.vendors.models import VendorMount

        class CustomAdapter(BaseVendorAdapter):
            vendor_name = "custom"

            def discover_mounts(self) -> list[VendorMount]:
                return []

        register_adapter(CustomAdapter)

        adapter_class = get_adapter_for_vendor("custom")
        assert adapter_class == CustomAdapter


class TestVendorMount:
    """Test VendorMount model."""

    def test_mount_model_fields(self) -> None:
        """VendorMount should have required fields."""
        from edison.core.vendors.models import VendorMount

        mount = VendorMount(
            source_path="src/prompts/",
            target_path=".prompts/",
            mount_type="symlink",
        )

        assert mount.source_path == "src/prompts/"
        assert mount.target_path == ".prompts/"
        assert mount.mount_type == "symlink"

    def test_mount_supports_copy_type(self) -> None:
        """VendorMount should support copy mount type."""
        from edison.core.vendors.models import VendorMount

        mount = VendorMount(
            source_path="configs/",
            target_path=".configs/",
            mount_type="copy",
        )

        assert mount.mount_type == "copy"

    def test_mount_immutable(self) -> None:
        """VendorMount should be immutable."""
        from edison.core.vendors.models import VendorMount

        mount = VendorMount(
            source_path="src/",
            target_path="dst/",
            mount_type="symlink",
        )

        with pytest.raises(AttributeError):
            mount.source_path = "changed/"  # type: ignore[misc]


class TestMountExecutor:
    """Test mount execution (symlink/copy creation)."""

    def test_executor_creates_symlink(self, tmp_path: Path) -> None:
        """Mount executor should create symlinks."""
        from edison.core.vendors.mount import MountExecutor
        from edison.core.vendors.models import VendorMount

        vendor_path = tmp_path / "vendors" / "test"
        vendor_path.mkdir(parents=True)
        (vendor_path / "src").mkdir()
        (vendor_path / "src" / "file.txt").write_text("content", encoding="utf-8")

        mount = VendorMount(
            source_path="src/",
            target_path="linked/",
            mount_type="symlink",
        )

        executor = MountExecutor(repo_root=tmp_path)
        result = executor.execute(mount, vendor_path=vendor_path)

        assert result.success
        target = tmp_path / "linked"
        assert target.is_symlink()
        assert (target / "file.txt").read_text() == "content"

    def test_executor_creates_copy(self, tmp_path: Path) -> None:
        """Mount executor should create copies."""
        from edison.core.vendors.mount import MountExecutor
        from edison.core.vendors.models import VendorMount

        vendor_path = tmp_path / "vendors" / "test"
        vendor_path.mkdir(parents=True)
        (vendor_path / "src").mkdir()
        (vendor_path / "src" / "file.txt").write_text("content", encoding="utf-8")

        mount = VendorMount(
            source_path="src/",
            target_path="copied/",
            mount_type="copy",
        )

        executor = MountExecutor(repo_root=tmp_path)
        result = executor.execute(mount, vendor_path=vendor_path)

        assert result.success
        target = tmp_path / "copied"
        assert target.is_dir()
        assert not target.is_symlink()
        assert (target / "file.txt").read_text() == "content"

    def test_executor_handles_existing_target(self, tmp_path: Path) -> None:
        """Mount executor should handle existing target gracefully."""
        from edison.core.vendors.mount import MountExecutor
        from edison.core.vendors.models import VendorMount

        vendor_path = tmp_path / "vendors" / "test"
        vendor_path.mkdir(parents=True)
        (vendor_path / "src").mkdir()
        (vendor_path / "src" / "file.txt").write_text("content", encoding="utf-8")

        # Pre-create target
        target = tmp_path / "linked"
        target.mkdir()
        (target / "existing.txt").write_text("old", encoding="utf-8")

        mount = VendorMount(
            source_path="src/",
            target_path="linked/",
            mount_type="symlink",
        )

        executor = MountExecutor(repo_root=tmp_path)
        result = executor.execute(mount, vendor_path=vendor_path, force=True)

        assert result.success
        assert target.is_symlink()

    def test_executor_dry_run(self, tmp_path: Path) -> None:
        """Mount executor should support dry-run mode."""
        from edison.core.vendors.mount import MountExecutor
        from edison.core.vendors.models import VendorMount

        vendor_path = tmp_path / "vendors" / "test"
        vendor_path.mkdir(parents=True)
        (vendor_path / "src").mkdir()

        mount = VendorMount(
            source_path="src/",
            target_path="linked/",
            mount_type="symlink",
        )

        executor = MountExecutor(repo_root=tmp_path)
        result = executor.execute(mount, vendor_path=vendor_path, dry_run=True)

        assert result.would_create
        target = tmp_path / "linked"
        assert not target.exists()

    def test_executor_rejects_target_outside_repo_root(self, tmp_path: Path) -> None:
        """Mount executor should refuse target paths that escape repo_root."""
        from edison.core.vendors.mount import MountExecutor
        from edison.core.vendors.models import VendorMount

        repo_root = tmp_path / "repo"
        vendor_path = repo_root / "vendors" / "test"
        vendor_path.mkdir(parents=True)
        (vendor_path / "src").mkdir()
        (vendor_path / "src" / "file.txt").write_text("content", encoding="utf-8")

        mount = VendorMount(
            source_path="src/",
            target_path="../escape/",
            mount_type="symlink",
        )

        executor = MountExecutor(repo_root=repo_root)
        result = executor.execute(mount, vendor_path=vendor_path)

        assert result.success is False
        assert "outside repo root" in (result.error or "").lower()
        assert not (tmp_path / "escape").exists()

    def test_executor_rejects_source_outside_vendor_root(self, tmp_path: Path) -> None:
        """Mount executor should refuse source paths that escape vendor_path."""
        from edison.core.vendors.mount import MountExecutor
        from edison.core.vendors.models import VendorMount

        repo_root = tmp_path / "repo"
        vendor_path = repo_root / "vendors" / "test"
        vendor_path.mkdir(parents=True)
        (repo_root / "vendors" / "escape-src").mkdir(parents=True)
        (repo_root / "vendors" / "escape-src" / "file.txt").write_text("content", encoding="utf-8")

        mount = VendorMount(
            source_path="../escape-src/",
            target_path="linked/",
            mount_type="symlink",
        )

        executor = MountExecutor(repo_root=repo_root)
        result = executor.execute(mount, vendor_path=vendor_path)

        assert result.success is False
        assert "outside vendor root" in (result.error or "").lower()
        assert not (repo_root / "linked").exists()

    def test_executor_copy_rejects_symlinks_outside_vendor_root(self, tmp_path: Path) -> None:
        """Copy mounts should fail if the source tree contains symlinks escaping vendor root."""
        from edison.core.vendors.mount import MountExecutor
        from edison.core.vendors.models import VendorMount

        repo_root = tmp_path / "repo"
        vendor_path = repo_root / "vendors" / "test"
        src_dir = vendor_path / "src"
        src_dir.mkdir(parents=True)

        outside = tmp_path / "outside"
        outside.mkdir(parents=True)
        (outside / "secret.txt").write_text("secret", encoding="utf-8")

        # Create a symlink within the vendor tree that escapes the vendor root.
        (src_dir / "leak").symlink_to(outside / "secret.txt")

        mount = VendorMount(
            source_path="src/",
            target_path="copied/",
            mount_type="copy",
        )

        executor = MountExecutor(repo_root=repo_root)
        result = executor.execute(mount, vendor_path=vendor_path)

        assert result.success is False
        assert "symlink" in (result.error or "").lower()
        assert not (repo_root / "copied").exists()

    def test_executor_copy_rejects_broken_symlinks(self, tmp_path: Path) -> None:
        """Copy mounts should fail with a clear error on broken symlinks."""
        from edison.core.vendors.mount import MountExecutor
        from edison.core.vendors.models import VendorMount

        repo_root = tmp_path / "repo"
        vendor_path = repo_root / "vendors" / "test"
        src_dir = vendor_path / "src"
        src_dir.mkdir(parents=True)

        # Create a broken symlink within the vendor tree.
        (src_dir / "broken").symlink_to(vendor_path / "missing.txt")

        mount = VendorMount(
            source_path="src/",
            target_path="copied/",
            mount_type="copy",
        )

        executor = MountExecutor(repo_root=repo_root)
        result = executor.execute(mount, vendor_path=vendor_path)

        assert result.success is False
        assert "broken symlink" in (result.error or "").lower()
        assert not (repo_root / "copied").exists()


class TestVendorMountDiscovery:
    """Test full vendor mount discovery flow."""

    def test_discover_all_vendor_mounts(self, tmp_path: Path) -> None:
        """Should discover mounts from all configured vendors."""
        from edison.core.vendors.discovery import VendorMountDiscovery

        # Set up vendor
        vendor_path = tmp_path / "vendors" / "opencode"
        vendor_path.mkdir(parents=True)
        (vendor_path / "prompts").mkdir()
        (vendor_path / "prompts" / "default.md").write_text("# Prompt", encoding="utf-8")

        # Set up config
        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/anthropics/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )

        discovery = VendorMountDiscovery(repo_root=tmp_path)
        mounts = discovery.discover_all()

        assert len(mounts) >= 1

    def test_discover_mounts_for_single_vendor(self, tmp_path: Path) -> None:
        """Should discover mounts for a specific vendor."""
        from edison.core.vendors.discovery import VendorMountDiscovery

        vendor_path = tmp_path / "vendors" / "opencode"
        vendor_path.mkdir(parents=True)
        (vendor_path / "prompts").mkdir()

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/anthropics/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )

        discovery = VendorMountDiscovery(repo_root=tmp_path)
        mounts = discovery.discover_for_vendor("opencode")

        assert isinstance(mounts, list)
