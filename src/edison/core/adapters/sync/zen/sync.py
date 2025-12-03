from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple, TYPE_CHECKING

from edison.core.utils.io import read_json, ensure_directory
from .composer import _canonical_model
from .discovery import _canonical_role

if TYPE_CHECKING:
    from .client import ZenSync

WORKFLOW_HEADING = "## Edison Workflow Loop"


class ZenSyncMixin:
    def _workflow_template(self: ZenSync) -> Optional[str]:
        from edison.core.config.domains import AdaptersConfig
        adapters_cfg = AdaptersConfig(repo_root=self.repo_root)
        template_path = adapters_cfg.get_template_path("zen", "workflow-loop.txt")
        if template_path.exists():
            return template_path.read_text(encoding="utf-8")
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

    def _attach_workflow_loop(self: ZenSync, core_text: str, existing_file: Optional[Path]) -> str:
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

    def _zen_prompts_dir(self: ZenSync) -> Path:
        from edison.core.config.domains import AdaptersConfig
        adapters_cfg = AdaptersConfig(repo_root=self.repo_root)
        sync_path = adapters_cfg.get_sync_path("zen", "prompts_path")
        if not sync_path:
            raise ValueError(
                "Zen prompts_path not configured in composition.yaml outputs.sync.zen. "
                "This path is required for Zen prompt sync."
            )
        out_dir = sync_path / "project"
        ensure_directory(out_dir)
        return out_dir

    def sync_role_prompts(self: ZenSync, model: str, roles: List[str]) -> Dict[str, Path]:
        """Sync composed prompts for a model across one or more logical roles.

        Generic roles (default / codereviewer / planner) are combined into
        the model-level file `<model>.txt`. project-specific roles
        (`project-*`) are written to individual files matching the Zen role
        name (e.g. `project-api-builder.txt`).
        """
        model_key = _canonical_model(model)
        if not roles:
            roles = ["default"]

        packs = self._active_packs()
        prompts_dir = self._zen_prompts_dir()

        results: Dict[str, Path] = {}

        generic_roles: List[str] = []
        project_roles: List[str] = []
        for role in roles:
            if role.lower().startswith("project-"):
                project_roles.append(role)
            else:
                generic_roles.append(role)

        # Generic roles share a single file per model
        if generic_roles:
            sections: List[str] = []
            for role in generic_roles:
                sections.append(self.compose_zen_prompt(role=role, model=model_key, packs=packs))
            combined = "\n\n".join(sections)
            target = prompts_dir / f"{model_key}.txt"
            final_text = self._attach_workflow_loop(combined, target if target.exists() else None)
            self.writer.write_text(target, final_text)
            for role in generic_roles:
                results[role] = target

        # project roles each get their own file
        for role in project_roles:
            target = prompts_dir / f"{role}.txt"
            text = self.compose_zen_prompt(role=role, model=model_key, packs=packs)
            final_text = self._attach_workflow_loop(text, target if target.exists() else None)
            self.writer.write_text(target, final_text)
            results[role] = target

        return results

    def verify_cli_prompts(self: ZenSync, sync: bool = True) -> Dict[str, Any]:
        """
        Verify that all Zen MCP CLI client roles have prompt files.

        When ``sync`` is True (default), this method first syncs prompts
        for all project-specific roles discovered in CLI client configs
        before performing verification.

        Returns a report dictionary with the following keys:
          - ``ok`` (bool): True when no problems were found.
          - ``models`` (list[str]): Models discovered from CLI configs.
          - ``roles`` (list[str]): project roles discovered from CLI configs.
          - ``missing`` (list[str]): Human-readable entries for missing files.
          - ``missingWorkflow`` (list[str]): Entries for files lacking the
            Edison workflow loop section.
        """
        from edison.core.config.domains import AdaptersConfig
        adapters_cfg = AdaptersConfig(repo_root=self.repo_root)
        zen_dir = adapters_cfg.get_client_path("zen")
        cli_dir = zen_dir / "conf" / "cli_clients"
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
