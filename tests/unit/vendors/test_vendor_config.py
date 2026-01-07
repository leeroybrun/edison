"""Tests for vendor configuration loading and schema validation.

RED Phase: These tests define expected behavior for vendor config.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import yaml


def write_yaml(path: Path, content: str) -> None:
    """Helper to write YAML content to a file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


class TestVendorConfigSchema:
    """Test vendor configuration schema and loading."""

    def test_vendor_config_loads_from_project_config(self, tmp_path: Path) -> None:
        """Vendor config should load from .edison/config/vendors.yaml."""
        from edison.core.vendors.config import VendorConfig

        # Create minimal Edison project structure
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

        cfg = VendorConfig(repo_root=tmp_path)
        sources = cfg.get_sources()

        assert len(sources) == 1
        assert sources[0].name == "opencode"
        assert sources[0].url == "https://github.com/anthropics/opencode.git"
        assert sources[0].ref == "main"
        assert sources[0].path == "vendors/opencode"

    def test_vendor_config_empty_when_no_vendors_yaml(self, tmp_path: Path) -> None:
        """Vendor config should return empty list when no vendors.yaml exists."""
        from edison.core.vendors.config import VendorConfig

        # Create minimal Edison project structure without vendors.yaml
        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)

        cfg = VendorConfig(repo_root=tmp_path)
        sources = cfg.get_sources()

        assert sources == []

    def test_vendor_config_supports_multiple_sources(self, tmp_path: Path) -> None:
        """Vendor config should support multiple vendor sources."""
        from edison.core.vendors.config import VendorConfig

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://github.com/anthropics/opencode.git
                  ref: v1.0.0
                  path: vendors/opencode
                - name: speckit
                  url: https://github.com/example/speckit.git
                  ref: main
                  path: vendors/speckit
            """,
        )

        cfg = VendorConfig(repo_root=tmp_path)
        sources = cfg.get_sources()

        assert len(sources) == 2
        assert {s.name for s in sources} == {"opencode", "speckit"}

    def test_vendor_config_validates_required_fields(self, tmp_path: Path) -> None:
        """Vendor config should validate that required fields are present."""
        from edison.core.vendors.config import VendorConfig
        from edison.core.vendors.exceptions import VendorConfigError

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  # Missing url, ref, path
            """,
        )

        cfg = VendorConfig(repo_root=tmp_path)
        with pytest.raises(VendorConfigError, match="required"):
            cfg.get_sources()

    def test_vendor_config_rejects_absolute_checkout_path(self, tmp_path: Path) -> None:
        """Vendor config should reject absolute checkout paths."""
        from edison.core.vendors.config import VendorConfig
        from edison.core.vendors.exceptions import VendorConfigError

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
                  path: /tmp/evil
            """,
        )

        cfg = VendorConfig(repo_root=tmp_path)
        with pytest.raises(VendorConfigError, match="must be relative"):
            cfg.get_sources()

    def test_vendor_config_rejects_path_traversal(self, tmp_path: Path) -> None:
        """Vendor config should reject paths that escape the repo root."""
        from edison.core.vendors.config import VendorConfig
        from edison.core.vendors.exceptions import VendorConfigError

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
                  path: ../evil
            """,
        )

        cfg = VendorConfig(repo_root=tmp_path)
        with pytest.raises(VendorConfigError, match="escapes repo root"):
            cfg.get_sources()

    def test_vendor_config_rejects_git_option_injection(self, tmp_path: Path) -> None:
        """Vendor config should reject url/ref values that look like options."""
        from edison.core.vendors.config import VendorConfig
        from edison.core.vendors.exceptions import VendorConfigError

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: --upload-pack=sh
                  ref: --help
                  path: vendors/opencode
            """,
        )

        cfg = VendorConfig(repo_root=tmp_path)
        with pytest.raises(VendorConfigError, match="unsafe url/ref"):
            cfg.get_sources()

    def test_vendor_config_rejects_url_with_embedded_credentials(self, tmp_path: Path) -> None:
        """Vendor config should reject URLs containing embedded credentials."""
        from edison.core.vendors.config import VendorConfig
        from edison.core.vendors.exceptions import VendorConfigError

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: https://token@github.com/anthropics/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )

        cfg = VendorConfig(repo_root=tmp_path)
        with pytest.raises(VendorConfigError, match="credentials"):
            cfg.get_sources()

    def test_vendor_config_rejects_scp_style_credential_urls(self, tmp_path: Path) -> None:
        """Vendor config should reject scp-style URLs with non-git userinfo."""
        from edison.core.vendors.config import VendorConfig
        from edison.core.vendors.exceptions import VendorConfigError

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              sources:
                - name: opencode
                  url: token@github.com:anthropics/opencode.git
                  ref: main
                  path: vendors/opencode
            """,
        )

        cfg = VendorConfig(repo_root=tmp_path)
        with pytest.raises(VendorConfigError, match="credentials"):
            cfg.get_sources()

    def test_vendor_config_rejects_sparse_option_injection(self, tmp_path: Path) -> None:
        """Vendor config should reject sparse paths that look like options."""
        from edison.core.vendors.config import VendorConfig
        from edison.core.vendors.exceptions import VendorConfigError

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
                  sparse:
                    - --bad
            """,
        )

        cfg = VendorConfig(repo_root=tmp_path)
        with pytest.raises(VendorConfigError, match="unsafe sparse path"):
            cfg.get_sources()

    def test_vendor_config_supports_sparse_checkout(self, tmp_path: Path) -> None:
        """Vendor config should support sparse checkout configuration."""
        from edison.core.vendors.config import VendorConfig

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
                  sparse:
                    - src/
                    - docs/
            """,
        )

        cfg = VendorConfig(repo_root=tmp_path)
        sources = cfg.get_sources()

        assert len(sources) == 1
        assert sources[0].sparse == ["src/", "docs/"]

    def test_vendor_config_cache_directory(self, tmp_path: Path) -> None:
        """Vendor config should define cache directory location."""
        from edison.core.vendors.config import VendorConfig

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              cacheDir: ~/.cache/edison/vendors
              sources: []
            """,
        )

        cfg = VendorConfig(repo_root=tmp_path)
        cache_dir = cfg.get_cache_dir()

        # Should expand ~ to home directory
        assert "~" not in str(cache_dir)
        assert cache_dir.name == "vendors"

    def test_vendor_config_rejects_cache_dir_outside_allowed_roots(self, tmp_path: Path) -> None:
        """Vendor config should refuse cacheDir paths outside repo root and safe user cache."""
        from edison.core.vendors.config import VendorConfig
        from edison.core.vendors.exceptions import VendorConfigError

        config_dir = tmp_path / ".edison" / "config"
        config_dir.mkdir(parents=True)
        write_yaml(
            config_dir / "vendors.yaml",
            """
            vendors:
              cacheDir: /tmp/edison-evil
              sources: []
            """,
        )

        cfg = VendorConfig(repo_root=tmp_path)
        with pytest.raises(VendorConfigError, match="cacheDir"):
            cfg.get_cache_dir()


class TestVendorLockFile:
    """Test vendor lock file generation and parsing."""

    def test_lock_entry_sanitizes_url_credentials_on_init(self) -> None:
        """Lock entries should never retain credential-bearing URLs in memory."""
        from edison.core.vendors.lock import VendorLockEntry

        entry = VendorLockEntry(
            name="opencode",
            url="https://token@github.com/anthropics/opencode.git",
            ref="main",
            commit="abc123def456",
            path="vendors/opencode",
        )

        assert "token@" not in entry.url
        assert "github.com/anthropics/opencode.git" in entry.url

    def test_lock_entry_from_dict_validates_required_keys(self) -> None:
        """Lock entry parsing should fail with a clear error when keys are missing."""
        from edison.core.vendors.lock import VendorLockEntry

        with pytest.raises(ValueError, match="Missing required keys"):
            VendorLockEntry.from_dict({"name": "opencode"})

    def test_lock_file_records_resolved_commit(self, tmp_path: Path) -> None:
        """Lock file should record the resolved commit SHA."""
        from edison.core.vendors.lock import VendorLock, VendorLockEntry

        lock = VendorLock(repo_root=tmp_path)
        lock.add_entry(
            VendorLockEntry(
                name="opencode",
                url="https://github.com/anthropics/opencode.git",
                ref="main",
                commit="abc123def456",
                path="vendors/opencode",
            )
        )
        lock.save()

        # Verify lock file was written
        lock_path = tmp_path / ".edison" / "config" / "vendors.lock.yaml"
        assert lock_path.exists()

        # Verify content
        content = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
        assert "vendors" in content
        assert len(content["vendors"]) == 1
        assert content["vendors"][0]["commit"] == "abc123def456"

    def test_lock_file_is_deterministic(self, tmp_path: Path) -> None:
        """Lock file should be deterministically ordered (sorted by name)."""
        from edison.core.vendors.lock import VendorLock, VendorLockEntry

        lock = VendorLock(repo_root=tmp_path)
        # Add in random order
        lock.add_entry(
            VendorLockEntry(
                name="zebra",
                url="https://example.com/zebra.git",
                ref="main",
                commit="zzz",
                path="vendors/zebra",
            )
        )
        lock.add_entry(
            VendorLockEntry(
                name="alpha",
                url="https://example.com/alpha.git",
                ref="main",
                commit="aaa",
                path="vendors/alpha",
            )
        )
        lock.save()

        lock_path = tmp_path / ".edison" / "config" / "vendors.lock.yaml"
        content = yaml.safe_load(lock_path.read_text(encoding="utf-8"))

        # Should be sorted by name
        names = [v["name"] for v in content["vendors"]]
        assert names == ["alpha", "zebra"]

    def test_lock_file_loads_existing(self, tmp_path: Path) -> None:
        """Lock file should load existing entries."""
        from edison.core.vendors.lock import VendorLock

        lock_path = tmp_path / ".edison" / "config" / "vendors.lock.yaml"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        write_yaml(
            lock_path,
            """
            vendors:
              - name: opencode
                url: https://github.com/anthropics/opencode.git
                ref: main
                commit: abc123
                path: vendors/opencode
            """,
        )

        lock = VendorLock(repo_root=tmp_path)
        lock.load()

        entries = lock.get_entries()
        assert len(entries) == 1
        assert entries[0].name == "opencode"
        assert entries[0].commit == "abc123"

    def test_lock_file_redacts_credentials_in_url(self, tmp_path: Path) -> None:
        """Lock file should not persist credential-bearing URLs."""
        from edison.core.vendors.lock import VendorLock, VendorLockEntry

        lock = VendorLock(repo_root=tmp_path)
        lock.add_entry(
            VendorLockEntry(
                name="opencode",
                url="https://token@github.com/anthropics/opencode.git",
                ref="main",
                commit="abc123def456",
                path="vendors/opencode",
            )
        )
        lock.save()

        lock_path = tmp_path / ".edison" / "config" / "vendors.lock.yaml"
        content = yaml.safe_load(lock_path.read_text(encoding="utf-8"))
        stored_url = content["vendors"][0]["url"]
        assert "token@" not in stored_url
        assert "github.com/anthropics/opencode.git" in stored_url


class TestVendorSource:
    """Test VendorSource model."""

    def test_vendor_source_from_dict(self) -> None:
        """VendorSource should be constructible from dict."""
        from edison.core.vendors.models import VendorSource

        data = {
            "name": "opencode",
            "url": "https://github.com/anthropics/opencode.git",
            "ref": "main",
            "path": "vendors/opencode",
        }
        source = VendorSource.from_dict(data)

        assert source.name == "opencode"
        assert source.url == "https://github.com/anthropics/opencode.git"
        assert source.ref == "main"
        assert source.path == "vendors/opencode"
        assert source.sparse is None  # Optional field

    def test_vendor_source_to_dict(self) -> None:
        """VendorSource should serialize to dict."""
        from edison.core.vendors.models import VendorSource

        source = VendorSource(
            name="opencode",
            url="https://github.com/anthropics/opencode.git",
            ref="main",
            path="vendors/opencode",
            sparse=["src/"],
        )
        data = source.to_dict()

        assert data["name"] == "opencode"
        assert data["sparse"] == ["src/"]

    def test_vendor_source_immutable(self) -> None:
        """VendorSource should be immutable (frozen dataclass)."""
        from edison.core.vendors.models import VendorSource

        source = VendorSource(
            name="opencode",
            url="https://github.com/anthropics/opencode.git",
            ref="main",
            path="vendors/opencode",
        )

        with pytest.raises(AttributeError):
            source.name = "changed"  # type: ignore[misc]
