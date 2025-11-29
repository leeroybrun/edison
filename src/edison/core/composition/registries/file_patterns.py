"""
File pattern rule registry with pack awareness.

This module keeps core free of tech-specific file pattern rules by loading
generic patterns from the core rules directory and merging in pack-provided
patterns only when those packs are active.

Moved from core.rules.file_patterns to composition.registries for architectural
coherence - file pattern composition follows the same patterns as other registries.

Architecture:
    BaseEntityManager
    └── BaseRegistry
        └── FilePatternRegistry (this module)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.entity import BaseRegistry
from edison.data import get_data_path
from edison.core.utils.paths import PathResolver, EdisonPathError
from edison.core.utils.paths import get_project_config_dir


class FilePatternRegistry(BaseRegistry[Dict[str, Any]]):
    """Load file pattern rules from core plus optional packs.
    
    Extends BaseRegistry with file-pattern-specific functionality:
    - YAML-based pattern loading from directories
    - Pack-aware pattern composition
    """
    
    entity_type: str = "file_pattern"

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        try:
            resolved_root = PathResolver.resolve_project_root() if repo_root is None else Path(repo_root)
        except (EdisonPathError, ValueError):
            # Fall back to cwd when path resolution fails (defensive guard for tests)
            resolved_root = Path.cwd()
        
        super().__init__(resolved_root)

        self.core_rules_dir = self._resolve_core_rules_dir()
        self.pack_roots = self._resolve_pack_roots()
    
    # ------- BaseRegistry Interface Implementation -------
    
    def discover_core(self) -> Dict[str, Dict[str, Any]]:
        """Discover core file pattern rules."""
        rules = self.load_core_rules()
        return {rule.get("name", rule.get("_path", f"rule-{i}")): rule for i, rule in enumerate(rules)}
    
    def discover_packs(self, packs: List[str]) -> Dict[str, Dict[str, Any]]:
        """Discover file pattern rules from active packs."""
        result: Dict[str, Dict[str, Any]] = {}
        for pack in packs:
            rules = self.load_pack_rules(pack)
            for i, rule in enumerate(rules):
                rule_name = rule.get("name", f"{pack}-rule-{i}")
                result[rule_name] = rule
        return result
    
    def discover_project(self) -> Dict[str, Dict[str, Any]]:
        """Discover project-level file pattern overrides."""
        # File patterns are in core/packs, not project-level
        return {}
    
    def exists(self, name: str) -> bool:
        """Check if a file pattern rule exists in core."""
        return name in self.discover_core()
    
    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a file pattern rule by name from core."""
        return self.discover_core().get(name)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all file pattern rules from core."""
        return list(self.discover_core().values())
    
    # ------- Path Resolution -------

    def _resolve_core_rules_dir(self) -> Path:
        candidate = get_project_config_dir(self.project_root, create=False) / "core" / "rules" / "file_patterns"
        if candidate.exists():
            return candidate
        return get_data_path("rules") / "file_patterns"

    def _resolve_pack_roots(self) -> List[Path]:
        roots: List[Path] = []
        project_packs = get_project_config_dir(self.project_root, create=False) / "packs"
        if project_packs.exists():
            roots.append(project_packs)

        data_packs = get_data_path("packs")
        if data_packs.exists() and data_packs not in roots:
            roots.append(data_packs)

        return roots

    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        from edison.core.utils.io import read_yaml
        data = read_yaml(path, raise_on_error=True) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path} must parse to a mapping")
        data["_path"] = str(path)
        return data

    def _load_dir(self, dir_path: Path, origin: str) -> List[Dict[str, Any]]:
        if not dir_path.exists():
            return []

        rules: List[Dict[str, Any]] = []
        for path in sorted(dir_path.glob("*.yaml")):
            payload = self._load_yaml(path)
            payload["_origin"] = origin
            rules.append(payload)
        return rules

    def load_core_rules(self) -> List[Dict[str, Any]]:
        """Return file pattern rules bundled with core (generic only)."""
        return self._load_dir(self.core_rules_dir, "core")

    def load_pack_rules(self, pack_name: str) -> List[Dict[str, Any]]:
        """Return file pattern rules from the given pack if present."""
        for root in self.pack_roots:
            candidate = root / pack_name / "rules" / "file_patterns"
            if candidate.exists():
                return self._load_dir(candidate, f"pack:{pack_name}")
        return []

    def compose(self, *, active_packs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Compose core + pack file pattern rules respecting active packs."""
        rules = list(self.load_core_rules())
        for pack in active_packs or []:
            rules.extend(self.load_pack_rules(pack))
        return rules


__all__ = ["FilePatternRegistry"]
