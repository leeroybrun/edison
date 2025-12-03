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
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from edison.core.adapters.base import PlatformAdapter
    from edison.core.composition.output.writer import CompositionFileWriter


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

    def __init__(self, adapter: "PlatformAdapter") -> None:
        """Initialize component with parent adapter.

        Args:
            adapter: The platform adapter this component belongs to.
        """
        self.adapter = adapter

    # =========================================================================
    # Adapter Property Access
    # =========================================================================

    @property
    def config(self) -> Dict[str, Any]:
        """Access adapter configuration.

        Returns:
            Configuration dictionary from the adapter.
        """
        return self.adapter.config

    @property
    def writer(self) -> "CompositionFileWriter":
        """Access adapter file writer.

        Returns:
            CompositionFileWriter instance from the adapter.
        """
        return self.adapter.writer

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
