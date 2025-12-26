"""Memory domain models (provider-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class MemoryHit:
    """A provider-agnostic search result."""

    provider_id: str
    text: str
    score: Optional[float] = None
    meta: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "providerId": self.provider_id,
            "text": self.text,
        }
        if self.score is not None:
            out["score"] = self.score
        if self.meta:
            out["meta"] = dict(self.meta)
        return out


__all__ = ["MemoryHit"]

