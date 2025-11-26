#!/usr/bin/env python3
from __future__ import annotations
"""Prompt composition for validators."""
from pathlib import Path
from typing import List, Optional, Set
from .base import ComposeResult
from ..includes import (
    ComposeError,
    resolve_includes,
    _repo_root,
    _read_text,
    _hash_files,
    _write_cache,
    validate_composition,
    get_cache_dir,
)
from ...paths.project import get_project_config_dir
from ...file_io.utils import ensure_dir
from ...utils.text import dry_duplicate_report, render_conditional_includes

def _validator_constitution_header(repo_root: Path) -> tuple[str, Path]:
    """Return constitution header text and dependency path."""
    project_dir = get_project_config_dir(repo_root)
    constitution_path = project_dir / "_generated" / "constitutions" / "VALIDATORS.md"
    try:
        constitution_rel = constitution_path.relative_to(repo_root)
    except ValueError:
        constitution_rel = constitution_path
    path_str = constitution_rel.as_posix()
    header = f"""## MANDATORY: Read Constitution First

Before starting validation, you MUST read the Validator Constitution at:
`{path_str}`

This constitution contains:
- Your validation workflow
- Applicable rules for validation
- Output format requirements
- All mandatory guideline reads

**Re-read the constitution:**
- At the start of every validation task
- After any context compaction

---"""
    return header, constitution_path

def _inject_constitution(text: str, *, repo_root: Path) -> tuple[str, Path]:
    """Prepend validator constitution reference when missing."""
    header, constitution_path = _validator_constitution_header(repo_root)
    if text.lstrip().startswith("## MANDATORY: Read Constitution First"):
        return text, constitution_path
    return f"{header}\n\n{text}", constitution_path

def _dedupe_pack_contexts(paths: List[Path]) -> List[Path]:
    """Return paths with duplicate packs removed while preserving order.

    Path structure: packs/{pack_name}/validators/overlays/{role}.md
    To get pack_name: path.parent.parent.parent.name
    """
    seen: Set[str] = set()
    unique: List[Path] = []
    for path in paths:
        # Navigate up: overlays -> validators -> {pack_name}
        pack_dir = path.parent.parent.parent if path.parent and path.parent.parent else None
        pack_name = pack_dir.name if pack_dir else ""
        key = pack_name or str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return unique

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
    deduped_pack_contexts = _dedupe_pack_contexts(pack_contexts)
    deps: List[Path] = [core_base.resolve()]
    core_raw = _read_text(core_base)
    core_expanded, core_deps = resolve_includes(core_raw, core_base)
    deps.extend([p for p in core_deps if p not in deps])
    pack_texts: List[str] = []
    for p in deduped_pack_contexts:
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
    # Build pack content section
    pack_section = f"\n\n# Tech-Stack Context (Packs)\n\n{packs_expanded}" if packs_expanded else ""
    overlay_section = f"\n\n# Project-Specific Rules\n\n{overlay_expanded}" if overlay_expanded else ""
    combined_section = pack_section + overlay_section
    # Replace unified placeholder {{SECTION:TechStack}}
    if "{{SECTION:TechStack}}" in core_expanded:
        final = core_expanded.replace("{{SECTION:TechStack}}", combined_section)
    else:
        # No placeholder: String concatenation
        sections = [
            "# Core Edison Principles",
            core_expanded,
            combined_section,
        ]
        final = "\n\n".join([s for s in sections if s])
    active_packs: Set[str] = set()
    for p in deduped_pack_contexts:
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
    # Auto-inject constitution reference for all validators
    final, constitution_dep = _inject_constitution(final, repo_root=root)
    constitution_dep_resolved = constitution_dep.resolve()
    if constitution_dep_resolved not in deps:
        deps.append(constitution_dep_resolved)
    duplicate_report = None
    if enforce_dry:
        # Get DRY detection config from composition.yaml
        if dry_min_shingles is None:
            from ...config import ConfigManager
            cfg = ConfigManager().load_config(validate=False)
            dry_config = cfg.get("composition", {}).get("dryDetection", {})
            min_s = dry_config.get("minShingles", 2)
            k = dry_config.get("shingleSize", 12)
        else:
            min_s = dry_min_shingles
            # Use config for k as well
            from ...config import ConfigManager
            cfg = ConfigManager().load_config(validate=False)
            dry_config = cfg.get("composition", {}).get("dryDetection", {})
            k = dry_config.get("shingleSize", 12)
        duplicate_report = dry_duplicate_report(
            {"core": core_expanded, "packs": packs_expanded, "overlay": overlay_expanded},
            min_shingles=min_s,
            k=k,
        )
        try:
            import json as _json
            dr_dir = get_cache_dir() / "duplication-reports"
            ensure_dir(dr_dir)
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
__all__ = ["compose_prompt"]