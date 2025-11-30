"""
Rules Registry for the Edison Rules system.

This module provides the RulesRegistry class for loading and composing rules
from bundled + pack YAML registries, with support for guideline anchors and
include resolution.

Architecture:
    - Bundled rules: edison.data/rules/registry.yml (ALWAYS used for core)
    - Pack rules: .edison/packs/<pack>/rules/registry.yml
    - Project rules: .edison/rules/registry.yml (overrides)
    - NO .edison/core/ - that is legacy

    BaseEntityManager
    └── BaseRegistry
        └── RulesRegistry (this module)
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from edison.core.entity import BaseRegistry
from edison.core.utils.paths import EdisonPathError, PathResolver
from edison.core.utils.paths import get_project_config_dir
from edison.core.utils.text import extract_anchor_content as _extract_anchor_content
from edison.data import read_yaml as read_bundled_yaml

from ..includes import resolve_includes, ComposeError
from ..core.errors import AnchorNotFoundError, RulesCompositionError
from edison.data import get_data_path


class RulesRegistry(BaseRegistry[Dict[str, Any]]):
    """
    Load and compose rules from bundled + pack YAML registries.
    
    Extends BaseRegistry with rule-specific functionality:
    - YAML-based rule loading
    - Anchor extraction from guidelines
    - Include resolution
    
    Registry locations:
      - Bundled: edison.data/rules/registry.yml (ALWAYS used for core)
      - Packs: .edison/packs/<pack>/rules/registry.yml (bundled + project)
      - Project: .edison/rules/registry.yml (overrides)
      - NO .edison/core/ - that is legacy

    This class is read-only; it does not mutate project state.
    """
    
    entity_type: str = "rule"

    def __init__(self, project_root: Optional[Path] = None) -> None:
        # Note: We handle project_root ourselves due to custom error handling
        try:
            resolved_root = project_root or PathResolver.resolve_project_root()
        except (EdisonPathError, ValueError) as exc:  # pragma: no cover - defensive
            raise RulesCompositionError(str(exc)) from exc
        
        super().__init__(resolved_root)

        self.project_config_dir = get_project_config_dir(self.project_root, create=False)

        # Core registry is ALWAYS from bundled data
        self.core_registry_path = get_data_path("rules", "registry.yml")
        
        # Bundled data directory for resolving guideline paths
        self.bundled_data_dir = Path(get_data_path(""))
        
        # Pack directories (bundled + project)
        self.bundled_packs_dir = Path(get_data_path("packs"))
        self.project_packs_dir = self.project_config_dir / "packs"
    
    # ------- Utility Methods -------

    @staticmethod
    def extract_anchor_content(source_file: Path, anchor: str) -> str:
        """
        Extract content between ANCHOR markers in a guideline file.

        This is a convenience wrapper around the canonical implementation
        in edison.core.utils.text.anchors for backwards compatibility.

        Supports both explicit END markers and implicit termination at the next
        ANCHOR marker (or EOF when no END marker is present).

        Args:
            source_file: Path to the guideline file
            anchor: Name of the anchor to extract

        Returns:
            The content between the anchor markers

        Raises:
            FileNotFoundError: If the source file doesn't exist
            AnchorNotFoundError: If the anchor isn't found in the file
        """
        return _extract_anchor_content(source_file, anchor)

    # ------- BaseRegistry Interface Implementation -------

    def discover_core(self) -> Dict[str, Dict[str, Any]]:
        """Discover core rules from bundled registry."""
        registry = self.load_core_registry()
        rules = registry.get("rules", [])
        return {rule.get("id", f"rule-{i}"): rule for i, rule in enumerate(rules) if isinstance(rule, dict)}
    
    def discover_packs(self, packs: List[str]) -> Dict[str, Dict[str, Any]]:
        """Discover rules from active packs (bundled + project)."""
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
        """Discover project-level rule overrides at .edison/rules/."""
        path = self.project_config_dir / "rules" / "registry.yml"
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
    @staticmethod
    def _load_yaml(path: Path, *, required: bool) -> Dict[str, Any]:
        if not path.exists():
            if required:
                raise RulesCompositionError(f"Rules registry not found at {path}")
            return {"version": None, "rules": []}

        from edison.core.utils.io import read_yaml
        data = read_yaml(path, raise_on_error=True) or {}
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
        """Load pack-specific rules registry (bundled or project)."""
        # Try bundled pack first
        bundled_path = self.bundled_packs_dir / pack_name / "rules" / "registry.yml"
        if bundled_path.exists():
            return self._load_yaml(bundled_path, required=False)
        
        # Fall back to project pack
        project_path = self.project_packs_dir / pack_name / "rules" / "registry.yml"
        return self._load_yaml(project_path, required=False)

    # ------------------------------------------------------------------
    # Composition helpers
    # ------------------------------------------------------------------
    def _resolve_source(self, rule: Dict[str, Any]) -> Tuple[Optional[Path], Optional[str]]:
        """Resolve source file path and optional anchor for a rule."""
        source = rule.get("source") or {}
        file_ref = str(source.get("file") or rule.get("sourcePath") or "").strip()
        anchor = source.get("anchor")

        if not file_ref:
            return None, None

        # Legacy form: "path#anchor" embedded in sourcePath
        file_part, sep, frag = file_ref.partition("#")
        if sep and frag and not anchor:
            anchor = frag
        else:
            file_part = file_ref

        # Resolve file path
        source_path: Optional[Path] = None
        
        # Project-relative paths starting with .edison/
        if file_part.startswith(".edison/"):
            source_path = (self.project_root / file_part).resolve()
        # Absolute paths
        elif file_part.startswith("/"):
            source_path = (self.project_root / file_part.lstrip("/")).resolve()
        else:
            # Relative paths resolve to bundled data (e.g., "guidelines/VALIDATION.md")
            bundled_path = (self.bundled_data_dir / file_part).resolve()
            if bundled_path.exists():
                source_path = bundled_path
            else:
                # Fall back to project directory for project-level content
                project_path = (self.project_config_dir / file_part).resolve()
                source_path = project_path

        return source_path, str(anchor) if anchor else None

    def _compose_rule_body(
        self,
        rule: Dict[str, Any],
        origin: str,
        *,
        deps: Optional[Set[Path]] = None,
    ) -> Tuple[str, List[Path]]:
        """
        Build composed body text for a single rule.

        Composition semantics:
          - If source.file (+ optional anchor) is present, extract anchor content
            or entire file, then resolve {{include:...}} patterns via the
            prompt composition engine.
          - Append inline ``guidance`` text after resolved anchor content.
        """
        if deps is None:
            deps = set()

        source_file, anchor = self._resolve_source(rule)

        body_parts: List[str] = []

        if source_file is not None:
            if anchor:
                anchor_text = self.extract_anchor_content(source_file, anchor)
            else:
                anchor_text = source_file.read_text(encoding="utf-8")

            body_parts.append(anchor_text)

            # Resolve any include directives within the anchor text.
            try:
                resolved_text, include_deps = resolve_includes(
                    "".join(body_parts),
                    base_file=source_file,
                )
            except ComposeError as exc:
                # Surface a composition-aware error while preserving details
                raise RulesCompositionError(str(exc)) from exc

            deps.update(include_deps)
            body_parts = [resolved_text]

        guidance = rule.get("guidance")
        if guidance:
            guidance_text = str(guidance).rstrip()
            if guidance_text:
                if body_parts and not body_parts[-1].endswith("\n"):
                    body_parts[-1] += "\n"
                body_parts.append(guidance_text + "\n")

        body = "".join(body_parts) if body_parts else ""
        return body, sorted({p.resolve() for p in deps})

    def compose(self, packs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compose rules from bundled core + optional packs into a single structure.

        Returns:
            Dict with keys:
              - version: registry version (string)
              - packs: list of packs used during composition
              - rules: mapping of rule-id -> composed rule payload
        """
        packs = list(packs or [])

        core = self.load_core_registry()
        rules_index: Dict[str, Dict[str, Any]] = {}

        # Core rules first (from bundled data)
        for raw_rule in core.get("rules", []) or []:
            if not isinstance(raw_rule, dict):
                continue
            rid = str(raw_rule.get("id") or "").strip()
            if not rid:
                continue

            body, deps = self._compose_rule_body(raw_rule, origin="core")
            entry: Dict[str, Any] = {
                "id": rid,
                "title": raw_rule.get("title") or rid,
                "category": raw_rule.get("category") or "",
                "blocking": bool(raw_rule.get("blocking", False)),
                "contexts": raw_rule.get("contexts") or [],
                "source": raw_rule.get("source") or {},
                "body": body,
                "origins": ["core"],
                "dependencies": [str(p) for p in deps],
            }
            rules_index[rid] = entry

        # Pack overlays merge by rule id
        for pack_name in packs:
            pack_registry = self.load_pack_registry(pack_name)
            for raw_rule in pack_registry.get("rules", []) or []:
                if not isinstance(raw_rule, dict):
                    continue
                rid = str(raw_rule.get("id") or "").strip()
                if not rid:
                    continue

                body, deps = self._compose_rule_body(
                    raw_rule,
                    origin=f"pack:{pack_name}",
                )

                if rid not in rules_index:
                    rules_index[rid] = {
                        "id": rid,
                        "title": raw_rule.get("title") or rid,
                        "category": raw_rule.get("category") or "",
                        "blocking": bool(raw_rule.get("blocking", False)),
                        "contexts": raw_rule.get("contexts") or [],
                        "source": raw_rule.get("source") or {},
                        "body": body,
                        "origins": [f"pack:{pack_name}"],
                        "dependencies": [str(p) for p in deps],
                    }
                    continue

                entry = rules_index[rid]
                # Title: allow pack to refine title when provided
                if raw_rule.get("title"):
                    entry["title"] = raw_rule["title"]
                # Category: allow pack to refine category when provided
                if raw_rule.get("category"):
                    entry["category"] = raw_rule["category"]
                # Blocking: once blocking, always blocking
                if raw_rule.get("blocking", False):
                    entry["blocking"] = True
                # Contexts: append pack contexts
                if raw_rule.get("contexts"):
                    entry["contexts"] = (entry.get("contexts") or []) + raw_rule["contexts"]  # type: ignore[index]
                # Body: append pack guidance after core text
                entry["body"] = (entry.get("body") or "") + (body or "")
                # Origins: record pack contribution
                entry.setdefault("origins", []).append(f"pack:{pack_name}")
                # Dependencies: merge without duplicates
                existing = set(entry.get("dependencies") or [])
                for p in deps:
                    existing.add(str(p))
                entry["dependencies"] = sorted(existing)

        return {
            "version": core.get("version") or "1.0.0",
            "packs": packs,
            "rules": rules_index,
        }

    def compose_rule(self, rule_id: str, packs: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compose a single rule by ID.

        Returns a dict with the rule metadata and composed content.
        Used by the CLI to show individual rules.
        """
        composed = self.compose(packs=packs)
        rules_dict = composed.get("rules", {})

        if rule_id not in rules_dict:
            raise RulesCompositionError(f"Rule not found: {rule_id}")

        rule = rules_dict[rule_id]

        # Build response with anchor information from source path
        source_path_str = rule.get("source", {}).get("file", "")
        if "#" in source_path_str:
            file_part, anchor_part = source_path_str.split("#", 1)
        else:
            file_part = source_path_str
            anchor_part = ""

        return {
            "id": rule["id"],
            "title": rule.get("title", ""),
            "category": rule.get("category", ""),
            "blocking": rule.get("blocking", False),
            "sourcePath": source_path_str,
            "startAnchor": f"<!-- ANCHOR: {anchor_part} -->" if anchor_part else "",
            "endAnchor": f"<!-- END ANCHOR: {anchor_part} -->" if anchor_part else "",
            "content": rule.get("body", ""),
            "guidance": rule.get("category", ""),  # Use category as guidance fallback
            "contexts": rule.get("contexts", []),
        }

    def load_composed_rules(self, packs: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Load all composed rules as a list.

        Returns a list of rule dicts suitable for filtering and display.
        """
        composed = self.compose(packs=packs)
        rules_dict = composed.get("rules", {})

        # Convert to list format
        rules_list = []
        for rule_id, rule in rules_dict.items():
            source_path_str = rule.get("source", {}).get("file", "")
            rules_list.append({
                "id": rule["id"],
                "title": rule.get("title", ""),
                "category": rule.get("category", ""),
                "blocking": rule.get("blocking", False),
                "sourcePath": source_path_str,
                "content": rule.get("body", ""),
                "guidance": rule.get("category", ""),  # Use category as guidance
                "contexts": rule.get("contexts", []),
            })

        return rules_list


def compose_rules(packs: Optional[List[str]] = None, project_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Convenience wrapper for composing rules via RulesRegistry.

    Used by tests and CLI entrypoints.

    Args:
        packs: List of pack names to include (optional)
        project_root: Project root path (optional, defaults to PathResolver.resolve_project_root())
    """
    registry = RulesRegistry(project_root=project_root)
    return registry.compose(packs=packs)


# ------------------------------------------------------------------
# Role-based rule query API (moved from RulesEngine)
# ------------------------------------------------------------------
def load_bundled_rules() -> List[Dict[str, Any]]:
    """
    Load all rules from the bundled registry.

    Returns:
        List of rule dictionaries from the registry
    """
    registry_data = read_bundled_yaml("rules", "registry.yml")
    rules = registry_data.get("rules", [])
    return rules if isinstance(rules, list) else []


def get_rules_for_role(role: str) -> List[Dict[str, Any]]:
    """
    Extract rules that apply to a specific role.

    Args:
        role: One of 'orchestrator', 'agent', 'validator'

    Returns:
        List of rule dictionaries where applies_to includes the role

    Raises:
        ValueError: If role is not one of the valid options
    """
    if role not in ('orchestrator', 'agent', 'validator'):
        raise ValueError(f"Invalid role: {role}. Must be orchestrator, agent, or validator")

    all_rules = load_bundled_rules()
    return [
        rule for rule in all_rules
        if role in rule.get('applies_to', [])
    ]


def filter_rules(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Filter rules by context metadata (role, category, etc.).

    This function provides simplified filtering of rules from the
    bundled registry, complementing the instance method get_rules_for_context
    which works with Rule objects for runtime enforcement.

    Args:
        context: Dictionary with optional keys:
            - role: One of 'orchestrator', 'agent', 'validator'
            - category: Rule category (e.g., 'validation', 'delegation')

    Returns:
        List of rule dictionaries matching the context filters
    """
    rules = load_bundled_rules()

    # Filter by role if specified
    if 'role' in context:
        rules = [r for r in rules if context['role'] in r.get('applies_to', [])]

    # Filter by category if specified
    if 'category' in context:
        rules = [r for r in rules if r.get('category') == context['category']]

    return rules


# Module-level export - delegates to canonical implementation in utils.text.anchors
extract_anchor_content = _extract_anchor_content


__all__ = [
    "RulesRegistry",
    "compose_rules",
    "extract_anchor_content",
    "load_bundled_rules",
    "get_rules_for_role",
    "filter_rules",
]
