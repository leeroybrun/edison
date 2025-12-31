from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ShimDefinition:
    """Declarative shim definition used for rendering."""

    id: str
    enabled: bool = True
    description: str = ""
    bin_name: str = ""
    template: str = ""
    contexts: list[str] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    def applies_to(self, context: str) -> bool:
        if not self.enabled:
            return False
        if not self.contexts:
            return True
        return context in self.contexts or "*" in self.contexts

