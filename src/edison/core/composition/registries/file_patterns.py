"""
File pattern rule registry with pack awareness.

This module keeps core free of tech-specific file pattern rules by loading
generic patterns from the bundled rules directory and merging in pack-provided
patterns only when those packs are active.

Architecture:
    - Bundled file patterns: edison.data/rules/file_patterns/ (ALWAYS)
    - Pack patterns: bundled packs + .edison/packs/<pack>/rules/file_patterns/
    - Project overrides: .edison/rules/file_patterns/ (optional)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.data import get_data_path
from edison.core.utils.paths import PathResolver, EdisonPathError
from edison.core.utils.io import read_yaml


class FilePatternRegistry:
    """Load file pattern rules from bundled core plus optional packs.

    Architecture:
    - Core patterns: ALWAYS from bundled edison.data/rules/file_patterns/
    - Pack patterns: bundled packs + project packs
    """
    
    entity_type: str = "file_pattern"

    def __init__(self, repo_root: Optional[Path] = None) -> None:
        try:
            self.project_root = PathResolver.resolve_project_root() if repo_root is None else Path(repo_root)
        except (EdisonPathError, ValueError):
            # Fall back to cwd when path resolution fails (defensive guard for tests)
            self.project_root = Path.cwd()

        # Project .edison directory
        self.project_dir = self.project_root / ".edison"
        
        # Bundled packs directory
        self.bundled_packs_dir = get_data_path("packs")
        
        # Project packs directory
        self.project_packs_dir = self.project_dir / "packs"

        # Core rules are ALWAYS from bundled data
        self.core_rules_dir = get_data_path("rules") / "file_patterns"

        # Project-level file pattern overrides
        self.project_rules_dir = self.project_dir / "rules" / "file_patterns"

    def _load_yaml_file(self, path: Path, required: bool = True) -> Any:
        """Load a single YAML file using shared utility.
        
        Args:
            path: Path to YAML file
            required: If True, raise FileNotFoundError when file doesn't exist
            
        Returns:
            Parsed YAML content
        """
        if not path.exists():
            if required:
                raise FileNotFoundError(f"YAML file not found: {path}")
            return {}
        
        return read_yaml(path, default={})

    def _load_yaml_dir(self, dir_path: Path, label: str = "") -> List[Dict[str, Any]]:
        """Load all YAML files from a directory.
        
        Args:
            dir_path: Directory containing YAML files
            label: Label for source tracking
            
        Returns:
            List of parsed YAML dicts
        """
        if not dir_path.exists():
            return []
        
        results: List[Dict[str, Any]] = []
        for yaml_file in sorted(dir_path.glob("*.yml")) + sorted(dir_path.glob("*.yaml")):
            if yaml_file.is_file():
                data = self._load_yaml_file(yaml_file, required=False)
                if isinstance(data, dict):
                    data["_path"] = str(yaml_file)
                    # Source/origin marker for tests and debugging.
                    # Convention: "core" | "project" | "pack:<pack>"
                    data["_origin"] = label
                    data["_source"] = label
                    results.append(data)
        
        return results

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
