from __future__ import annotations

"""Formatting helpers for Zen prompts and orchestrator outputs."""

import re
from pathlib import Path
from typing import Dict, List

from ..utils.text import render_conditional_includes
from ..file_io.utils import ensure_dir
from .path_utils import resolve_project_dir_placeholders


def format_for_zen(content: str) -> str:
    """Format composed content for Zen MCP consumption (plain text)."""
    txt = content.replace("```python", "").replace("```typescript", "").replace("```", "")
    txt = re.sub(r"^### (.+)$", r"**\1**", txt, flags=re.MULTILINE)
    txt = re.sub(r"^## (.+)$", r"\n**\1**\n", txt, flags=re.MULTILINE)
    txt = re.sub(r"^# (.+)$", r"\n=== \1 ===\n", txt, flags=re.MULTILINE)
    return txt


def format_rules_context(rules_config: Dict) -> str:
    """Render rules configuration into human-readable Markdown."""
    lines: List[str] = []
    lines.append("## State-Based Rules")

    for state, rules in (rules_config.get("byState", {}) or {}).items():
        lines.append(f"\n**{str(state).upper()}**:")
        for rule in rules or []:
            blocking = "🔴 BLOCKING" if rule.get("blocking") else "⚠️  WARNING"
            desc = rule.get("description", "")
            lines.append(f"  - [{blocking}] {desc}")
            if rule.get("reference"):
                lines.append(f"    Reference: {rule['reference']}")

    lines.append("\n## Task-Type Rules")
    for task_type, rules in (rules_config.get("byTaskType", {}) or {}).items():
        lines.append(f"\n**{str(task_type).upper()}**:")
        for rule in rules or []:
            blocking = "🔴 BLOCKING" if rule.get("blocking") else "⚠️  WARNING"
            desc = rule.get("description", "")
            lines.append(f"  - [{blocking}] {desc}")

    return "\n".join(lines)


