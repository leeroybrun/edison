"""Rules registry base implementation.

This module provides the RulesRegistry class for loading and composing rules
from bundled + pack YAML registries, with support for guideline anchors and
include resolution.

Architecture:
    - Bundled rules: edison.data/rules/registry.yml (ALWAYS used for core)
    - Pack rules: <packs-root>/<pack>/rules/registry.yml (bundled + user + project)
    - User rules: <user-config-dir>/rules/registry.yml (overrides)
    - Project rules: <project-config-dir>/rules/registry.yml (overrides)

Uses the unified composition path resolver for consistent layer roots
across config/composition/packs/rules subsystems.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from edison.core.composition.core.sections import SectionParser
from edison.core.utils.paths import EdisonPathError, PathResolver
from edison.core.utils.io import read_yaml, resolve_yaml_path

from edison.core.composition.core.errors import AnchorNotFoundError, RulesCompositionError
from edison.data import get_data_path
from edison.core.utils.profiling import span


class RulesRegistryBase:
    """
    Load and compose rules from bundled + pack YAML registries.

    Features:
    - YAML-based rule loading
    - Anchor extraction from guidelines
    - Include resolution
    - Uses unified composition path resolver for layer roots

    Registry locations:
      - Bundled: edison.data/rules/registry.yml (ALWAYS used for core)
      - Packs: <packs-root>/<pack>/rules/registry.yml (bundled + user + project)
      - User: <user-config-dir>/rules/registry.yml (overrides)
      - Project: <project-config-dir>/rules/registry.yml (overrides)

    This class is read-only; it does not mutate project state.
    """

    entity_type: str = "rule"

    def __init__(self, project_root: Optional[Path] = None) -> None:
        try:
            self.project_root = project_root or PathResolver.resolve_project_root()
        except (EdisonPathError, ValueError) as exc:
            raise RulesCompositionError(str(exc)) from exc

        # Resolve all layer roots from the unified composition path resolver.
        from edison.core.composition.core.paths import CompositionPathResolver

        resolver = CompositionPathResolver(self.project_root)
        layer_ctx = resolver.layer_context

        # Project config directory (e.g. <project-config-dir>, configurable)
        self.project_dir = layer_ctx.project_dir
        # User config directory root (~/<user-config-dir>)
        self.user_dir = layer_ctx.user_dir
        # Pack roots (bundled → user → project)
        self._pack_roots = layer_ctx.pack_roots
        # Overlay layers (e.g., company → user → project)
        self._overlay_layers = list(layer_ctx.overlay_layers)

        # Core registry is ALWAYS from bundled data
        self.core_registry_path = get_data_path("rules", "registry.yml")

        # Bundled data directory for resolving guideline paths
        self.bundled_data_dir = Path(get_data_path(""))

        # Store reference to config manager for active packs lookup
        from edison.core.config import ConfigManager

        self._cfg_mgr = ConfigManager(repo_root=self.project_root)
        self._types_manager: Optional["ComposableTypesManager"] = None  # type: ignore[name-defined]

    def get_active_packs(self) -> List[str]:
        """Get active packs from ConfigManager.

        Returns:
            List of active pack names from packs.active config.
        """
        cfg = self._cfg_mgr.load_config(validate=False, include_packs=False)
        packs_section = cfg.get("packs", {}) or {}
        active = packs_section.get("active", []) or []
        return [str(p) for p in active if p] if isinstance(active, list) else []

    def _get_types_manager(self) -> "ComposableTypesManager":  # type: ignore[name-defined]
        """Lazy ComposableTypesManager for composed-include resolution."""
        if self._types_manager is None:
            from edison.core.composition.registries._types_manager import ComposableTypesManager

            self._types_manager = ComposableTypesManager(project_root=self.project_root)
        return self._types_manager

    def _build_include_provider(self, packs: List[str]) -> Callable[[str], Optional[str]]:
        """Build a composed include provider (no legacy include resolver)."""
        from edison.core.composition.includes import ComposedIncludeProvider

        return ComposedIncludeProvider(
            types_manager=self._get_types_manager(),
            packs=tuple(packs),
            materialize=False,
        ).build()

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

    # ------- Utility Methods -------

    @staticmethod
    def extract_section_content(source_file: Path, section_name: str) -> str:
        """
        Extract content between SECTION markers in a guideline file.

        Uses SectionParser to extract content from <!-- SECTION: name --> markers.

        Args:
            source_file: Path to the guideline file
            section_name: Name of the section to extract

        Returns:
            The content between the section markers

        Raises:
            FileNotFoundError: If the source file doesn't exist
            AnchorNotFoundError: If the section isn't found in the file
        """
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")
        
        content = source_file.read_text(encoding="utf-8")
        parser = SectionParser()
        section_content = parser.extract_section(content, section_name)
        
        if section_content is None:
            raise AnchorNotFoundError(f"Section '{section_name}' not found in {source_file}")
        
        return section_content

    # ------- Registry Interface Implementation -------

    def discover_core(self) -> Dict[str, Dict[str, Any]]:
        """Discover core rules from bundled registry."""
        registry = self.load_core_registry()
        rules = registry.get("rules", [])
        return {rule.get("id", f"rule-{i}"): rule for i, rule in enumerate(rules) if isinstance(rule, dict)}
    
    def discover_packs(self, packs: List[str]) -> Dict[str, Dict[str, Any]]:
        """Discover rules from active packs (bundled + user + project packs)."""
        result: Dict[str, Dict[str, Any]] = {}
        for pack in packs:
            registry = self.load_pack_registry(pack)
            rules = registry.get("rules", [])
            for i, rule in enumerate(rules):
                if isinstance(rule, dict):
                    rule_id = rule.get("id", f"{pack}-rule-{i}")
                    result[rule_id] = rule
        return result
    
    def discover_project(self) -> Dict[str, Dict[str, Any]]:
        """Discover project-level rule overrides at <project-config-dir>/rules/."""
        path = self.project_dir / "rules" / "registry.yml"
        registry = self._load_yaml(path, required=False)
        rules = registry.get("rules", [])
        return {rule.get("id", f"project-rule-{i}"): rule for i, rule in enumerate(rules) if isinstance(rule, dict)}
    
    def exists(self, rule_id: str) -> bool:
        """Check if a rule exists in core registry."""
        return rule_id in self.discover_core()
    
    def get(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get a rule by ID from core registry."""
        return self.discover_core().get(rule_id)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all rules from core registry."""
        return list(self.discover_core().values())

    # ------------------------------------------------------------------
    # Registry loading
    # ------------------------------------------------------------------
    def _load_yaml(self, path: Path, *, required: bool) -> Dict[str, Any]:
        """Load and validate rules YAML file."""
        path = resolve_yaml_path(path)
        try:
            data = self._load_yaml_file(path, required=required)
        except FileNotFoundError:
            if required:
                raise RulesCompositionError(f"Rules registry not found at {path}")
            return {"version": None, "rules": []}

        if not isinstance(data, dict):
            raise RulesCompositionError(
                f"Invalid rules registry at {path}: expected mapping at top level"
            )

        rules = data.get("rules") or []
        if not isinstance(rules, list):
            raise RulesCompositionError(
                f"Invalid rules registry at {path}: 'rules' must be a list"
            )
        data["rules"] = rules
        return data

    def load_core_registry(self) -> Dict[str, Any]:
        """Load bundled rules registry from edison.data package."""
        return self._load_yaml(self.core_registry_path, required=True)

    def load_pack_registry(self, pack_name: str) -> Dict[str, Any]:
        """Load pack-specific rules registry, merging bundled + user + project.

        Architecture:
        - Pack rules can exist in multiple pack roots (bundled → user → project).
        - Each root contributes <packs-root>/<pack>/rules/registry.yml.
        - Merge strategy: rules are appended low→high precedence so later IDs
          can override earlier ones during composition.
        """
        registries: List[Dict[str, Any]] = []
        for root in self._pack_roots:
            path = root.path / pack_name / "rules" / "registry.yml"
            registries.append(self._load_yaml(path, required=False))

        merged_rules: List[Any] = []
        for reg in registries:
            merged_rules.extend(list(reg.get("rules", [])))

        version = "1.0.0"
        for reg in reversed(registries):
            v = reg.get("version")
            if v:
                version = str(v)
                break

        return {"version": version, "rules": merged_rules}

    # ------------------------------------------------------------------
    # Composition helpers
    # ------------------------------------------------------------------
