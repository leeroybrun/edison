"""Vendor configuration loading.

Loads vendor configuration from .edison/config/vendors.yaml
and provides access to vendor sources and settings.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from edison.core.vendors.exceptions import VendorConfigError
from edison.core.vendors.models import VendorSource


class VendorConfig:
    """Load and access vendor configuration.

    Configuration is read from .edison/config/vendors.yaml in the project.
    """

    def __init__(self, repo_root: Path) -> None:
        """Initialize vendor config.

        Args:
            repo_root: Path to repository root
        """
        self.repo_root = repo_root
        self._config: dict[str, Any] | None = None

    @property
    def config_path(self) -> Path:
        """Path to vendors.yaml configuration file."""
        return self.repo_root / ".edison" / "config" / "vendors.yaml"

    def _load(self) -> dict[str, Any]:
        """Load configuration from file.

        Returns:
            Configuration dictionary, empty if file doesn't exist
        """
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            self._config = {}
            return self._config

        import yaml

        content = self.config_path.read_text(encoding="utf-8")
        self._config = yaml.safe_load(content) or {}
        return self._config

    def get_sources(self) -> list[VendorSource]:
        """Get list of configured vendor sources.

        Returns:
            List of VendorSource objects

        Raises:
            VendorConfigError: If required fields are missing
        """
        config = self._load()
        vendors = config.get("vendors", {})
        sources_data = vendors.get("sources", [])

        if not sources_data:
            return []

        sources: list[VendorSource] = []
        for item in sources_data:
            # Validate required fields
            required = ["name", "url", "ref", "path"]
            missing = [f for f in required if f not in item or not item[f]]
            if missing:
                raise VendorConfigError(
                    f"Vendor source missing required fields: {', '.join(missing)}"
                )

            self._validate_source_item(item)
            sources.append(VendorSource.from_dict(item))

        return sources

    def _validate_source_item(self, item: dict[str, Any]) -> None:
        """Validate a vendor source config item.

        This is defense-in-depth against unsafe values in `.edison/config/vendors.yaml`.
        """
        name = str(item.get("name", "")).strip()
        url = str(item.get("url", "")).strip()
        ref = str(item.get("ref", "")).strip()
        path_str = str(item.get("path", "")).strip()

        if any(x.startswith("-") for x in (url, ref)):
            raise VendorConfigError(
                f"Vendor source '{name}' has unsafe url/ref (must not start with '-')."
            )
        if any(any(ch.isspace() for ch in x) for x in (url, ref)):
            raise VendorConfigError(
                f"Vendor source '{name}' has unsafe url/ref (must not contain whitespace)."
            )

        # Disallow embedded credentials in URLs (e.g., https://token@host/repo.git).
        # Use SSH remotes or a credential manager instead.
        if "://" in url:
            from urllib.parse import urlsplit

            parts = urlsplit(url)
            if parts.password is not None:
                raise VendorConfigError(
                    f"Vendor source '{name}' has unsafe url (must not include credentials)."
                )
            if parts.username is not None and not (parts.scheme == "ssh" and parts.username == "git"):
                raise VendorConfigError(
                    f"Vendor source '{name}' has unsafe url (must not include credentials)."
                )
        else:
            # SSH scp-style URLs like git@github.com:org/repo.git are allowed only for the
            # standard non-secret user ("git"). Reject token@host:path style URLs.
            import re

            m = re.match(r"(?P<user>[^@\s/]+)@(?P<host>[^:\s/]+):", url)
            if m and m.group("user") != "git":
                raise VendorConfigError(
                    f"Vendor source '{name}' has unsafe url (must not include credentials)."
                )

        # Path must be relative and confined to repo_root.
        path_obj = Path(path_str)
        if path_obj.is_absolute():
            raise VendorConfigError(
                f"Vendor source '{name}' has unsafe path '{path_str}' (must be relative)."
            )
        if path_str.startswith("~"):
            raise VendorConfigError(
                f"Vendor source '{name}' has unsafe path '{path_str}' (must not start with '~')."
            )

        repo_root_resolved = self.repo_root.resolve()
        checkout_resolved = (self.repo_root / path_obj).resolve()
        if not checkout_resolved.is_relative_to(repo_root_resolved):
            raise VendorConfigError(
                f"Vendor source '{name}' has unsafe path '{path_str}' (escapes repo root)."
            )
        if checkout_resolved == repo_root_resolved:
            raise VendorConfigError(
                f"Vendor source '{name}' has unsafe path '{path_str}' (must not be repo root)."
            )

        sparse = item.get("sparse")
        if sparse is not None:
            if not isinstance(sparse, list):
                raise VendorConfigError(
                    f"Vendor source '{name}' has invalid sparse config (must be a list)."
                )
            for p in sparse:
                s = str(p).strip()
                if not s:
                    continue
                if s.startswith("-"):
                    raise VendorConfigError(
                        f"Vendor source '{name}' has unsafe sparse path '{s}' (must not start with '-')."
                    )

    def get_source_by_name(self, name: str) -> VendorSource | None:
        """Get a specific vendor source by name.

        Args:
            name: Vendor name to find

        Returns:
            VendorSource if found, None otherwise
        """
        for source in self.get_sources():
            if source.name == name:
                return source
        return None

    def get_cache_dir(self) -> Path:
        """Get vendor cache directory.

        Returns:
            Path to cache directory (expanded from ~ if needed)
        """
        config = self._load()
        vendors = config.get("vendors", {})
        cache_dir = vendors.get("cacheDir", "~/.cache/edison/vendors")

        # Expand ~ to home directory, and treat relative cacheDir as repo-root-relative.
        raw = Path(cache_dir).expanduser()
        path = raw if raw.is_absolute() else (self.repo_root / raw)

        # Defense-in-depth: refuse cacheDir outside repo root or the default user cache base.
        # This avoids destructive operations (e.g., vendor gc) targeting arbitrary paths from a repo-provided config.
        resolved = path.resolve()
        repo_root_resolved = self.repo_root.resolve()
        default_user_cache = Path("~/.cache/edison/vendors").expanduser().resolve()

        if not (resolved.is_relative_to(repo_root_resolved) or resolved.is_relative_to(default_user_cache)):
            raise VendorConfigError(
                f"Vendor cacheDir '{path}' is unsafe (must be within repo root or {default_user_cache})."
            )

        return path


__all__ = ["VendorConfig"]
