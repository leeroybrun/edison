from __future__ import annotations

"""Constitution composition engine for Edison.

Builds the three role constitutions (orchestrator, agents, validators) from
layered sources:
  - Core templates:      <repo>/src/edison/data/constitutions/*-base.md
  - Pack additions:      <repo>/.edison/packs/<pack>/constitutions/*-additions.md
  - Project overrides:   <project_config_dir>/constitutions/*-overrides.md

Templates use a small Handlebars-style syntax. Rendering covers:
  - {{source_layers}}                → provenance of the composed layers
  - {{generated_date}}               → ISO timestamp
  - {{#each mandatoryReads.<role>}}  → bullet list from constitution.yaml
  - {{#each rules.<role>}}           → rules filtered by applies_to
  - {{#each delegationRules}}        → delegation rules (when provided)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from edison.core.config import ConfigManager
from edison.core.config.domains import PacksConfig
from edison.core.utils.io import ensure_directory
from edison.core.utils.time import utc_timestamp
from edison.core.utils.paths import get_project_config_dir
from ..output.headers import resolve_version
from ..path_utils import resolve_project_dir_placeholders

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for type checkers
    from edison.core.rules import RulesEngine


ROLE_MAP: Dict[str, Dict[str, str]] = {
    "orchestrator": {"slug": "orchestrator", "rules": "orchestrator", "mandatory": "orchestrator"},
    "agents": {"slug": "agents", "rules": "agent", "mandatory": "agents"},
    "agent": {"slug": "agents", "rules": "agent", "mandatory": "agents"},
    "validators": {"slug": "validators", "rules": "validator", "mandatory": "validators"},
    "validator": {"slug": "validators", "rules": "validator", "mandatory": "validators"},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalize_role(role: str) -> str:
    normalized = (role or "").strip().lower()
    if normalized not in ROLE_MAP:
        raise ValueError(
            f"Invalid role: {role}. Must be orchestrator, agent(s), or validator(s)"
        )
    # Canonical keys: orchestrator, agents, validators
    if normalized == "agent":
        return "agents"
    if normalized == "validator":
        return "validators"
    return normalized


def _core_base_path(repo_root: Path) -> Path:
    """Resolve core layer root using composition path resolution."""
    from ..core import CompositionPathResolver
    return CompositionPathResolver(repo_root, "constitutions").core_dir


def _packs_root(repo_root: Path, config: Dict[str, Any]) -> Path:
    """Resolve packs directory using composition path resolution.
    
    Respects config override for directory, otherwise uses composition resolver.
    """
    config_dir = get_project_config_dir(repo_root, create=False)
    directory = (config.get("packs", {}) or {}).get("directory")
    
    if directory:
        path = (repo_root / directory).resolve()
        if path.exists():
            return path
    
    # Use composition path resolver
    from ..core import CompositionPathResolver
    return CompositionPathResolver(repo_root).packs_dir


def _project_constitutions_dir(repo_root: Path) -> Path:
    project_root = get_project_config_dir(repo_root)
    return project_root / "constitutions"


def _active_packs(repo_root: Path) -> List[str]:
    """Get active packs via PacksConfig."""
    return PacksConfig(repo_root=repo_root).active_packs


def _replace_each_block(template: str, token: str, rendered: str) -> str:
    """Replace a {{#each token}}...{{/each}} block with rendered text."""
    start_marker = f"{{{{#each {token}}}}}"
    end_marker = "{{/each}}"

    while True:
        start = template.find(start_marker)
        if start == -1:
            break
        end = template.find(end_marker, start)
        if end == -1:
            break
        template = template[:start] + rendered + template[end + len(end_marker):]
    return template


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_rules_for_role(role: str) -> List[Dict[str, Any]]:
    """Extract rules that apply to a specific role using bundled registry."""
    normalized = _normalize_role(role)
    rule_key = ROLE_MAP[normalized]["rules"]

    # Local import prevents circular dependency during module import
    from edison.core.rules import RulesEngine

    rules = RulesEngine.get_rules_for_role(rule_key)
    formatted: List[Dict[str, Any]] = []
    for rule in rules:
        entry = dict(rule)
        entry["name"] = rule.get("title") or rule.get("name") or rule.get("id", "")
        entry["content"] = rule.get("content") or rule.get("guidance") or ""
        formatted.append(entry)
    return formatted


def load_constitution_layer(base_path: Path, role: str, layer_type: str) -> str:
    """Load constitution content from a specific layer."""
    normalized = _normalize_role(role)
    slug = ROLE_MAP[normalized]["slug"]

    if layer_type == "core":
        filename = f"{slug}-base.md"
    elif layer_type == "pack":
        filename = f"{slug}-additions.md"
    elif layer_type == "project":
        # Project overrides are canonical; allow additions as a secondary option.
        preferred = base_path / "constitutions" / f"{slug}-overrides.md"
        additions = base_path / "constitutions" / f"{slug}-additions.md"
        if preferred.exists():
            return preferred.read_text(encoding="utf-8")
        if additions.exists():
            return additions.read_text(encoding="utf-8")
        return ""
    else:
        raise ValueError(f"Unknown layer_type: {layer_type}")

    file_path = base_path / "constitutions" / filename
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return ""


def compose_constitution(role: str, config: ConfigManager) -> str:
    """Compose a constitution from core + packs + project layers."""
    normalized = _normalize_role(role)
    cfg_dict = config.load_config(validate=False)
    repo_root = config.repo_root

    layers: List[str] = []
    source_layers: List[str] = []

    # Core layer
    core_path = _core_base_path(repo_root)
    core_content = load_constitution_layer(core_path, normalized, "core")
    if core_content:
        layers.append(core_content)
        source_layers.append("core")

    # Packs (in configured order)
    packs_root = _packs_root(repo_root, cfg_dict)
    for pack in _active_packs(repo_root):
        pack_content = load_constitution_layer(packs_root / pack, normalized, "pack")
        if pack_content:
            layers.append(pack_content)
            source_layers.append(f"pack({pack})")

    # Project overrides
    project_dir = _project_constitutions_dir(repo_root)
    project_content = load_constitution_layer(project_dir.parent, normalized, "project")
    if project_content:
        layers.append(project_content)
        source_layers.append("project")

    composed = "\n\n".join([layer.strip() for layer in layers if layer])

    return render_constitution_template(
        composed,
        normalized,
        config,
        source_layers,
    )


def render_constitution_template(
    template: str,
    role: str,
    config: ConfigManager,
    source_layers: List[str],
) -> str:
    """Render Handlebars-style placeholders in constitution template."""
    normalized = _normalize_role(role)
    role_cfg_key = ROLE_MAP[normalized]["mandatory"]
    rule_role = ROLE_MAP[normalized]["rules"]
    template_name = f"constitutions/{ROLE_MAP[normalized]['slug']}-base.md"
    full_config = config.load_config(validate=False)
    version = resolve_version(config, full_config)
    generated_iso = utc_timestamp()

    # Load constitution config with project overlay precedence
    core_cfg = config.load_yaml(config.core_config_dir / "constitution.yaml")
    project_cfg_path = config.project_config_dir.parent / "constitution.yml"
    project_cfg = config.load_yaml(project_cfg_path) if project_cfg_path.exists() else {}

    constitution_cfg = config.deep_merge(core_cfg, project_cfg) if project_cfg else core_cfg
    mandatory_reads = constitution_cfg.get("mandatoryReads", {}).get(role_cfg_key, [])

    # Render mandatory reads
    reads_section = "\n".join(
        f"- {item.get('path')}: {item.get('purpose')}"
        for item in mandatory_reads
        if isinstance(item, dict)
    )

    # Render rules
    rules = get_rules_for_role(rule_role)
    rules_section = "\n\n".join(
        (
            f"### {r.get('id')}: {r.get('name')}\n{(r.get('content') or '').rstrip()}"
        ).strip()
        for r in rules
    )

    # Delegation rules (optional)
    delegation_rules = constitution_cfg.get("delegationRules", [])
    delegation_section = "\n".join(
        f"- {d.get('pattern')}: {d.get('agent')} ({d.get('model')})"
        for d in delegation_rules
        if isinstance(d, dict)
    )

    rendered = template
    rendered = rendered.replace("{{source_layers}}", " + ".join(source_layers))
    rendered = rendered.replace("{{generated_date}}", generated_iso)
    rendered = rendered.replace("{{timestamp}}", generated_iso)
    rendered = rendered.replace("{{version}}", str(version))
    rendered = rendered.replace("{{template_name}}", template_name)
    rendered = _replace_each_block(
        rendered,
        f"mandatoryReads.{role_cfg_key}",
        reads_section,
    )
    rendered = _replace_each_block(
        rendered,
        f"rules.{rule_role}",
        rules_section,
    )
    rendered = _replace_each_block(
        rendered,
        "delegationRules",
        delegation_section,
    )

    # Strip any unmatched closing tags for cleanliness
    rendered = rendered.replace("{{/each}}", "")
    return rendered


def generate_all_constitutions(config: ConfigManager, output_path: Path) -> None:
    """Generate all three constitution files."""
    out_dir = (Path(output_path) / "constitutions").resolve()
    ensure_directory(out_dir)

    for role, filename in [
        ("orchestrator", "ORCHESTRATORS.md"),
        ("agents", "AGENTS.md"),
        ("validators", "VALIDATORS.md"),
    ]:
        content = compose_constitution(role, config)
        out_path = out_dir / filename
        rendered = resolve_project_dir_placeholders(
            content,
            project_dir=config.project_config_dir.parent,
            target_path=out_path,
            repo_root=config.repo_root,
        )
        out_path.write_text(rendered, encoding="utf-8")


__all__ = [
    "get_rules_for_role",
    "load_constitution_layer",
    "compose_constitution",
    "render_constitution_template",
    "generate_all_constitutions",
]
