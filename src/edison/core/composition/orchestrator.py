from __future__ import annotations

"""Orchestrator manifest assembly and delegation helpers."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Iterable

from edison.core.file_io import utils as io_utils
from .packs import yaml
from ..utils.text import render_conditional_includes
from .formatting import render_orchestrator_json, render_orchestrator_markdown
from .validators import collect_validators
from .workflow import get_workflow_loop_instructions


def collect_agents(repo_root: Path, packs_dir: Path, active_packs: List[str], project_dir: Path) -> Dict[str, List[str]]:
    """Collect agents from Core + Packs + Project using AgentRegistry."""
    from . import agents as agents_module

    AgentRegistry = agents_module.AgentRegistry

    registry = AgentRegistry(repo_root=repo_root)
    # Ensure project overlays resolve to the provided project_dir during tests
    registry.project_dir = project_dir
    agents: Dict[str, List[str]] = {
        "generic": [],
        "specialized": [],
        "project": [],
    }

    core_agents = registry.discover_core_agents()
    generic_names = sorted(core_agents.keys())
    agents["generic"] = generic_names

    specialized_set: set[str] = set()
    for name in generic_names:
        overlays = registry.discover_pack_overlays(name, active_packs)
        if overlays:
            specialized_set.add(name)

    for name in registry.discover_pack_agent_names(active_packs):
        if name not in core_agents:
            specialized_set.add(name)

    agents["specialized"] = sorted(specialized_set)

    project_names: List[str] = []
    for name in generic_names:
        if registry.project_overlay_path(name) is not None:
            project_names.append(name)

    project_agents_dir = project_dir / "agents"
    if project_agents_dir.exists():
        for agent_file in sorted(project_agents_dir.glob("*.md")):
            stem = agent_file.stem
            if stem not in core_agents and stem not in project_names:
                project_names.append(stem)

    agents["project"] = sorted(project_names)
    return agents


def collect_packs(packs_dir: Path, active_packs: Iterable[str]) -> List[Dict[str, str]]:
    """Return metadata for active packs (id, name, version).

    Falls back to sensible defaults if pack.yml is missing or PyYAML is unavailable.
    """

    packs: List[Dict[str, str]] = []
    for pack_name in active_packs:
        base_meta = {
            "id": str(pack_name),
            "name": str(pack_name).replace("-", " ").title(),
            "version": "0.0.0",
        }

        pack_yml = packs_dir / pack_name / "pack.yml"
        if pack_yml.exists() and yaml is not None:
            try:
                data = yaml.safe_load(pack_yml.read_text(encoding="utf-8")) or {}
                meta_block = data.get("pack") or {}
                if isinstance(meta_block, dict):
                    base_meta["id"] = str(meta_block.get("id") or base_meta["id"])
                    base_meta["name"] = str(meta_block.get("name") or base_meta["name"])
                    base_meta["version"] = str(meta_block.get("version") or base_meta["version"])
            except Exception:
                pass

        packs.append(base_meta)

    return packs


def collect_mandatory_guidelines(repo_root: Path, packs_dir: Path, active_packs: List[str]) -> List[Dict]:
    """Collect mandatory preload guidelines for orchestrators."""
    mandatory: List[Dict] = [
        {
            "file": ".edison/core/guidelines/SESSION_WORKFLOW.md",
            "purpose": "Session workflow rules",
        },
        {
            "file": ".edison/core/guidelines/DELEGATION.md",
            "purpose": "Delegation priority chain",
        },
        {
            "file": ".edison/core/guidelines/TDD.md",
            "purpose": "TDD requirements",
        },
    ]

    for pack_name in active_packs:
        pack_guidelines_dir = packs_dir / pack_name / "guidelines"
        if not pack_guidelines_dir.exists():
            continue
        for guideline_file in sorted(pack_guidelines_dir.glob("*.md")):
            mandatory.append(
                {
                    "file": str(guideline_file.relative_to(repo_root)),
                    "purpose": f"{pack_name} pack: {guideline_file.stem}",
                    "pack": pack_name,
                }
            )

    return mandatory


def collect_role_guidelines(repo_root: Path, core_dir: Path) -> Dict[str, List[Dict[str, str]]]:
    """Discover role-specific guideline files for agents, validators, and orchestrators."""

    categories = {
        "agents": core_dir / "guidelines" / "agents",
        "validators": core_dir / "guidelines" / "validators",
        "orchestrators": core_dir / "guidelines" / "orchestrators",
    }

    results: Dict[str, List[Dict[str, str]]] = {}
    for role, path in categories.items():
        entries: List[Dict[str, str]] = []
        if path.exists():
            for guideline in sorted(path.glob("*.md")):
                entries.append(
                    {
                        "file": str(guideline.relative_to(repo_root)),
                        "title": guideline.stem.replace("_", " ").replace("-", " ").title(),
                    }
                )
        results[role] = entries

    return results


def compose_claude_orchestrator(engine, output_dir: Path | str) -> Path:
    """Generate Claude Code orchestrator (CLAUDE.md)."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    orchestrator_parts: List[str] = [
        "# Claude Code Orchestrator",
        "<!-- GENERATED - DO NOT EDIT -->",
        "<!-- Source: Edison composition system -->",
        "<!-- Regenerate: scripts/prompts/compose --claude -->",
        "\n---\n\n",
    ]

    core_brief = engine.repo_root / ".edison" / "packs" / "clients" / "claude" / "CLAUDE.md"
    if core_brief.exists():
        raw = core_brief.read_text(encoding="utf-8")
        orchestrator_parts.append(engine.resolve_includes(raw, core_brief))
    else:
        raise FileNotFoundError(f"Missing orchestrator brief: {core_brief}")

    project_orch = engine.project_dir / "claude" / "ORCHESTRATOR.md"
    if project_orch.exists():
        raw = project_orch.read_text(encoding="utf-8")
        orchestrator_parts.append("\n\n---\n\n")
        orchestrator_parts.append("## Project-Specific Guidance\n\n")
        orchestrator_parts.append(engine.resolve_includes(raw, project_orch))

    content = "\n".join(orchestrator_parts)

    packs = engine._active_packs()
    if packs:
        content = render_conditional_includes(content, packs)
    output_file = out_dir / "CLAUDE.md"
    output_file.write_text(content, encoding="utf-8")

    return output_file