def render_orchestrator_markdown(data: Dict) -> str:
    """Render orchestrator guide as Markdown for LLM consumption."""
    md: List[str] = []

    project_cfg = (data.get("config") or {}).get("project", {}) or {}
    if not isinstance(project_cfg, dict):
        project_cfg = {}
    project_name = project_cfg.get("name", "Project")

    composition = data.get("composition", {})
    if not isinstance(composition, dict):
        composition = {}
    packs = composition.get("packs", []) or []

    guidelines = data.get("guidelines", []) or []
    if not isinstance(guidelines, list):
        guidelines = []
    framework_guidelines = [g for g in guidelines if "pack" not in g]
    pack_guidelines = [g for g in guidelines if "pack" in g]
    validation_cfg = (data.get("config") or {}).get("validation", {}) or {}
    blocking_ids = set(validation_cfg.get("blocking_validators", []) or [])

    md.append(f"# {project_name} Orchestrator Guide")
    md.append(f"**Generated**: {data['generated']}")
    md.append(
        f"**From**: defaults.yaml + config.yml + {len(packs)} active packs"
    )
    md.append("**Regenerate**: scripts/prompts/compose --orchestrator")
    md.append("\n---\n")

    md.append("## 📋 Mandatory Preloads (Session Start)\n")
    md.append("**Framework Guidelines** (ALWAYS read):")
    if framework_guidelines:
        md.append("| File | Purpose |")
        md.append("|------|---------|")
        for guideline in framework_guidelines:
            md.append(f"| {guideline['file']} | {guideline['purpose']} |")
    else:
        md.append("- None discovered (check .edison/core/guidelines)")
    md.append("\n")

    if pack_guidelines:
        md.append("### Pack Guidelines (active packs)")
        md.append("| Pack | File | Purpose |")
        md.append("|------|------|---------|")
        for guideline in sorted(pack_guidelines, key=lambda g: (g.get("pack", ""), g.get("file", ""))):
            md.append(
                f"| {guideline.get('pack', '-')} | {guideline['file']} | {guideline.get('purpose', '')} |"
            )
        md.append("\n")

    role_guidelines = data.get("roleGuidelines") or {}
    if not isinstance(role_guidelines, dict):
        role_guidelines = {}
    if role_guidelines:
        md.append("## 🧑‍💻 Role-Specific Guidelines\n")
        label_map = {
            "agents": "Agents",
            "validators": "Validators",
            "orchestrators": "Orchestrators",
        }
        for key in ("agents", "validators", "orchestrators"):
            entries = role_guidelines.get(key) or []
            md.append(f"### {label_map.get(key, key.title())}")
            if entries:
                for entry in entries:
                    title = entry.get("title") or Path(entry.get("file", "")).stem
                    md.append(f"- {entry.get('file')} ({title})")
            else:
                md.append("- None discovered")
            md.append("")

    md.append("## 🧩 Active Packs\n")
    if packs:
        for pack in packs:
            md.append(f"- {pack}")
    else:
        md.append("- No packs active (packs.enabled = false)")
    md.append("\n")

    def _format_triggers(raw: List[str] | None) -> str:
        triggers = raw or ["*"]
        if len(triggers) > 3:
            return ", ".join(triggers[:3]) + ", …"
        return ", ".join(triggers)

    def _flag(val: bool) -> str:
        return "Yes" if bool(val) else "No"

    md.append("## 🔍 Available Validators\n")
    md.append("### Global Validators (ALWAYS run)")
    md.append("| Validator | Model | Triggers | Always Run | Blocking |")
    md.append("|-----------|-------|----------|------------|----------|")

    validators = data.get("validators", {})
    if not isinstance(validators, dict):
        validators = {}

    for v in validators.get("global", []):
        block_val = v.get("blocksOnFail", v.get("blocking", False)) or v.get("id") in blocking_ids
        md.append(
            "| {name} ({vid}) | {model} | `{triggers}` | {always} | {block} |".format(
                name=v.get("name", "-"),
                vid=v.get("id", "-"),
                model=v.get("model", "codex"),
                triggers=_format_triggers(v.get("triggers")),
                always=_flag(v.get("alwaysRun", False)),
                block=_flag(block_val),
            )
        )
    md.append("\n")

    critical = validators.get("critical", [])
    if critical:
        md.append("### Critical Validators")
        md.append("| Validator | Model | Triggers | Blocking |")
        md.append("|-----------|-------|----------|----------|")
        for v in critical:
            block_val = v.get("blocksOnFail", v.get("blocking", False)) or v.get("id") in blocking_ids
            md.append(
                "| {name} ({vid}) | {model} | `{triggers}` | {block} |".format(
                    name=v.get("name", "-"),
                    vid=v.get("id", "-"),
                    model=v.get("model", "codex"),
                    triggers=_format_triggers(v.get("triggers")),
                    block=_flag(block_val),
                )
            )
        md.append("\n")

    specialized = validators.get("specialized", [])
    if specialized:
        md.append("### Specialized Validators (triggered by file patterns)")
        md.append("| Validator | Model | Triggers | Blocking |")
        md.append("|-----------|-------|----------|----------|")
        for v in specialized:
            block_val = v.get("blocksOnFail", v.get("blocking", False)) or v.get("id") in blocking_ids
            md.append(
                "| {name} ({vid}) | {model} | `{triggers}` | {block} |".format(
                    name=v.get("name", "-"),
                    vid=v.get("id", "-"),
                    model=v.get("model", "codex"),
                    triggers=_format_triggers(v.get("triggers")),
                    block=_flag(block_val),
                )
            )
        md.append("\n")

    md.append("## 🤖 Available Agents\n")
    md.append(
        f"**Total**: {composition.get('agentsCount', 0)} (dynamic from AgentRegistry)"
    )

    agents = data.get("agents", {})
    if not isinstance(agents, dict):
        agents = {}

    md.append("### Generic Agents (Core framework)")
    for agent in agents.get("generic", []):
        md.append(f"- {agent}")
    md.append("\n")

    specialized_agents = agents.get("specialized", [])
    if specialized_agents:
        md.append("### Specialized Agents (From packs)")
        for agent in specialized_agents:
            md.append(f"- {agent}")
        md.append("\n")

    project_agents = agents.get("project", [])
    if project_agents:
        md.append("### Project Agents (<project_config_dir>/agents)")
        for agent in project_agents:
            md.append(f"- {agent}")
        md.append("\n")

    md.append("## 🔁 Workflow Loop (CRITICAL)\n")
    md.append("**Before EVERY action**:")
    md.append("```bash")
    md.append(data["workflowLoop"]["command"])
    md.append("```")
    md.append("")
    md.append("**Read output sections IN ORDER:**")
    for step in data["workflowLoop"]["readOrder"]:
        md.append(step)
    md.append("")

    delegation = data.get("delegation") or {}
    # Guard against Path objects being passed instead of dicts
    if not isinstance(delegation, dict):
        delegation = {}
    if delegation:
        md.append("## 🧭 Delegation Configuration\n")

        priority = delegation.get("priority") or {}
        if priority:
            md.append("### Priority Chains")
            implementers = priority.get("implementers") or []
            validators = priority.get("validators") or []
            if implementers:
                md.append(f"- Implementers: {', '.join(implementers)}")
            if validators:
                md.append(f"- Validators: {', '.join(validators)}")
            md.append("")

        role_mapping = delegation.get("roleMapping") or {}
        if isinstance(role_mapping, dict) and role_mapping:
            md.append("### Role Mapping (Generic → Project)")
            md.append("| Generic | Concrete |")
            md.append("|---------|----------|")
            for generic, concrete in sorted(role_mapping.items()):
                md.append(f"| {generic} | {concrete} |")
            md.append("")

        file_rules = delegation.get("filePatternRules") or []
        if isinstance(file_rules, list) and file_rules:
            md.append("### File Pattern Rules")
            md.append("| Pattern | Model | Sub-agent | Delegation |")
            md.append("|---------|-------|-----------|------------|")
            for rule in file_rules[:10]:
                pattern = rule.get("pattern", "")
                model = rule.get("preferredModel") or ""
                preferred_models = rule.get("preferredModels") or []
                if not model and isinstance(preferred_models, list) and preferred_models:
                    model = ", ".join(preferred_models)
                sub_agent = rule.get("subAgentType") or ""
                delegation_mode = rule.get("delegation") or ""
                md.append(
                    f"| `{pattern}` | {model or '-'} | {sub_agent or '-'} | {delegation_mode or '-'} |"
                )
            md.append("")

        task_rules = delegation.get("taskTypeRules") or {}
        if isinstance(task_rules, dict) and task_rules:
            md.append("### Task Type Defaults")
            for task_type, rule in sorted(task_rules.items()):
                if not isinstance(rule, dict):
                    continue
                model = rule.get("preferredModel") or ""
                sub_agent = rule.get("subAgentType") or ""
                delegation_mode = rule.get("delegation") or ""
                md.append(
                    f"- **{task_type}** → model: {model or '-'}, "
                    f"sub-agent: {sub_agent or '-'}, delegation: {delegation_mode or '-'}"
                )
            md.append("")

    md.append("---")
    md.append(
        f"**Generated by**: Edison Composition Engine v{data.get('version', '2.0.0')}"
    )
    md.append(
        "**Dependencies**: "
        f"{len(packs)} packs, "
        f"{data['composition']['guidelinesCount']} guidelines, "
        f"{data['composition']['validatorsCount']} validators, "
        f"{data['composition']['agentsCount']} agents"
    )

    return "\n".join(md)


