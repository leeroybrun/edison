"""Base class for platform adapter components.

AdapterComponent provides a base for platform-AGNOSTIC components
that can be reused across different platform adapters.

Components are responsible for:
- Composing specific types of content (hooks, commands, settings, etc.)
- Syncing composed content to output directories
- Accessing adapter configuration and utilities

This follows the Composition over Inheritance principle.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from edison.core.adapters.base import PlatformAdapter
    from edison.core.composition.output.writer import CompositionFileWriter


@dataclass(frozen=True)
class AdapterContext:
    """Shared context passed to adapter components."""

    project_root: Path
    project_dir: Path
    core_dir: Path
    bundled_packs_dir: Path
    project_packs_dir: Path
    cfg_mgr: Any
    config: Dict[str, Any]
    writer: "CompositionFileWriter"
    adapter: "PlatformAdapter"


class AdapterComponent(ABC):
    """Base class for platform adapter components.

    Components are platform-AGNOSTIC pieces of functionality that can be
    composed into platform adapters. Examples:
    - HookComponent: Compose IDE hooks
    - CommandComponent: Compose IDE commands
    - SettingsComponent: Compose IDE settings

    Components have access to the adapter's:
    - config: Configuration dictionary
    - writer: File writer for output
    - All other adapter properties and methods

    Subclasses must implement:
    - compose(): Generate the component content
    - sync(): Write the component content to disk

    Example:
        class MyComponent(AdapterComponent):
            def compose(self) -> str:
                return "my content"

            def sync(self, output_dir: Path) -> List[Path]:
                path = output_dir / "my-file.txt"
                self.writer.write_text(path, self.compose())
                return [path]
    """

    def __init__(self, context: AdapterContext) -> None:
        """Initialize component with adapter context."""
        self.context = context
        self.adapter = getattr(context, "adapter", None)

    # =========================================================================
    # Adapter Property Access
    # =========================================================================

    @property
    def config(self) -> Dict[str, Any]:
        """Access adapter configuration.

        Returns:
            Configuration dictionary from the adapter.
        """
        return self.context.config

    @property
    def writer(self) -> "CompositionFileWriter":
        """Access adapter file writer.

        Returns:
            CompositionFileWriter instance from the adapter.
        """
        return self.context.writer

    # ---------------------------------------------------------------------
    # Delegation helpers (CompositionBase passthrough)
    # ---------------------------------------------------------------------

    def get_active_packs(self) -> List[str]:
        """Delegate to adapter's active packs helper."""
        if self.adapter is None:
            return []
        return self.adapter.get_active_packs()

    def merge_definitions(
        self,
        base: Dict[str, Dict[str, Any]],
        new_defs: Dict[str, Dict[str, Any]] | List[Dict[str, Any]],
        id_key: str = "id",
    ) -> Dict[str, Dict[str, Any]]:
        """Delegate to adapter merge helpers.

        CompositionBase.merge_definitions accepts a key_getter; to keep a
        simple API for components we use _merge_definitions_by_id under the
        hood when an ``id_key`` is provided.
        """
        if self.adapter is None:
            raise RuntimeError("Adapter not attached to component")
        # Prefer the dedicated helper when id_key is provided
        return self.adapter._merge_definitions_by_id(base, new_defs, id_key=id_key)

    def _merge_definitions_by_id(
        self,
        base: Dict[str, Dict[str, Any]],
        new_defs: List[Dict[str, Any]],
        *,
        id_key: str = "id",
    ) -> Dict[str, Dict[str, Any]]:
        """Delegates to adapter's protected merge helper."""
        if self.adapter is None:
            raise RuntimeError("Adapter not attached to component")
        return self.adapter._merge_definitions_by_id(base, new_defs, id_key=id_key)

    @property
    def cfg_mgr(self) -> Any:
        """Access ConfigManager."""
        return self.context.cfg_mgr

    @property
    def core_dir(self) -> Path:
        return self.context.core_dir

    @property
    def bundled_packs_dir(self) -> Path:
        return self.context.bundled_packs_dir

    @property
    def project_packs_dir(self) -> Path:
        return self.context.project_packs_dir

    @property
    def project_dir(self) -> Path:
        return self.context.project_dir

    @property
    def project_root(self) -> Path:
        return self.context.project_root

    @property
    def active_packs(self) -> List[str]:
        """Active packs from the parent adapter."""
        if self.adapter:
            try:
                return self.adapter.get_active_packs()
            except Exception:
                return []
        return []

    # =========================================================================
    # Abstract Methods
    # =========================================================================

    @abstractmethod
    def compose(self) -> Any:
        """Compose the component content.

        This method should generate the content for this component
        (e.g., hook definitions, command definitions, settings).

        Returns:
            The composed content. Type varies by component.
        """
        pass

    @abstractmethod
    def sync(self, output_dir: Path) -> List[Path]:
        """Sync the component content to disk.

        This method should write the composed content to the output
        directory and return the list of written files.

        Args:
            output_dir: Directory to write output files to.

        Returns:
            List of paths to files that were written.
        """
        pass


__all__ = ["AdapterComponent"]