def compose_claude_agents(engine, output_dir: Path | str | None = None, *, packs_override: Optional[List[str]] = None) -> Dict[str, Path]:
    """Compose agents for Claude Code consumption."""
    from . import agents as agents_module

    AgentRegistry = agents_module.AgentRegistry
    AgentError = agents_module.AgentError

    registry = AgentRegistry(repo_root=engine.repo_root)
    registry.project_dir = engine.project_dir

    core_agents = registry.discover_core_agents()
    if not core_agents:
        return {}

    if packs_override is not None:
        packs = packs_override
    else:
        try:
            packs = engine._active_packs()
        except Exception:
            packs = []

    out_dir = Path(output_dir) if output_dir is not None else (
        engine.project_dir / "_generated" / "agents"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    results: Dict[str, Path] = {}
    for name in sorted(core_agents.keys()):
        try:
            text = registry.compose_agent(name, packs=packs)
        except AgentError:
            continue

        out_file = out_dir / f"{name}.md"
        out_file.write_text(text, encoding="utf-8")
        results[name] = out_file

    return results


def load_delegation_config(config: Dict, core_dir: Path, project_dir: Path) -> Dict:
    """Load delegation configuration subset relevant for orchestrators.

    Merges on-disk delegation config (core + project) with in-memory config.
    """
    priority: Dict = {}
    role_mapping: Dict = {}
    file_pattern_rules: List[Dict] = []
    task_type_rules: Dict = {}
    sub_agent_defaults: Dict = {}

    cfg = config or {}
    delegation_cfg: Dict = {}

    for path in [
        core_dir / "delegation" / "config.json",
        project_dir / "delegation" / "config.json",
    ]:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict):
                    delegation_cfg.update(data)
            except Exception:
                continue

    if isinstance(cfg, dict) and isinstance(cfg.get("delegation"), dict):
        delegation_cfg.update(cfg.get("delegation") or {})
    elif isinstance(cfg, dict) and cfg.get("delegation") is not None:
        # Log warning if delegation is present but not a dict (defensive guard)
        pass  # Skip non-dict delegation values

    if isinstance(delegation_cfg.get("roleMapping"), dict):
        role_mapping = delegation_cfg.get("roleMapping") or {}

    priority_cfg: Dict = {}
    if isinstance(cfg, dict) and isinstance(cfg.get("priority"), dict):
        priority_cfg = cfg.get("priority") or {}
    elif isinstance(delegation_cfg.get("priority"), dict):
        priority_cfg = delegation_cfg.get("priority") or {}

    if isinstance(priority_cfg, dict):
        priority = {
            "implementers": list(priority_cfg.get("implementers") or []),
            "validators": list(priority_cfg.get("validators") or []),
        }

    raw_file_patterns = delegation_cfg.get("filePatternRules")
    if isinstance(raw_file_patterns, dict):
        for pattern, rule in raw_file_patterns.items():
            if not isinstance(rule, dict):
                continue
            entry = {"pattern": pattern}
            entry.update(rule)
            file_pattern_rules.append(entry)

    raw_task_types = delegation_cfg.get("taskTypeRules")
    if isinstance(raw_task_types, dict):
        task_type_rules = raw_task_types

    raw_defaults = delegation_cfg.get("subAgentDefaults")
    if isinstance(raw_defaults, dict):
        sub_agent_defaults = raw_defaults

    return {
        "priority": priority,
        "roleMapping": role_mapping,
        "filePatternRules": file_pattern_rules,
        "taskTypeRules": task_type_rules,
        "subAgentDefaults": sub_agent_defaults,
    }


