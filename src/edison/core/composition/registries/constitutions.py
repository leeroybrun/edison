"""Constitution registry (unified composition).

Builds role constitutions (orchestrator, agents, validators) from layered
markdown using MarkdownCompositionStrategy via ComposableRegistry.
Role-specific data injection is performed in _post_compose.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from edison.core.entity.composable_registry import ComposableRegistry
from edison.core.utils.time import utc_timestamp
from edison.core.composition.output.headers import resolve_version
from edison.core.composition.path_utils import resolve_project_dir_placeholders
from edison.core.composition.registries.rules import get_rules_for_role


ROLE_MAP: Dict[str, Dict[str, str]] = {
    "orchestrator": {"slug": "orchestrator", "rules": "orchestrator", "mandatory": "orchestrator"},
    "agents": {"slug": "agents", "rules": "agent", "mandatory": "agents"},
    "validators": {"slug": "validators", "rules": "validator", "mandatory": "validators"},
}


def _normalize_role(role: str) -> str:
    key = (role or "").strip().lower()
    if key == "agent":
        return "agents"
    if key == "validator":
        return "validators"
    if key not in ROLE_MAP:
        raise ValueError(f"Invalid role: {role}")
    return key


@dataclass
class ConstitutionResult:
    role: str
    content: str
    source_layers: List[str]


class ConstitutionRegistry(ComposableRegistry[ConstitutionResult]):
    content_type: ClassVar[str] = "constitutions"
    file_pattern: ClassVar[str] = "*-base.md"
    strategy_config: ClassVar[Dict[str, Any]] = {
        "enable_sections": True,
        "enable_dedupe": False,
        "enable_template_processing": True,
    }

    def compose_constitution(self, role: str, packs: Optional[List[str]] = None) -> ConstitutionResult:
        role = _normalize_role(role)
        name = f"{ROLE_MAP[role]['slug']}-base"
        result = self.compose(name, packs)
        if result is None:
            raise FileNotFoundError(f"Constitution template for role '{role}' not found")
        return result

    def _post_compose(self, name: str, content: str) -> ConstitutionResult:
        role = _normalize_role(name.replace("-base", ""))

        cfg = self.config
        version = resolve_version(self.cfg_mgr, cfg)
        generated_iso = utc_timestamp()
        source_layers = ["core"] + [f"pack({p})" for p in self.get_active_packs()]

        role_cfg = cfg.get("constitutions", {}).get(ROLE_MAP[role]["mandatory"], {}) or {}
        mandatory_reads = role_cfg.get("mandatoryReads", []) if isinstance(role_cfg, dict) else []
        optional_reads = role_cfg.get("optionalReads", []) if isinstance(role_cfg, dict) else []

        def _render_reads(reads: List[Dict[str, Any]]) -> str:
            lines = []
            for item in reads or []:
                if isinstance(item, dict):
                    lines.append(f"- {item.get('path')}: {item.get('purpose')}")
            return "\n".join(lines)

        reads_section = _render_reads(mandatory_reads)
        optional_section = _render_reads(optional_reads)

        rules = get_rules_for_role(ROLE_MAP[role]["rules"])
        rules_section = "\n\n".join(
            (f"### {r.get('id')}: {r.get('name')}\n{(r.get('content') or '').rstrip()}").strip()
            for r in rules
        )

        rendered = content
        rendered = rendered.replace("{{source_layers}}", " + ".join(source_layers))
        rendered = rendered.replace("{{generated_date}}", generated_iso)
        rendered = rendered.replace("{{timestamp}}", generated_iso)
        rendered = rendered.replace("{{version}}", str(version))
        rendered = rendered.replace("{{template_name}}", f"constitutions/{ROLE_MAP[role]['slug']}-base.md")

        rendered = rendered.replace(f"{{{{#each mandatoryReads.{ROLE_MAP[role]['mandatory']}}}}}", reads_section)
        rendered = rendered.replace(f"{{{{#each optionalReads.{ROLE_MAP[role]['mandatory']}}}}}", optional_section)
        rendered = rendered.replace(f"{{{{#each rules.{ROLE_MAP[role]['rules']}}}}}", rules_section)
        rendered = rendered.replace("{{/each}}", "")

        target_path = self.project_dir / "_generated" / "constitutions" / f"{ROLE_MAP[role]['slug'].upper()}.md"
        rendered = resolve_project_dir_placeholders(
            rendered,
            project_dir=self.project_dir,
            target_path=target_path,
            repo_root=self.project_root,
        )

        return ConstitutionResult(role=role, content=rendered, source_layers=source_layers)


def generate_all_constitutions(config: Any, output_path: Path) -> None:
    out_dir = (Path(output_path) / "constitutions").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    registry = ConstitutionRegistry(project_root=config.repo_root)
    writer = registry.writer

    for role in ("orchestrator", "agents", "validators"):
        result = registry.compose_constitution(role, packs=registry.get_active_packs())
        outfile = out_dir / f"{ROLE_MAP[role]['slug'].upper()}.md"
        writer.write_text(outfile, result.content)


__all__ = ["ConstitutionRegistry", "ConstitutionResult", "generate_all_constitutions"]
