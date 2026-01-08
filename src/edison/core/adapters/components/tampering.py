"""Platform-agnostic tampering deny rules component.

Provides a DenyRules class that generates deny rules from TamperingConfig.
Platform adapters consume these rules and translate them into platform-specific
settings (e.g., Claude permissions, Cursor deny patterns, etc.).

The protected directory path is defined ONCE in TamperingConfig and consumed
by all platforms through this shared component - no per-platform hardcoding.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from edison.core.config.domains.tampering import TamperingConfig


@dataclass(frozen=True, slots=True)
class DenyRules:
    """Platform-agnostic deny rules for tampering protection.

    This class represents abstract deny rules that can be translated into
    platform-specific permission formats. The protected paths are resolved
    from TamperingConfig and stored as relative paths.

    Attributes:
        deny_paths: List of paths that should be denied write/edit access.
    """

    deny_paths: List[Path] = field(default_factory=list)

    @classmethod
    def from_tampering_config(cls, tampering_config: "TamperingConfig") -> "DenyRules":
        """Create DenyRules from a TamperingConfig instance.

        Args:
            tampering_config: TamperingConfig instance to read settings from.

        Returns:
            DenyRules instance. If tampering is disabled, returns empty rules.
        """
        if not tampering_config.enabled:
            return cls(deny_paths=[])

        # Get the protected directory path
        protected_dir = tampering_config.protected_dir

        # Convert to relative path for platform-agnostic representation
        # If it's absolute, make it relative to repo root
        repo_root = tampering_config.repo_root
        try:
            if protected_dir.is_absolute():
                relative_path = protected_dir.relative_to(repo_root)
            else:
                relative_path = protected_dir
        except ValueError:
            # Path is not under repo_root, use as-is
            relative_path = protected_dir

        return cls(deny_paths=[relative_path])

    def is_empty(self) -> bool:
        """Check if deny rules are empty (no paths to deny).

        Returns:
            True if there are no deny paths, False otherwise.
        """
        return len(self.deny_paths) == 0

    def to_claude_deny_permissions(self) -> List[str]:
        """Convert deny rules to Claude Code permission format.

        Generates deny permission strings for Claude Code's settings.json
        permissions.deny array.

        Returns:
            List of Claude-compatible deny permission strings.
        """
        permissions: List[str] = []

        for path in self.deny_paths:
            # Normalize path string (use ./ prefix and /** suffix for glob patterns)
            path_str = str(path)
            if not path_str.startswith("./"):
                path_str = "./" + path_str

            # Add deny rules for Write and Edit operations
            permissions.append(f"Edit({path_str}/**)")
            permissions.append(f"Write({path_str}/**)")

        return permissions


__all__ = ["DenyRules"]
