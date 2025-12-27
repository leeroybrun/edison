from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PackRoot:
    """A single pack root (bundled, company, user, project, etc)."""

    kind: str
    path: Path


__all__ = ["PackRoot"]

