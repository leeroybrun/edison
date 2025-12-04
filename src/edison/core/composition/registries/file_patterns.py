"""
File pattern rule registry with pack awareness.

This module keeps core free of tech-specific file pattern rules by loading
generic patterns from the bundled rules directory and merging in pack-provided
patterns only when those packs are active.

Architecture:
    - Bundled file patterns: edison.data/rules/file_patterns/ (ALWAYS)
    - Pack patterns: bundled packs + .edison/packs/<pack>/rules/file_patterns/
    - Project overrides: .edison/rules/file_patterns/ (optional)
    - NO .edison/core/ - that is legacy

    BaseEntityManager
    └── BaseRegistry
        └── FilePatternRegistry (this module) + YamlLayerMixin
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from ._registry_base import BaseRegistry
from edison.core.composition.core.yaml_layer import YamlLayerMixin
from edison.data import get_data_path
from edison.core.utils.paths import PathResolver, EdisonPathError
from edison.core.utils.paths import get_project_config_dir


class FilePatternRegistry(YamlLayerMixin, BaseRegistry[Dict[str, Any]]):
    """Load file pattern rules from bundled core plus optional packs.

    Extends BaseRegistry with file-pattern-specific functionality:
    - YAML-based pattern loading from directories (via YamlLayerMixin)
    - Pack-aware pattern composition

    Architecture:
    - Core patterns: ALWAYS from bundled edison.data/rules/file_patterns/
    - Pack patterns: bundled packs + project packs
    - NO .edison/core/ - that is legacy
    """
    
    entity_type: str = "file_pattern"

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        try:
            resolved_root = PathResolver.resolve_project_root() if repo_root is None else Path(repo_root)
        except (EdisonPathError, ValueError):
            # Fall back to cwd when path resolution fails (defensive guard for tests)
            resolved_root = Path.cwd()

        super().__init__(resolved_root)

        # Note: bundled_packs_dir, project_packs_dir, project_dir are inherited from BaseRegistry

        # Core rules are ALWAYS from bundled data
        self.core_rules_dir = get_data_path("rules") / "file_patterns"

        # Project-level file pattern overrides (use inherited project_dir)
        self.project_rules_dir = self.project_dir / "rules" / "file_patterns"
    
    # ------- BaseRegistry Interface Implementation -------
    
    def discover_core(self) -> Dict[str, Dict[str, Any]]:
        """Discover core file pattern rules from bundled data."""
        rules = self.load_core_rules()
        return {rule.get("name", rule.get("_path", f"rule-{i}")): rule for i, rule in enumerate(rules)}
    
    def discover_packs(self, packs: List[str]) -> Dict[str, Dict[str, Any]]:
        """Discover file pattern rules from active packs (bundled + project)."""
        result: Dict[str, Dict[str, Any]] = {}
        for pack in packs:
            rules = self.load_pack_rules(pack)
            for i, rule in enumerate(rules):
                rule_name = rule.get("name", f"{pack}-rule-{i}")
                result[rule_name] = rule
        return result
    
    def discover_project(self) -> Dict[str, Dict[str, Any]]:
        """Discover project-level file pattern overrides at .edison/rules/file_patterns/."""
        rules = self._load_yaml_dir(self.project_rules_dir, "project")
        return {rule.get("name", rule.get("_path", f"project-rule-{i}")): rule for i, rule in enumerate(rules)}
    
    def exists(self, name: str) -> bool:
        """Check if a file pattern rule exists in core."""
        return name in self.discover_core()
    
    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a file pattern rule by name from core."""
        return self.discover_core().get(name)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all file pattern rules from core."""
        return list(self.discover_core().values())

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """Load and validate file pattern YAML file.

        Uses YamlLayerMixin._load_yaml_file() for consistent YAML loading.
        """
        data = self._load_yaml_file(path, required=True)
        if not isinstance(data, dict):
            raise ValueError(f"{path} must parse to a mapping")
        data["_path"] = str(path)
        return data

    # Note: Uses _load_yaml_dir() from YamlLayerMixin

    def load_core_rules(self) -> List[Dict[str, Any]]:
        """Return file pattern rules from bundled core (generic only)."""
        return self._load_yaml_dir(self.core_rules_dir, "core")

    def load_pack_rules(self, pack_name: str) -> List[Dict[str, Any]]:
        """Return file pattern rules from the given pack (bundled or project)."""
        # Try bundled pack first
        bundled_candidate = self.bundled_packs_dir / pack_name / "rules" / "file_patterns"
        if bundled_candidate.exists():
            return self._load_yaml_dir(bundled_candidate, f"pack:{pack_name}")

        # Try project pack
        project_candidate = self.project_packs_dir / pack_name / "rules" / "file_patterns"
        if project_candidate.exists():
            return self._load_yaml_dir(project_candidate, f"pack:{pack_name}")

        return []

    def compose(self, *, active_packs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Compose bundled core + pack file pattern rules respecting active packs."""
        rules = list(self.load_core_rules())
        for pack in active_packs or []:
            rules.extend(self.load_pack_rules(pack))
        return rules


__all__ = ["FilePatternRegistry"]
