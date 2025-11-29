from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.io import read_yaml


@dataclass
class PackMetadata:
    name: str
    version: str
    description: str
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    triggers: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    validators: Optional[List[str]] = None
    guidelines: Optional[List[str]] = None
    examples: Optional[List[str]] = None


def load_pack_metadata(pack_path: Path) -> PackMetadata:
    yml = read_yaml(pack_path / "pack.yml", default={})
    raw_triggers = yml.get("triggers") or {}
    trigger_patterns: List[str] = []
    if isinstance(raw_triggers, dict):
        trigger_patterns = list(raw_triggers.get("filePatterns") or [])

    return PackMetadata(
        name=str(yml.get("name", "")),
        version=str(yml.get("version", "")),
        description=str(yml.get("description", "")),
        category=yml.get("category"),
        tags=list(yml.get("tags") or []),
        triggers=trigger_patterns,
        dependencies=list(yml.get("dependencies") or []),
        validators=list(yml.get("validators") or []),
        guidelines=list(yml.get("guidelines") or []),
        examples=list(yml.get("examples") or []),
    )
