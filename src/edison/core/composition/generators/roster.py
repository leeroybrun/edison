"""Roster generators for agents and validators.

Generates:
- AVAILABLE_AGENTS.md from AgentRegistry
- AVAILABLE_VALIDATORS.md from ValidatorRegistry

Uses ComposableGenerator pattern with two-phase generation:
1. Compose template from layers (supports pack customization)
2. Inject data from registries
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from .base import ComposableGenerator


def _utc_timestamp() -> str:
    """Generate UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()




class AgentRosterGenerator(ComposableGenerator):
    """Generate AVAILABLE_AGENTS.md from AgentRegistry.

    Two-phase generation:
    1. Compose AVAILABLE_AGENTS.md template from layers
    2. Inject agent data from AgentRegistry
    """

    @property
    def template_name(self) -> str:
        return "AVAILABLE_AGENTS"

    @property
    def output_filename(self) -> str:
        return "AVAILABLE_AGENTS.md"

    def _gather_data(self) -> Dict[str, Any]:
        """Gather agent data from AgentRegistry.

        Returns:
            Dictionary with:
            - agents: List of agent metadata
            - timestamp: Generation timestamp
            - generated_header: Header comment block
        """
        from edison.core.composition.registries import AgentRegistry

        registry = AgentRegistry(project_root=self.project_root)
        agents = registry.get_all_metadata()

        return {
            "agents": agents,
            "timestamp": _utc_timestamp(),
        }


class ValidatorRosterGenerator(ComposableGenerator):
    """Generate AVAILABLE_VALIDATORS.md from ValidatorRegistry.

    Two-phase generation:
    1. Compose AVAILABLE_VALIDATORS.md template from layers
    2. Inject validator data from ValidatorRegistry
    """

    @property
    def template_name(self) -> str:
        return "AVAILABLE_VALIDATORS"

    @property
    def output_filename(self) -> str:
        return "AVAILABLE_VALIDATORS.md"

    def _gather_data(self) -> Dict[str, Any]:
        """Gather validator data from ValidatorRegistry.

        Returns:
            Dictionary with:
            - global_validators: List of global validators
            - critical_validators: List of critical validators
            - specialized_validators: List of specialized validators
            - timestamp: Generation timestamp
            - generated_header: Header comment block
        """
        from edison.core.composition.registries import ValidatorRegistry

        registry = ValidatorRegistry(project_root=self.project_root)
        validators_by_tier = registry.get_all_grouped()

        return {
            "global_validators": validators_by_tier.get("global", []),
            "critical_validators": validators_by_tier.get("critical", []),
            "specialized_validators": validators_by_tier.get("specialized", []),
            "timestamp": _utc_timestamp(),
        }


__all__ = [
    "AgentRosterGenerator",
    "ValidatorRosterGenerator",
]