def count_validators(validators: Dict[str, List[Dict]]) -> int:
    """Count total validators in roster."""
    return (
        len(validators.get("global", []))
        + len(validators.get("critical", []))
        + len(validators.get("specialized", []))
    )


def count_agents(agents: Dict[str, List[str]]) -> int:
    """Count total agents across categories."""
    return (
        len(agents.get("generic", []))
        + len(agents.get("specialized", []))
        + len(agents.get("project", []))
    )


def compose_orchestrator_manifest(
    *,
    config: Dict,
    repo_root: Path,
    core_dir: Path,
    packs_dir: Path,
    project_dir: Path,
    active_packs: List[str],
    output_dir: Path,
) -> Dict[str, Path]:
    """Generate orchestrator manifest (JSON only) for LLM orchestrators.

    DEPRECATED: ORCHESTRATOR_GUIDE.md generation removed (T-011).
    Use constitutions/ORCHESTRATORS.md instead.

    Returns:
        Dict with 'json' key pointing to orchestrator-manifest.json
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    validators = collect_validators(
        config,
        repo_root=repo_root,
        project_dir=project_dir,
        packs_dir=packs_dir,
        active_packs=active_packs,
    )
    agents = collect_agents(repo_root, packs_dir, active_packs, project_dir)
    packs = collect_packs(packs_dir, active_packs)
    mandatory_guidelines = collect_mandatory_guidelines(repo_root, packs_dir, active_packs)
    role_guidelines = collect_role_guidelines(repo_root, core_dir)
    delegation = load_delegation_config(config, core_dir, project_dir)

    data = {
        "generated": datetime.now().isoformat(),
        "version": "2.0.0",
        "config": config,
        "composition": {
            "packs": active_packs,
            "guidelinesCount": len(list(core_dir.glob("guidelines/**/*.md"))),
            "validatorsCount": count_validators(validators),
            "agentsCount": count_agents(agents),
        },
        "packs": packs,
        "validators": validators,
        "agents": agents,
        "guidelines": mandatory_guidelines,
        "roleGuidelines": role_guidelines,
        "delegation": delegation,
        "workflowLoop": get_workflow_loop_instructions(),
    }

    # DEPRECATED: ORCHESTRATOR_GUIDE.md no longer generated (T-011)
    # Constitution system (constitutions/ORCHESTRATORS.md) replaces it
    # md_content = render_orchestrator_markdown(data)
    # md_file = output_path / "ORCHESTRATOR_GUIDE.md"
    # md_file.write_text(md_content, encoding="utf-8")

    json_content = render_orchestrator_json(data)
    json_file = output_path / "orchestrator-manifest.json"
    io_utils.write_json_safe(json_file, json_content, indent=2)

    # Return only JSON manifest (no markdown)
    return {"json": json_file}


__all__ = [
    "collect_agents",
    "collect_packs",
    "collect_mandatory_guidelines",
    "collect_role_guidelines",
    "collect_validators",
    "load_delegation_config",
    "get_workflow_loop_instructions",
    "compose_orchestrator_manifest",
    "count_agents",
    "count_validators",
    "compose_claude_orchestrator",
    "compose_claude_agents",
]
