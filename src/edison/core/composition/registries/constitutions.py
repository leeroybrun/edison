"""Constitution registry (unified composition).

Builds role constitutions from layered markdown using MarkdownCompositionStrategy
via ComposableRegistry. Uses standard file discovery and composition - no hardcoding.

Constitution-specific context_vars:
- mandatoryReads, optionalReads: From config.constitutions.<name>
- rules: From rules system (role-based, graceful fallback)
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from ._base import ComposableRegistry


class ConstitutionRegistry(ComposableRegistry[str]):
    """Registry for composing role constitutions.

    Extends ComposableRegistry with constitution-specific context_vars:
    - mandatoryReads/optionalReads from config.constitutions.<name>
    - rules from get_rules_for_role() (graceful fallback if not a valid role)
    
    Uses standard file discovery - no hardcoded roles.
    """

    content_type: ClassVar[str] = "constitutions"
    file_pattern: ClassVar[str] = "*.md"
    strategy_config: ClassVar[Dict[str, Any]] = {
        "enable_sections": True,
        "enable_dedupe": False,
        "enable_template_processing": True,
    }

    def get_context_vars(self, name: str, packs: List[str]) -> Dict[str, Any]:
        """Build context_vars for template processing.

        Extends base class with constitution-specific variables:
        - mandatoryReads, optionalReads from config
        - rules from rules system

        Args:
            name: Constitution name (from filename)
            packs: Active pack names

        Returns:
            Dict of context variables for TemplateEngine
        """
        # Get base context vars (source_layers, timestamp, version, etc.)
        context = super().get_context_vars(name, packs)

        # Constitution-specific: mandatoryReads/optionalReads from config
        role_cfg = self.config.get("constitutions", {}).get(name, {}) or {}
        if isinstance(role_cfg, dict):
            context["mandatoryReads"] = role_cfg.get("mandatoryReads", [])
            context["optionalReads"] = role_cfg.get("optionalReads", [])
        else:
            context["mandatoryReads"] = []
            context["optionalReads"] = []

        # Constitution-specific: rules from rules system
        # Graceful fallback - if name isn't a valid role, rules will be empty
        rules: List[Dict[str, Any]] = []
        try:
            from edison.core.rules.registry import get_rules_for_role
            # Normalize: agents -> agent, validators -> validator
            rule_role = name.rstrip("s") if name.endswith("s") else name
            rules = get_rules_for_role(rule_role)
        except (ValueError, ImportError):
            pass  # Not a valid role or rules system unavailable

        context["rules"] = rules
        return context

    # Legacy compatibility method
    def compose_constitution(self, role: str, packs: Optional[List[str]] = None) -> Optional[str]:
        """Compose a constitution for a specific role.
        
        Legacy method for backwards compatibility.
        Prefer using compose() directly.
        """
        # Normalize role name for file lookup
        if role == "agent":
            role = "agents"
        elif role == "validator":
            role = "validators"
        return self.compose(role, packs)


def generate_all_constitutions(config: Any, output_path: Path) -> List[Path]:
    """Generate all role constitutions to output directory.

    Args:
        config: Config object with repo_root attribute
        output_path: Base output path (constitutions/ subdir will be created)
        
    Returns:
        List of paths to written constitution files
    """
    registry = ConstitutionRegistry(project_root=config.repo_root)
    return registry.write_all()


# Keep ConstitutionResult for backwards compatibility in imports
from dataclasses import dataclass

@dataclass
class ConstitutionResult:
    """Deprecated - kept for backwards compatibility."""
    role: str
    content: str
    source_layers: List[str]


__all__ = ["ConstitutionRegistry", "ConstitutionResult", "generate_all_constitutions"]
