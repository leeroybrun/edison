from __future__ import annotations

"""
Zen MCP prompt adapter (thin).

Projects Edison `_generated` orchestrator artifacts into Zen MCP
system prompt files under:

    .zen/conf/systemprompts/clink/<project>/*.txt

This adapter intentionally:
  - Reads only from `_generated` + existing workflow template
  - Does not re-run validator/guideline composition
"""

import json
from pathlib import Path
from typing import Any, Dict, List

from ..base import PromptAdapter


WORKFLOW_HEADING = "## Edison Workflow Loop"


class ZenPromptAdapter(PromptAdapter):
    """Adapter for generating Zen MCP system prompts from `_generated`."""

    def __init__(self, generated_root: Path, repo_root: Optional[Path] = None) -> None:
        super().__init__(generated_root, repo_root=repo_root)
        self._manifest: Dict[str, Any] = {}
        self.project_config_dir_name = self.generated_root.parent.name

    # ----- Internal helpers -----
    def _load_manifest(self) -> Dict[str, Any]:
        if self._manifest:
            return self._manifest
        path = self.orchestrator_manifest_path
        if not path.exists():
            self._manifest = {}
            return self._manifest
        try:
            self._manifest = json.loads(path.read_text(encoding="utf-8") or "{}")
        except Exception:
            self._manifest = {}
        return self._manifest

    def _workflow_loop_block(self) -> str:
        """Return shared workflow loop block for all Zen prompts."""
        template = self.repo_root / ".zen" / "templates" / "workflow-loop.txt"
        if template.exists():
            return template.read_text(encoding="utf-8").strip()
        # Fallback minimal block that still satisfies WORKFLOW_HEADING checks.
        return "\n".join(
            [
                "## Edison Workflow Loop (CRITICAL)",
                "",
                "scripts/session next <session-id>",
            ]
        )

    # ----- PromptAdapter API -----
    def render_orchestrator(self, guide_path: Path, manifest_path: Path) -> str:
        guide = guide_path.read_text(encoding="utf-8").strip()
        lines = [
            "=== Edison / Zen MCP Orchestrator ===",
            f"Source: {guide_path.relative_to(self.repo_root)}",
            f"Manifest: {manifest_path.relative_to(self.repo_root)}",
            "",
            guide,
        ]
        return "\n".join(lines).rstrip() + "\n"

    def render_agent(self, agent_name: str) -> str:
        """Render a role-specific Zen MCP prompt."""
        manifest = self._load_manifest()
        delegation = manifest.get("delegation") or {}
        priority = delegation.get("priority") or {}
        role_mapping = delegation.get("roleMapping") or {}

        # Determine generic role for diagnostics (if any).
        generic_for_concrete = None
        for generic, concrete in role_mapping.items():
            if concrete == agent_name:
                generic_for_concrete = generic
                break

        workflow_block = self._workflow_loop_block()

        lines: List[str] = [
            "=== Edison / Zen MCP Prompt ===",
            f"Role: {agent_name}",
            "",
            f"Orchestrator manifest: {self.project_config_dir_name}/_generated/orchestrator-manifest.json",
            f"Orchestrator constitution: {self.project_config_dir_name}/_generated/constitutions/ORCHESTRATORS.md",
        ]

        if generic_for_concrete:
            lines.append(f"Generic role: {generic_for_concrete}")

        # Include delegation priority chains when relevant so the prompt
        # stands alone for CLI clients.
        impl_chain = ", ".join(priority.get("implementers", []))
        val_chain = ", ".join(priority.get("validators", []))
        if impl_chain or val_chain:
            lines.append("")
            lines.append("## Delegation Priority (from manifest)")
            if impl_chain:
                lines.append(f"- Implementers: {impl_chain}")
            if val_chain:
                lines.append(f"- Validators: {val_chain}")

        lines.append("")
        lines.append(workflow_block)

        return "\n".join(lines).rstrip() + "\n"

    def render_validator(self, validator_name: str) -> str:
        """Render validators as standalone Zen prompts when needed."""
        manifest = self._load_manifest()
        validators = manifest.get("validators") or {}
        all_specs: List[Dict[str, Any]] = []
        for bucket in ("global", "critical", "specialized"):
            all_specs.extend(validators.get(bucket, []) or [])

        meta = next(
            (v for v in all_specs if v.get("id") == validator_name),
            None,
        )

        lines: List[str] = [
            "=== Edison / Zen MCP Validator Prompt ===",
            f"Validator id: {validator_name}",
            "",
            f"Orchestrator manifest: {self.project_config_dir_name}/_generated/orchestrator-manifest.json",
        ]

        if meta:
            lines.append(f"Model: {meta.get('model', '')}")
            lines.append(f"Scope: {meta.get('scope', '')}")
            if meta.get("triggers"):
                lines.append(f"Triggers: {', '.join(meta['triggers'])}")

        lines.append("")
        lines.append(self._workflow_loop_block())

        return "\n".join(lines).rstrip() + "\n"

    def write_outputs(self, output_root: Path) -> None:
        """Write role-specific prompts into the Zen MCP prompt directory."""
        output_root.mkdir(parents=True, exist_ok=True)

        manifest = self._load_manifest()
        if not manifest:
            # Nothing to project; keep behavior graceful for partially
            # configured projects.
            return

        delegation = manifest.get("delegation") or {}
        role_mapping = delegation.get("roleMapping") or {}
        priority = delegation.get("priority") or {}

        generic_roles: List[str] = []
        generic_roles.extend(priority.get("implementers", []) or [])
        generic_roles.extend(priority.get("validators", []) or [])
        # Ensure we include any generic roles that only appear in roleMapping.
        for key in role_mapping.keys():
            if key not in generic_roles:
                generic_roles.append(key)

        concrete_roles = sorted(
            role_mapping.get(r, r) for r in generic_roles if isinstance(r, str)
        )

        for role_name in concrete_roles:
            text = self.render_agent(role_name)
            (output_root / f"{role_name}.txt").write_text(text, encoding="utf-8")


__all__ = ["ZenPromptAdapter", "WORKFLOW_HEADING"]
