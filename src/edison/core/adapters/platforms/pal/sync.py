"""Pal sync mixin for prompt synchronization.

This module provides PalSyncMixin which handles syncing
Pal prompts to the appropriate directories.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, TYPE_CHECKING

from edison.core.utils.io import read_json, ensure_directory
from .composer import _canonical_model
from .discovery import _canonical_role

if TYPE_CHECKING:
    from .adapter import PalAdapter

WORKFLOW_HEADING = "## Edison Workflow Loop"


class PalSyncMixin:
    """Mixin for syncing Pal prompts."""

    def _workflow_template(self: PalAdapter) -> Optional[str]:
        """Get workflow loop template text."""
        pal_cfg = self.config.get("pal") or {}
        template_cfg = (pal_cfg.get("templates") or {}) if isinstance(pal_cfg, dict) else {}
        configured = None
        if isinstance(template_cfg, dict):
            configured = template_cfg.get("workflow_loop")

        candidates: List[Path] = []
        if isinstance(configured, str) and configured.strip():
            raw_path = Path(configured.strip())
            if raw_path.is_absolute():
                candidates.append(raw_path)
            else:
                # Allow project overrides (relative to repo root) and core-bundled templates.
                candidates.append(self.project_root / raw_path)
                candidates.append(self.core_dir / raw_path)

        # Core default (kept as a file, not a hardcoded string).
        candidates.append(self.core_dir / "templates" / "pal" / "workflow-loop.txt")

        for path in candidates:
            if path.exists():
                return path.read_text(encoding="utf-8")
        return None

    @staticmethod
    def _split_workflow_section(content: str) -> tuple[str, Optional[str]]:
        """Split content into (body, workflow_section)."""
        idx = content.find(WORKFLOW_HEADING)
        if idx == -1:
            return content, None
        body = content[:idx].rstrip()
        workflow = content[idx:]
        return body, workflow

    def _attach_workflow_loop(self: PalAdapter, core_text: str, existing_file: Optional[Path]) -> str:
        """Attach or preserve workflow loop section when syncing prompts."""
        existing_loop: Optional[str] = None
        if existing_file is not None and existing_file.exists():
            _, existing_loop = self._split_workflow_section(
                existing_file.read_text(encoding="utf-8")
            )

        loop_text = existing_loop or self._workflow_template()
        if not loop_text:
            # No workflow template available; return core text as-is.
            return core_text

        if WORKFLOW_HEADING in core_text:
            # Already attached; avoid duplication.
            return core_text

        return core_text.rstrip() + "\n\n" + loop_text.rstrip() + "\n"

    def _pal_prompts_dir(self: PalAdapter) -> Path:
        """Get Pal prompts directory path."""
        # Prefer the configured sync destination (agents/prompts) so all prompt
        # artifacts land in a single coherent directory.
        dest = self.get_sync_destination("agents") or self.get_sync_destination("prompts")
        if dest is None:
            dest = self.get_output_path() / "systemprompts" / "clink" / "project"
        ensure_directory(dest)
        return dest

    def sync_role_prompts(self: PalAdapter, model: str, roles: List[str]) -> Dict[str, Path]:
        """Sync composed prompts for a model across one or more logical roles.

        Each role gets its own file under the Pal system prompts directory:
        - Generic roles: `<model>_<role>.txt` (e.g. `codex_default.txt`)
        - Project roles: `<model>_<project-role>.txt` (e.g. `codex_project-api-builder.txt`)

        Args:
            model: Model identifier (codex/claude/gemini)
            roles: List of role identifiers

        Returns:
            Dict mapping role names to written file paths
        """
        model_key = _canonical_model(model)
        if not roles:
            roles = ["default"]

        packs = self.get_active_packs()
        prompts_dir = self._pal_prompts_dir()

        results: Dict[str, Path] = {}

        generic_roles: List[str] = []
        project_roles: List[str] = []
        for role in roles:
            if role.lower().startswith("project-"):
                project_roles.append(role)
            else:
                generic_roles.append(role)

        # Generic roles: one file per (model, role)
        for role in generic_roles:
            role_key = _canonical_role(role)
            target = prompts_dir / f"{model_key}_{role_key}.txt"
            text = self.compose_pal_prompt(role=role, model=model_key, packs=packs)
            final_text = self._attach_workflow_loop(text, target if target.exists() else None)
            self.writer.write_text(target, final_text)
            results[role] = target

        # Project roles: one file per (model, role)
        for role in project_roles:
            target = prompts_dir / f"{model_key}_{role}.txt"
            text = self.compose_pal_prompt(role=role, model=model_key, packs=packs)
            final_text = self._attach_workflow_loop(text, target if target.exists() else None)
            self.writer.write_text(target, final_text)
            results[role] = target

        return results

    def verify_cli_prompts(self: PalAdapter, sync: bool = True) -> Dict[str, Any]:
        """Verify that all Pal MCP CLI client roles have prompt files.

        When ``sync`` is True (default), this method first syncs prompts
        for all project-specific roles discovered in CLI client configs
        before performing verification.

        Args:
            sync: If True, sync prompts before verification

        Returns:
            Report dictionary with keys:
              - ok (bool): True when no problems were found
              - models (list[str]): Models discovered from CLI configs
              - roles (list[str]): project roles discovered from CLI configs
              - missing (list[str]): Human-readable entries for missing files
              - missingWorkflow (list[str]): Entries for files lacking workflow loop
        """
        # AdaptersConfig was removed; adapter paths are now driven by CompositionConfig.adapters.
        from edison.core.config.domains import CompositionConfig

        comp_cfg = CompositionConfig(repo_root=self.project_root)
        pal_adapter = next((a for a in comp_cfg.get_enabled_adapters() if a.name == "pal"), None)
        if pal_adapter is None:
            return {"ok": True, "models": [], "roles": [], "missing": [], "missingWorkflow": []}

        pal_conf_dir = comp_cfg.resolve_output_path(pal_adapter.output_path)
        cli_dir = pal_conf_dir / "cli_clients"
        report: Dict[str, Any] = {
            "ok": True,
            "models": [],
            "roles": [],
            "missing": [],
            "missingWorkflow": [],
        }

        if not cli_dir.exists():
            # Nothing to verify; treat as success but keep report minimal.
            return report

        models: Set[str] = set()
        roles: Set[str] = set()
        role_to_paths: Dict[str, Set[Path]] = {}

        for cfg_path in sorted(cli_dir.glob("*.json")):
            data = read_json(cfg_path, default={})

            model_name = str(data.get("name") or cfg_path.stem)
            models.add(_canonical_model(model_name))

            raw_roles = data.get("roles") or {}
            if not isinstance(raw_roles, dict):
                continue

            for role_name, spec in raw_roles.items():
                if not isinstance(spec, dict):
                    continue
                # Only verify project-specific roles; generic prompts share model files.
                if not role_name.startswith("project-"):
                    continue
                prompt_rel = spec.get("prompt_path")
                if not isinstance(prompt_rel, str):
                    continue
                prompt_path = (cfg_path.parent / prompt_rel).resolve()
                roles.add(role_name)
                role_to_paths.setdefault(role_name, set()).add(prompt_path)

        report["models"] = sorted(models)
        report["roles"] = sorted(roles)

        # Optionally sync prompts for all discovered roles first.
        if sync and roles:
            for model in sorted(models):
                self.sync_role_prompts(model=model, roles=sorted(roles))

        missing: List[str] = []
        missing_workflow: List[str] = []

        for role_name, paths in role_to_paths.items():
            for path in paths:
                if not path.exists():
                    missing.append(f"{role_name} → {path}")
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except Exception:
                    missing.append(f"{role_name} → {path}")
                    continue
                if WORKFLOW_HEADING not in text:
                    missing_workflow.append(f"{role_name} → {path}")

        report["missing"] = missing
        report["missingWorkflow"] = missing_workflow
        report["ok"] = not missing and not missing_workflow
        return report


__all__ = ["PalSyncMixin", "WORKFLOW_HEADING"]
