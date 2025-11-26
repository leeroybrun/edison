#!/usr/bin/env python3
from __future__ import annotations

"""Core composition routines for agents, validators, and guidelines."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from ..paths.project import get_project_config_dir
from ..utils.text import (
    ENGINE_VERSION,
    dry_duplicate_report,
    render_conditional_includes,
    _strip_headings_and_code,
    _tokenize,
    _shingles,
)
from .includes import (
    ComposeError,
    resolve_includes,
    _repo_root,
    _read_text,
    _hash_files,
    _write_cache,
    validate_composition,
    get_cache_dir,
    MAX_DEPTH,
    _REPO_ROOT_OVERRIDE,
)
from .packs import auto_activate_packs
from .formatting import compose_zen_prompts as formatting_compose_zen_prompts
from .orchestrator import (
    compose_orchestrator_manifest,
    collect_validators,
    count_agents,
    count_validators,
    compose_claude_orchestrator as orch_compose_claude_orchestrator,
    compose_claude_agents as orch_compose_claude_agents,
)


@dataclass
class ComposeResult:
    text: str
    dependencies: List[Path]
    cache_path: Optional[Path]
    hash: str
    duplicate_report: Optional[Dict]


def compose_prompt(
    *,
    validator_id: str,
    core_base: Path,
    pack_contexts: List[Path],
    overlay: Optional[Path],
    enforce_dry: bool = True,
    dry_min_shingles: Optional[int] = None,
) -> ComposeResult:
    """Compose a validator prompt from core + pack contexts + overlay."""
    root = _repo_root()
    if not core_base.exists():
        raise ComposeError(
            f"Core base not found for {validator_id}: {core_base.relative_to(root)}"
        )

    deps: List[Path] = [core_base.resolve()]
    core_raw = _read_text(core_base)
    core_expanded, core_deps = resolve_includes(core_raw, core_base)
    deps.extend([p for p in core_deps if p not in deps])

    pack_texts: List[str] = []
    for p in pack_contexts:
        if not p.exists():
            pack_texts.append(f"<!-- Missing pack context: {p.relative_to(root)} -->")
            continue
        raw = _read_text(p)
        expanded, p_deps = resolve_includes(raw, p)
        deps.append(p.resolve())
        for d in p_deps:
            if d not in deps:
                deps.append(d)
        pack_texts.append(expanded)

    packs_expanded = "\n\n".join([t for t in pack_texts if t])

    overlay_expanded = ""
    if overlay is not None and overlay.exists():
        raw = _read_text(overlay)
        overlay_expanded, o_deps = resolve_includes(raw, overlay)
        deps.append(overlay.resolve())
        for d in o_deps:
            if d not in deps:
                deps.append(d)
    elif overlay is not None:
        overlay_expanded = f"<!-- Missing overlay: {overlay.relative_to(root)} -->"

    # Check if core template has {{PACK_CONTEXT}} placeholder
    if "{{PACK_CONTEXT}}" in core_expanded:
        # New approach: Template substitution
        # Wrap pack context in section header if content exists
        pack_section = ""
        if packs_expanded:
            pack_section = f"\n\n# Tech-Stack Context (Packs)\n\n{packs_expanded}"

        # Wrap overlay in section header if content exists
        overlay_section = ""
        if overlay_expanded:
            overlay_section = f"\n\n# Project-Specific Rules\n\n{overlay_expanded}"

        # Substitute pack context into template
        final = core_expanded.replace("{{PACK_CONTEXT}}", pack_section + overlay_section)
    else:
        # Legacy approach: String concatenation (for validators without placeholder)
        sections = [
            "# Core Edison Principles",
            core_expanded,
            "\n# Tech-Stack Context (Packs)",
            packs_expanded,
            "\n# Project-Specific Rules",
            overlay_expanded,
        ]
        final = "\n\n".join([s for s in sections if s is not None])

    active_packs: Set[str] = set()
    for p in pack_contexts:
        try:
            pack_name = p.parent.parent.name
            if pack_name:
                active_packs.add(pack_name)
        except Exception:
            continue
    if active_packs:
        final = render_conditional_includes(final, active_packs)

    # Resolve any include directives introduced by conditional rendering.
    final, final_deps = resolve_includes(final, core_base)
    for d in final_deps:
        if d not in deps:
            deps.append(d)

    duplicate_report = None
    if enforce_dry:
        import os as _os

        min_s = (
            int(_os.environ.get("EDISON_DRY_MIN_SHINGLES", "2"))
            if dry_min_shingles is None
            else dry_min_shingles
        )
        duplicate_report = dry_duplicate_report(
            {"core": core_expanded, "packs": packs_expanded, "overlay": overlay_expanded},
            min_shingles=min_s,
            k=12,
        )
        try:
            import json as _json

            dr_dir = get_cache_dir() / "duplication-reports"
            dr_dir.mkdir(parents=True, exist_ok=True)
            (dr_dir / f"{validator_id}.json").write_text(
                _json.dumps(duplicate_report, indent=2), encoding="utf-8"
            )
        except Exception:
            pass
        if duplicate_report.get("violations"):
            raise ComposeError(
                "DRY violation: duplicate content detected across layers (see report)."
            )

    content_hash = _hash_files(deps, extra=validator_id)
    out_path = _write_cache(validator_id, final, deps, content_hash)
    try:
        validate_composition(final)
    except ComposeError as e:
        raise ComposeError(f"Validation failed for {validator_id}: {e}")
    return ComposeResult(
        text=final,
        dependencies=deps,
        cache_path=out_path,
        hash=content_hash,
        duplicate_report=duplicate_report,
    )


class CompositionEngine:
    """High-level engine that wraps functional API and adds Zen composition."""

    def __init__(self, config: Optional[Dict] = None, repo_root: Optional[Path] = None) -> None:
        from ..config import ConfigManager  # local import to avoid cycles at import time

        self.repo_root = repo_root or _repo_root()
        # Ensure all composition helpers resolve paths relative to this engine's repo.
        global _REPO_ROOT_OVERRIDE
        _REPO_ROOT_OVERRIDE = self.repo_root
        # Keep the source of truth inside the includes module as well.
        from . import includes as _includes  # local import to avoid cycles

        _includes._REPO_ROOT_OVERRIDE = self.repo_root
        if config is None:
            cfg_mgr = ConfigManager(self.repo_root)
            self.config = cfg_mgr.load_config(validate=False)
        else:
            self.config = config

        # For Edison's own tests, use bundled data directory instead of .edison/core
        edison_dir = self.repo_root / ".edison"
        if edison_dir.exists():
            self.core_dir = edison_dir / "core"
            self.packs_dir = edison_dir / "packs"
        else:
            # Running within Edison itself - use bundled data
            from edison.data import get_data_path
            self.core_dir = get_data_path("")
            self.packs_dir = get_data_path("packs")

        self.project_dir = get_project_config_dir(self.repo_root)

    def _active_packs(self) -> List[str]:
        packs = ((self.config or {}).get("packs", {}) or {}).get("active", [])
        if not isinstance(packs, list):
            return []
        return packs

    def _pack_context_paths(self, packs: List[str], role: str) -> List[Path]:
        paths: List[Path] = []
        for name in packs:
            base = self.packs_dir / name / "validators"
            preferred = base / f"{role}-context.md"
            fallback = base / "codex-context.md"
            paths.append(preferred if preferred.exists() else fallback)
        return paths

    def _overlay_path_for_role(self, role: str) -> Optional[Path]:
        overlay_cfg = ((self.config or {}).get("validators", {}) or {}).get("overlays", {}) or {}
        ov_rel = overlay_cfg.get(role)
        if isinstance(ov_rel, str) and ov_rel:
            rel_path = Path(ov_rel)
            candidates = []
            if rel_path.is_absolute():
                candidates.append(rel_path)
            else:
                candidates.append((self.project_dir / rel_path).resolve())
                candidates.append((self.repo_root / rel_path).resolve())

            for candidate in candidates:
                if candidate.exists():
                    return candidate

            # Return the first candidate even when missing so compose emits a helpful marker
            return candidates[0] if candidates else rel_path
        candidates = [
            self.project_dir / "validators" / "overlays" / f"{role}-overlay.md",
            self.project_dir / "validators" / "overlays" / f"{role}-global-overlay.md",
        ]
        for c in candidates:
            if c.exists():
                return c
        return None

    def resolve_includes(self, text: str, base_file: Path) -> str:
        expanded, _ = resolve_includes(text, base_file)
        return expanded

    def compose_claude_orchestrator(self, output_dir: Path | str) -> Path:
        return orch_compose_claude_orchestrator(self, output_dir)

    def compose_claude_agents(
        self,
        output_dir: Path | str | None = None,
        *,
        packs_override: Optional[List[str]] = None,
    ) -> Dict[str, Path]:
        return orch_compose_claude_agents(self, output_dir, packs_override=packs_override)

    def compose_agents(
        self,
        output_dir: Path | str | None = None,
        *,
        packs_override: Optional[List[str]] = None,
    ) -> Dict[str, Path]:
        """Alias for compose_claude_agents for backward compatibility."""
        return self.compose_claude_agents(output_dir, packs_override=packs_override)

    def compose_validators(
        self,
        *,
        validator: str = "all",
        packs_override: Optional[List[str]] = None,
        enforce_dry: bool = True,
        changed_files: Optional[List[Path]] = None,
    ) -> Dict[str, ComposeResult]:
        def _validator_ids_from_config(active_packs: List[str]) -> List[str]:
            """Collect validator ids using the same merged roster logic as the orchestrator.

            This pulls from both the core `validation.roster` and the project
            `validators.roster` overlay, ensuring compose coverage matches the
            orchestrator manifest (prevents missing pack/project validators
            like `styling`).
            """

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
            candidates = [
                self.core_dir / "validators" / "global" / f"{role}-core.md",
                self.core_dir / "validators" / "critical" / f"{role}.md",
                self.core_dir / "validators" / "specialized" / f"{role}.md",
                self.project_dir / "validators" / "specialized" / f"{role}.md",
            ]
            for c in candidates:
                if c.exists():
                    return c

            # Fallback: pack-provided validator specs (e.g., prisma/database)
            # Search all packs, not just active ones, to support validator composition
            # even when packs aren't explicitly activated
            if self.packs_dir.exists():
                # Try role name first, then common aliases
                role_aliases = [role]
                if role == "prisma":
                    role_aliases.append("database")

                for pack_path in self.packs_dir.iterdir():
                    if pack_path.is_dir():
                        for alias in role_aliases:
                            cand = pack_path / "validators" / f"{alias}.md"
                            if cand.exists():
                                return cand

            raise ComposeError(
                f"Validator spec not found for {v_id}. Looked for: "
                + ", ".join(str(c.relative_to(self.repo_root)) for c in candidates)
            )

        role_map = {
            "codex": "codex-global",
            "claude": "claude-global",
            "gemini": "gemini-global",
        }

        packs: List[str] = (
            list(packs_override)
            if packs_override is not None
            else list(self._active_packs())
        )

        if validator == "all":
            validators = _validator_ids_from_config(packs) or [
                "codex-global",
                "claude-global",
                "gemini-global",
                "security",
                "performance",
                "react",
                "nextjs",
                "api",
                "database",
                "testing",
            ]
        else:
            validators = [role_map.get(validator, validator)]

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
        for v in validators:
            role = v.split("-", 1)[0]
            core_path = _core_path_for_validator(v)
            overlay = self._overlay_path_for_role(role)
            pack_paths = [] if role in critical_roles else self._pack_context_paths(packs, role)

            res = compose_prompt(
                validator_id=v,
                core_base=core_path,
                pack_contexts=pack_paths,
                overlay=overlay,
                enforce_dry=enforce_dry,
            )
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
        from .guidelines import GuidelineRegistry

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
        out_dir.mkdir(parents=True, exist_ok=True)

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

            # Determine subfolder to preserve source structure
            subfolder = registry.get_subfolder(name, packs)
            if subfolder:
                guideline_out_dir = out_dir / subfolder
                guideline_out_dir.mkdir(parents=True, exist_ok=True)
                out_file = guideline_out_dir / f"{name}.md"
            else:
                out_file = out_dir / f"{name}.md"

            out_file.write_text(result.text, encoding="utf-8")
            results[name] = out_file

        return results

    def compose_zen_prompts(self, output_dir: str | Path) -> Dict[str, Path]:
        return formatting_compose_zen_prompts(self, output_dir)

    def compose_orchestrator_manifest(self, output_dir: Path) -> Dict[str, Path]:
        return compose_orchestrator_manifest(
            config=self.config,
            repo_root=self.repo_root,
            core_dir=self.core_dir,
            packs_dir=self.packs_dir,
            project_dir=self.project_dir,
            active_packs=self._active_packs(),
            output_dir=output_dir,
        )

    def compose_commands(self, platforms: Optional[List[str]] = None) -> Dict[str, Dict[str, Path]]:
        """Compose slash commands for the given platforms (or configured defaults)."""
        from .commands import compose_commands as _compose_commands

        enabled = (self.config.get("commands") or {}).get("platforms", []) if self.config else []
        target_platforms = platforms or enabled or None
        return _compose_commands(self.config, target_platforms, repo_root=self.repo_root)


def compose_guidelines(
    active_packs: Iterable[str],
    project_config: Optional[Dict] = None,
    *,
    repo_root: Optional[Path] = None,
    names: Optional[Iterable[str]] = None,
    project_overrides: bool = True,
    dry_min_shingles: Optional[int] = None,
) -> Dict[str, Path]:
    engine = CompositionEngine(
        project_config or {},
        repo_root=repo_root,
    )
    return engine.compose_guidelines(
        packs_override=list(active_packs),
        names=list(names) if names is not None else None,
        project_overrides=project_overrides,
        dry_min_shingles=dry_min_shingles,
    )


__all__ = [
    "ComposeError",
    "ComposeResult",
    "compose_prompt",
    "compose_guidelines",
    "resolve_includes",
    "render_conditional_includes",
    "auto_activate_packs",
    "validate_composition",
    "dry_duplicate_report",
    "ENGINE_VERSION",
    "MAX_DEPTH",
    "CompositionEngine",
    "get_cache_dir",
    "_strip_headings_and_code",
    "_tokenize",
    "_shingles",
    "_repo_root",
]
