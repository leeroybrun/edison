from __future__ import annotations

"""Orchestrator manifest assembly and delegation helpers."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Iterable

from .packs import yaml

from ..composition_utils import render_conditional_includes
from .formatting import render_orchestrator_json, render_orchestrator_markdown


def get_workflow_loop_instructions() -> Dict:
    """Return workflow loop instructions for orchestrators."""
    return {
        "command": "scripts/session next <session-id>",
        "frequency": "Before EVERY action",
        "readOrder": [
            "1. 📋 APPLICABLE RULES (read FIRST)",
            "2. 🎯 RECOMMENDED ACTIONS (read AFTER rules)",
            "3. 🤖 DELEGATION HINT (follow priority chain)",
            "4. 🔍 VALIDATORS (auto-detected from git diff)",
        ],
    }


def _validator_map(roster: Dict[str, List[Dict]]) -> Dict[str, Dict]:
    """Build quick lookup map of validator definitions keyed by id."""
    mapping: Dict[str, Dict] = {}
    for entries in roster.values():
        for entry in entries or []:
            if isinstance(entry, dict) and entry.get("id"):
                mapping[entry["id"]] = entry
    return mapping


def _infer_validator_metadata(
    validator_id: str,
    *,
    repo_root: Path,
    project_dir: Path,
    packs_dir: Path,
    active_packs: Iterable[str],
) -> Dict:
    """Best-effort metadata extraction for validators defined only by id."""

    inferred: Dict[str, object] = {
        "id": validator_id,
        "name": validator_id.replace("-", " ").title(),
        "model": "codex",
        "triggers": ["*"],
        "alwaysRun": False,
        "blocksOnFail": False,
    }

    def _first_existing(paths: Iterable[Path]) -> Path | None:
        for p in paths:
            if p.exists():
                return p
        return None

    candidate_paths = [
        project_dir / "_generated" / "validators" / f"{validator_id}.md",
        project_dir / ".cache" / "composed" / f"{validator_id}.md",
        project_dir / "validators" / "specialized" / f"{validator_id}.md",
        repo_root / ".edison" / "core" / "validators" / "specialized" / f"{validator_id}.md",
    ]

    for pack in active_packs:
        candidate_paths.append(packs_dir / pack / "validators" / f"{validator_id}.md")

    path = _first_existing(candidate_paths)
    if not path:
        return inferred

    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return inferred

    headers = re.findall(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    for h in headers:
        cleaned = h.strip()
        if cleaned and cleaned.lower() != "core edison principles":
            inferred["name"] = cleaned
            break

    model = re.search(r"\*\*Model\*\*:\s*([^\n*]+)", text)
    if model:
        inferred["model"] = model.group(1).strip()

    triggers_line = re.search(r"\*\*Triggers\*\*:\s*([^\n]+)", text)
    if triggers_line:
        triggers = re.findall(r"`([^`]+)`", triggers_line.group(1))
        if triggers:
            inferred["triggers"] = triggers

    if re.search(r"\*\*Blocks on Fail\*\*:\s*✅\s*YES", text, flags=re.IGNORECASE):
        inferred["blocksOnFail"] = True

    return inferred  # type: ignore[return-value]


def _normalize_validator_entries(
    raw_entries,
    *,
    fallback_map: Dict[str, Dict],
    repo_root: Path,
    project_dir: Path,
    packs_dir: Path,
    active_packs: Iterable[str],
) -> List[Dict]:
    """Normalize roster entries into dicts, enriching ids with inferred metadata."""
    normalized: List[Dict] = []
    for entry in raw_entries or []:
        if isinstance(entry, dict):
            if "id" in entry:
                normalized.append(entry)
        elif isinstance(entry, str) and entry:
            base = fallback_map.get(entry)
            if base:
                normalized.append(base)
            else:
                normalized.append(
                    _infer_validator_metadata(
                        entry,
                        repo_root=repo_root,
                        project_dir=project_dir,
                        packs_dir=packs_dir,
                        active_packs=active_packs,
                    )
                )
    return normalized


def _merge_rosters(
    base_roster: Dict[str, List[Dict]],
    override_roster: Dict[str, List[Dict]],
    *,
    repo_root: Path,
    project_dir: Path,
    packs_dir: Path,
    active_packs: Iterable[str],
) -> Dict[str, List[Dict]]:
    """Merge validation + validators rosters without hardcoded ids."""
    result: Dict[str, List[Dict]] = {}
    base_map = _validator_map(base_roster)

    for bucket in ("global", "critical", "specialized"):
        base_entries = _normalize_validator_entries(
            base_roster.get(bucket, []),
            fallback_map=base_map,
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=active_packs,
        )

        override_entries = _normalize_validator_entries(
            override_roster.get(bucket, []),
            fallback_map=base_map,
            repo_root=repo_root,
            project_dir=project_dir,
            packs_dir=packs_dir,
            active_packs=active_packs,
        )

        if override_entries:
            seen = {e["id"] for e in override_entries if isinstance(e, dict) and e.get("id")}
            merged: List[Dict] = list(override_entries)
            for entry in base_entries:
                if entry.get("id") not in seen:
                    merged.append(entry)
            result[bucket] = merged
        else:
            result[bucket] = base_entries

    return result


def collect_validators(
    config: Dict,
    *,
    repo_root: Path,
    project_dir: Path,
    packs_dir: Path,
    active_packs: Iterable[str],
) -> Dict[str, List[Dict]]:
    """Collect validator roster from merged configuration (validation + validators)."""
    validation_cfg = ((config or {}).get("validation", {}) or {})
    validators_cfg = ((config or {}).get("validators", {}) or {})

    base_roster = (validation_cfg.get("roster", {}) or {}) if isinstance(validation_cfg, dict) else {}
    override_roster = (validators_cfg.get("roster", {}) or {}) if isinstance(validators_cfg, dict) else {}

    return _merge_rosters(
        base_roster,
        override_roster,
        repo_root=repo_root,
        project_dir=project_dir,
        packs_dir=packs_dir,
        active_packs=active_packs,
    )


def collect_agents(repo_root: Path, packs_dir: Path, active_packs: List[str], project_dir: Path) -> Dict[str, List[str]]:
    """Collect agents from Core + Packs + Project using AgentRegistry."""
    from .. import agents as agents_module  # type: ignore

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
    from .. import agents as agents_module  # type: ignore

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
    """Generate orchestrator guide (Markdown + JSON) for LLM orchestrators."""
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

    md_content = render_orchestrator_markdown(data)
    md_file = output_path / "ORCHESTRATOR_GUIDE.md"
    md_file.write_text(md_content, encoding="utf-8")

    json_content = render_orchestrator_json(data)
    json_file = output_path / "orchestrator-manifest.json"
    json_file.write_text(json.dumps(json_content, indent=2), encoding="utf-8")

    return {"markdown": md_file, "json": json_file}


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
