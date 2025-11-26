#!/usr/bin/env python3
from __future__ import annotations
"""Composition engine for coordinating all composition operations."""
from pathlib import Path
from typing import Dict, List, Optional
from .base import ComposeResult
from .prompt import compose_prompt
from ..includes import ComposeError, resolve_includes, _repo_root
from ..packs import auto_activate_packs
from ..formatting import compose_zen_prompts as formatting_compose_zen_prompts
from ..path_utils import resolve_project_dir_placeholders
from ..orchestrator import collect_validators
from ...file_io.utils import ensure_dir

class CompositionEngine:
    """High-level engine that wraps functional API and adds Zen composition."""

    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None) -> None:
        from ...config import ConfigManager
        from ..unified import UnifiedPathResolver
        self.repo_root = repo_root or _repo_root()
        global _REPO_ROOT_OVERRIDE
        _REPO_ROOT_OVERRIDE = self.repo_root
        from .. import includes as _includes
        _includes._REPO_ROOT_OVERRIDE = self.repo_root
        if config is None:
            cfg_mgr = ConfigManager(self.repo_root)
            self.config = cfg_mgr.load_config(validate=False)
        else:
            self.config = config
        path_resolver = UnifiedPathResolver(self.repo_root, "validators")
        self.core_dir = path_resolver.core_dir
        self.packs_dir = path_resolver.packs_dir
        self.project_dir = path_resolver.project_dir

    def _active_packs(self) -> List[str]:
        packs = ((self.config or {}).get("packs", {}) or {}).get("active", [])
        if not isinstance(packs, list):
            return []
        return packs

    def _pack_context_paths(self, packs: List[str], role: str) -> List[Path]:
        paths: List[Path] = []
        for name in packs:
            path = self.packs_dir / name / "validators" / "overlays" / f"{role}.md"
            if path.exists():
                paths.append(path)
        return paths

    def _overlay_path_for_role(self, role: str) -> Optional[Path]:
        overlay_cfg = ((self.config or {}).get("validators", {}) or {}).get("overlays", {}) or {}
        ov_rel = overlay_cfg.get(role)
        if isinstance(ov_rel, str) and ov_rel:
            rel_path = Path(ov_rel)
            if rel_path.is_absolute():
                return rel_path if rel_path.exists() else None
            path = (self.project_dir / rel_path).resolve()
            return path if path.exists() else None
        path = self.project_dir / "validators" / "overlays" / f"{role}.md"
        return path if path.exists() else None

    def resolve_includes(self, text: str, base_file: Path) -> str:
        expanded, _ = resolve_includes(text, base_file)
        return expanded

    def compose_validators(
        self,
        *,
        validator: str = "all",
        packs_override: Optional[List[str]] = None,
        enforce_dry: bool = True,
        changed_files: Optional[List[Path]] = None,
    ) -> Dict[str, ComposeResult]:
        def _validator_ids_from_config(active_packs: List[str]) -> List[str]:
            ids: List[str] = []
            roster = collect_validators(
                self.config,
                repo_root=self.repo_root,
                project_dir=self.project_dir,
                packs_dir=self.packs_dir,
                active_packs=active_packs,
            )
            for bucket in ("global", "critical", "specialized"):
                for item in roster.get(bucket) or []:
                    vid = None
                    if isinstance(item, str):
                        vid = item
                    elif isinstance(item, dict):
                        vid = item.get("id") or item.get("name")
                    if vid and vid not in ids:
                        ids.append(vid)
            return ids

        def _core_path_for_validator(v_id: str) -> Path:
            role = v_id.split("-", 1)[0]
            for subdir in ("global", "critical", "specialized"):
                path = self.core_dir / "validators" / subdir / f"{role}.md"
                if path.exists():
                    return path
            if self.packs_dir.exists():
                for pack_path in self.packs_dir.iterdir():
                    if pack_path.is_dir():
                        path = pack_path / "validators" / f"{role}.md"
                        if path.exists():
                            return path
            raise ComposeError(f"Validator spec not found: {role}.md")

        packs: List[str] = (
            list(packs_override)
            if packs_override is not None
            else list(self._active_packs())
        )
        if validator == "all":
            validators = _validator_ids_from_config(packs) or [
                "global-codex",
                "global-claude",
                "global-gemini",
                "security",
                "performance",
                "react",
                "nextjs",
                "api",
                "database",
                "testing",
            ]
        else:
            validators = [validator]
        if changed_files:
            try:
                auto = auto_activate_packs(
                    changed_files,
                    pack_root=self.packs_dir,
                    available_packs=packs,
                )
                if auto:
                    packs = sorted(auto)
            except Exception:
                pass
        critical_roles = {"security", "performance"}
        results: Dict[str, ComposeResult] = {}
        composed_roles: Dict[str, ComposeResult] = {}
        for v in validators:
            role = v.split("-", 1)[0]
            if role in composed_roles:
                results[v] = composed_roles[role]
                continue
            core_path = _core_path_for_validator(v)
            overlay = self._overlay_path_for_role(role)
            pack_paths = [] if role in critical_roles else self._pack_context_paths(packs, role)
            res = compose_prompt(
                validator_id=role,
                core_base=core_path,
                pack_contexts=pack_paths,
                overlay=overlay,
                enforce_dry=enforce_dry,
            )
            composed_roles[role] = res
            results[v] = res
        return results

    def compose_guidelines(
        self,
        *,
        packs_override: Optional[List[str]] = None,
        names: Optional[List[str]] = None,
        project_overrides: bool = True,
        dry_min_shingles: Optional[int] = None,
    ) -> Dict[str, Path]:
        from ..guidelines import GuidelineRegistry
        registry = GuidelineRegistry(repo_root=self.repo_root)
        packs: List[str] = (
            list(packs_override)
            if packs_override is not None
            else list(self._active_packs())
        )
        if names is not None:
            guideline_names: List[str] = list(names)
        else:
            guideline_names = registry.all_names(packs, include_project=True)
        if not guideline_names:
            return {}
        out_dir = self.project_dir / "_generated" / "guidelines"
        ensure_dir(out_dir)
        results: Dict[str, Path] = {}
        for name in sorted(set(guideline_names)):
            try:
                result = registry.compose(
                    name,
                    packs,
                    project_overrides=project_overrides,
                    dry_min_shingles=dry_min_shingles,
                )
            except ComposeError:
                continue
            subfolder = registry.get_subfolder(name, packs)
            if subfolder:
                guideline_out_dir = out_dir / subfolder
                ensure_dir(guideline_out_dir)
                out_file = guideline_out_dir / f"{name}.md"
            else:
                out_file = out_dir / f"{name}.md"
            rendered = resolve_project_dir_placeholders(
                result.text,
                project_dir=self.project_dir,
                target_path=out_file,
                repo_root=self.repo_root,
            )
            out_file.write_text(rendered, encoding="utf-8")
            results[name] = out_file
        return results

    def compose_zen_prompts(self, output_dir: str | Path) -> Dict[str, Path]:
        return formatting_compose_zen_prompts(self, output_dir)

    def compose_commands(self, platforms: Optional[List[str]] = None) -> Dict[str, Dict[str, Path]]:
        from ..commands import compose_commands as _compose_commands
        enabled = (self.config.get("commands") or {}).get("platforms", []) if self.config else []
        target_platforms = platforms or enabled or None
        return _compose_commands(self.config, target_platforms, repo_root=self.repo_root)

_REPO_ROOT_OVERRIDE = None

__all__ = ["CompositionEngine"]
