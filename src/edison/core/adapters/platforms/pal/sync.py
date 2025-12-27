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

class PalSyncMixin:
    """Mixin for syncing Pal prompts."""

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
        """Sync composed prompts for one or more roles (shared across CLI clients).

        Edison writes a single prompt file per role under the Pal project prompts directory:
        - Builtin roles: `<role>.txt` (e.g. `default.txt`, `planner.txt`)

        Args:
            model: Base model identifier used for composing shared content (codex/claude/gemini).
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
        for role in roles:
            role_key = _canonical_role(role)
            target = prompts_dir / f"{role_key}.txt"
            text = self.compose_pal_prompt(role=role, model=model_key, packs=packs)
            self.writer.write_text(target, text)
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
        """
        # AdaptersConfig was removed; adapter paths are now driven by CompositionConfig.adapters.
        from edison.core.config.domains import CompositionConfig

        comp_cfg = CompositionConfig(repo_root=self.project_root)
        pal_adapter = next((a for a in comp_cfg.get_enabled_adapters() if a.name == "pal"), None)
        if pal_adapter is None:
            return {"ok": True, "models": [], "roles": [], "missing": []}

        pal_conf_dir = comp_cfg.resolve_output_path(pal_adapter.output_path)
        cli_dir = pal_conf_dir / "cli_clients"
        report: Dict[str, Any] = {
            "ok": True,
            "models": [],
            "roles": [],
            "missing": [],
        }

        if not cli_dir.exists():
            # Nothing to verify; treat as success but keep report minimal.
            return report

        models: Set[str] = set()
        roles: Set[str] = set()
        role_to_paths: Dict[str, Set[Path]] = {}

        pal_cfg = self.config.get("pal") or {}
        cli_cfg = (pal_cfg.get("cli_clients") or {}) if isinstance(pal_cfg, dict) else {}
        roles_cfg = (cli_cfg.get("roles") or {}) if isinstance(cli_cfg, dict) else {}
        builtin_roles_cfg = roles_cfg.get("builtin") if isinstance(roles_cfg, dict) else None
        builtin_roles: Set[str] = set()
        if isinstance(builtin_roles_cfg, list):
            builtin_roles = {str(r).strip() for r in builtin_roles_cfg if str(r).strip()}

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
                prompt_rel = spec.get("prompt_path")
                if not isinstance(prompt_rel, str):
                    continue
                prompt_path = (cfg_path.parent / prompt_rel).resolve()
                roles.add(role_name)
                role_to_paths.setdefault(role_name, set()).add(prompt_path)

        report["models"] = sorted(models)
        report["roles"] = sorted(roles)

        # Optionally ensure builtin role prompts exist (agent/validator prompts are generated by sync_all).
        if sync and builtin_roles:
            # Use the configured base model when composing shared builtin prompts.
            base_model_raw = pal_cfg.get("prompt_base_model") if isinstance(pal_cfg, dict) else None
            if not isinstance(base_model_raw, str) or not base_model_raw.strip():
                raise ValueError("pal.prompt_base_model must be configured (non-empty string).")
            base_model = base_model_raw.strip()
            self.sync_role_prompts(model=base_model, roles=sorted(builtin_roles))

        missing: List[str] = []

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
        report["missing"] = missing
        report["ok"] = not missing
        return report


__all__ = ["PalSyncMixin"]
