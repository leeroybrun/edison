"""Dynamic generation of roster documentation files.

Generates AVAILABLE_VALIDATORS.md from ValidatorRegistry.

Uses unified path resolution for consistent discovery.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any, Optional

from edison.core.config import ConfigManager
from edison.core.file_io.utils import ensure_dir

from .agents import AgentRegistry
from .headers import build_generated_header
from .validators import ValidatorRegistry
from .path_utils import resolve_project_dir_placeholders
from .unified import UnifiedPathResolver


def generate_available_agents(output_path: Path, repo_root: Optional[Path] = None) -> None:
    """Generate AVAILABLE_AGENTS.md from AgentRegistry.
    
    Uses unified path resolution for consistent discovery.
    """
    ensure_dir(output_path.parent)

    registry = AgentRegistry(repo_root=repo_root)
    agents = registry.get_all()
    
    # Use unified path resolver instead of direct get_project_config_dir
    resolver = UnifiedPathResolver(repo_root or registry.repo_root)
    project_dir = resolver.project_dir
    cfg_mgr = ConfigManager(repo_root=repo_root)

    content = (
        f"{build_generated_header('rosters.available_agents', config=cfg_mgr, target_path=output_path)}"
        "# Available Agents\n\n"
        "This file is dynamically generated from the AgentRegistry. Do not edit directly.\n\n"
        "## Agent Roster\n\n"
        "| Agent | Type | Model | Description |\n"
        "|-------|------|-------|-------------|\n"
        f"{_format_agent_table(agents)}\n\n"
        "## Agent Details\n\n"
        f"{_format_agent_details(agents)}\n"
        "## Delegation Patterns\n\n"
        "See `guidelines/shared/DELEGATION.md` for file pattern → agent mappings.\n"
    )

    content = resolve_project_dir_placeholders(
        content,
        project_dir=project_dir,
        target_path=output_path,
        repo_root=repo_root or registry.repo_root,
    )
    output_path.write_text(content, encoding="utf-8")


def generate_available_validators(output_path: Path, repo_root: Optional[Path] = None) -> None:
    """Generate AVAILABLE_VALIDATORS.md from ValidatorRegistry.

    Uses unified path resolution for consistent discovery.
    
    Args:
        output_path: Path where the generated file should be written
        repo_root: Optional repository root path for testing
    """
    # Ensure output directory exists
    ensure_dir(output_path.parent)

    # Get validators from registry
    registry = ValidatorRegistry(repo_root=repo_root)
    validators_by_tier = registry.get_all()

    # Extract validators by tier
    global_validators = validators_by_tier.get('global', [])
    critical_validators = validators_by_tier.get('critical', [])
    specialized_validators = validators_by_tier.get('specialized', [])

    cfg_mgr = ConfigManager(repo_root=repo_root)
    
    # Use unified path resolver instead of direct get_project_config_dir
    resolver = UnifiedPathResolver(repo_root or registry.repo_root)
    project_dir = resolver.project_dir

    content = (
        f"{build_generated_header('rosters.available_validators', config=cfg_mgr, target_path=output_path)}"
        "# Available Validators\n\n"
        "This file is dynamically generated from the ValidatorRegistry. Do not edit directly.\n\n"
        "## Validator Roster\n\n"
        "### Global Validators (Always Run)\n\n"
        "| Validator | Model | Blocking | Description |\n"
        "|-----------|-------|----------|-------------|\n"
        f"{_format_validator_table(global_validators)}\n\n"
        "### Critical Validators (Blocking)\n\n"
        "| Validator | Model | Blocking | Description |\n"
        "|-----------|-------|----------|-------------|\n"
        f"{_format_validator_table(critical_validators)}\n\n"
        "### Specialized Validators (Pattern-Triggered)\n\n"
        "| Validator | Model | Blocking | Triggers |\n"
        "|-----------|-------|----------|----------|\n"
        f"{_format_specialized_validator_table(specialized_validators)}\n\n"
        "## Validator Execution Order\n\n"
        "1. **Wave 1**: Global validators (parallel)\n"
        "2. **Wave 2**: Critical validators (parallel, blocks on failure)\n"
        "3. **Wave 3**: Specialized validators (parallel, triggered by file patterns)\n\n"
        "## Consensus Requirements\n\n"
        "- Global validators must reach consensus (codex-global + claude-global agree)\n"
        "- Critical validators are blocking (any failure rejects the task)\n"
        "- Specialized validators are advisory unless configured as blocking\n\n"
        "See `guidelines/shared/VALIDATION.md` for detailed workflow.\n"
    )

    content = resolve_project_dir_placeholders(
        content,
        project_dir=project_dir,
        target_path=output_path,
        repo_root=repo_root or registry.repo_root,
    )
    output_path.write_text(content, encoding="utf-8")


def _format_validator_table(validators: List[Dict[str, Any]]) -> str:
    """Format validators as markdown table rows.

    Args:
        validators: List of validator metadata dictionaries

    Returns:
        Formatted markdown table rows
    """
    if not validators:
        return "| (none) | - | - | - |"

    rows = []
    for v in validators:
        blocking = "✅" if v.get('blocking', False) else "❌"
        name = v.get('name', v.get('id', 'Unknown'))
        model = v.get('model', 'codex')
        description = v.get('description', '')
        rows.append(
            f"| {name} | {model} | {blocking} | {description} |"
        )
    return "\n".join(rows)


def _format_specialized_validator_table(validators: List[Dict[str, Any]]) -> str:
    """Format specialized validators with trigger patterns.

    Args:
        validators: List of specialized validator metadata dictionaries

    Returns:
        Formatted markdown table rows with triggers
    """
    if not validators:
        return "| (none) | - | - | - |"

    rows = []
    for v in validators:
        blocking = "✅" if v.get('blocking', False) else "❌"
        name = v.get('name', v.get('id', 'Unknown'))
        model = v.get('model', 'codex')
        triggers = v.get('fileTriggers', v.get('triggers', []))
        triggers_str = ", ".join(triggers[:3]) if triggers else "(no triggers)"
        if len(triggers) > 3:
            triggers_str += ", ..."
        rows.append(f"| {name} | {model} | {blocking} | {triggers_str} |")
    return "\n".join(rows)


def _format_agent_table(agents: List[Dict[str, Any]]) -> str:
    """Format agents as markdown table rows."""
    if not agents:
        return "| (none) | - | - | - |"

    rows = []
    for agent in agents:
        rows.append(
            f"| {agent['name']} | {agent.get('type', 'implementer')} | "
            f"{agent.get('model', 'codex')} | {agent.get('description', '')} |"
        )
    return "\n".join(rows)


def _format_agent_details(agents: List[Dict[str, Any]]) -> str:
    """Format detailed agent descriptions."""
    if not agents:
        return "_No agents registered._\n\n"

    sections = []
    for agent in agents:
        sections.append(
            f"### {agent['name']}\n\n"
            f"**Model**: {agent.get('model', 'codex')}\n"
            f"**Type**: {agent.get('type', 'implementer')}\n"
            f"**Prompt**: `agents/{agent['name']}.md`\n\n"
            f"{agent.get('description', 'No description available.')}\n"
        )
    return "\n".join(sections)


__all__ = [
    "generate_available_agents",
    "generate_available_validators",
]
