"""Base classes for composition strategies.

This module provides the foundation for all composition strategies:
- LayerContent: Represents content from a composition layer
- CompositionContext: Context information for composition operations (from context.py)
- CompositionStrategy: Abstract base class for all composition strategies
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# Import unified CompositionContext from central location
from ..context import CompositionContext


@dataclass
class LayerContent:
    """Content from a composition layer.

    Attributes:
        content: The markdown content
        source: Layer identifier ("core" | "pack:{name}" | "project")
        path: Optional source file path
    """

    content: str
    source: str  # "core" | "pack:{name}" | "project"
    path: Optional[Path] = None

    @property
    def is_core(self) -> bool:
        """Check if this is core layer content."""
        return self.source == "core"

    @property
    def is_pack(self) -> bool:
        """Check if this is pack layer content."""
        return self.source.startswith("pack:")

    @property
    def is_project(self) -> bool:
        """Check if this is project layer content."""
        return self.source == "project"

    @property
    def pack_name(self) -> Optional[str]:
        """Get pack name if this is pack layer content."""
        if self.is_pack:
            return self.source.split(":", 1)[1]
        return None


class CompositionStrategy(ABC):
    """Abstract base class for composition strategies.

    All composition strategies must implement the compose() method
    to transform a list of layer contents into final composed output.
    """

    @abstractmethod
    def compose(
        self,
        layers: List[LayerContent],
        context: CompositionContext,
    ) -> str:
        """Compose content from layers.

        Args:
            layers: List of layer content in order (core → packs → user → project)
            context: Composition context with packs and config

        Returns:
            Composed content as string
        """
        ...


__all__ = [
    "CompositionContext",
    "CompositionStrategy",
    "LayerContent",
]