def render_orchestrator_json(data: Dict) -> Dict:
    """Render orchestrator manifest as JSON structure."""
    return {
        "version": data["version"],
        "generated": data["generated"],
        "composition": data["composition"],
        "packs": data.get("packs", []),
        "validators": data["validators"],
        "agents": data["agents"],
        "guidelines": data["guidelines"],
        "roleGuidelines": data.get("roleGuidelines", {}),
        "delegation": data["delegation"],
        "workflowLoop": data["workflowLoop"],
    }


def compose_for_role(engine, role: str) -> str:
    """Compose prompt content for a specific role using unified path resolution.
    
    Uses UnifiedPathResolver for consistent path discovery.
    """
    from .unified import UnifiedPathResolver
    
    parts: List[str] = []
    
    # Use unified path resolver
    resolver = UnifiedPathResolver(engine.repo_root, "validators")

    core_template = resolver.core_dir / "validators" / "global" / f"{role}.md"
    if core_template.exists():
        parts.append(f"# Edison Core Context for {role}")
        parts.append(engine.resolve_includes(core_template.read_text(encoding="utf-8"), core_template))

    active_packs = engine._active_packs()
    if active_packs:
        # Reference shared tech-stack context instead of duplicating pack contexts
        parts.append("\n# Tech-Stack Pack Contexts")
        parts.append("<!-- MANDATORY READ: {{PROJECT_EDISON_DIR}}/core/guidelines/validators/TECH_STACK_CONTEXT.md -->")
        parts.append("")
        parts.append("**Note**: This validator uses tech-stack guidelines from the shared context file.")
        parts.append("The composition engine replaces inline pack duplication with this reference to reduce")
        parts.append("prompt size and maintain DRY principles across all validators.")

    rules_cfg = (engine.config or {}).get("rules", {}) or {}
    if rules_cfg.get("enforcement"):
        parts.append("\n# Project Rules")
        parts.append(format_rules_context(rules_cfg))

    # Use unified discovery for overlay
    overlay_path = resolver.project_dir / "validators" / "overlays" / f"{role}.md"
    if overlay_path.exists():
        parts.append("\n# Project Overlay")
        parts.append(engine.resolve_includes(overlay_path.read_text(encoding="utf-8"), overlay_path))

    content = "\n\n".join(parts)
    if active_packs:
        content = render_conditional_includes(content, active_packs)
    return content


def compose_zen_prompts(engine, output_dir: str | Path) -> Dict[str, Path]:
    """Compose Zen MCP system prompts for configured roles."""
    output_path = Path(output_dir)
    ensure_dir(output_path)

    results: Dict[str, Path] = {}

    zen_config = (engine.config or {}).get("zen", {}) or {}
    roles = zen_config.get("roles", ["codex", "gemini", "claude"]) or [
        "codex",
        "gemini",
        "claude",
    ]

    for role in roles:
        content = compose_for_role(engine, role)
        zen_content = format_for_zen(content)
        out_file = output_path / f"{role}.txt"
        zen_content = resolve_project_dir_placeholders(
            zen_content,
            project_dir=engine.project_dir,
            target_path=out_file,
            repo_root=engine.repo_root,
        )
        out_file.write_text(zen_content, encoding="utf-8")
        results[role] = out_file
        print(f"✓ Zen prompt for {role}: {out_file}")

    return results


__all__ = [
    "format_for_zen",
    "format_rules_context",
    "render_orchestrator_markdown",
    "render_orchestrator_json",
]
