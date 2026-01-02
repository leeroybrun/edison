"""Start prompt discovery and loading.

Start prompts are Markdown templates intended to bootstrap an LLM session.

Resolution order (fail-closed):
1. Project-composed prompts: `<project>/<project-config-dir>/_generated/start/START_*.md`
2. Bundled core prompts: `edison.data/start/START_*.md`
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

from edison.core.utils.paths.project import get_project_config_dir
from edison.data import get_data_path


def _candidate_prompt_dirs(project_root: Path) -> list[Path]:
    out: list[Path] = []

    try:
        proj_cfg = get_project_config_dir(project_root, create=False)
        gen = proj_cfg / "_generated" / "start"
        if gen.exists():
            out.append(gen)
    except Exception:
        pass

    try:
        bundled = Path(get_data_path("start"))
        if bundled.exists():
            out.append(bundled)
    except Exception:
        pass

    return out


def _normalize_prompt_id(raw: str) -> str:
    text = str(raw or "").strip()
    if not text:
        raise ValueError("Prompt id is required")
    upper = text.upper()
    if upper.startswith("START_"):
        return upper
    return f"START_{upper}"


def list_start_prompts(project_root: Path) -> List[str]:
    """List available start prompt IDs (without the START_ prefix)."""
    prompts: dict[str, str] = {}
    for d in _candidate_prompt_dirs(project_root):
        for p in sorted(d.glob("START_*.md")):
            stem = p.stem.upper()
            short = stem[len("START_") :] if stem.startswith("START_") else stem
            # Prefer earlier dirs (project-composed) over bundled
            prompts.setdefault(short, stem)
    return sorted(prompts.keys())


def read_start_prompt(project_root: Path, prompt_id: str) -> str:
    """Read a start prompt by id (accepts with/without START_ prefix).

    Start prompts are authored as Edison templates (includes, include-section,
    config vars, functions, etc.). In fully composed projects, prompts are
    materialized under `<project>/<project-config-dir>/_generated/start/`.

    However tests and new repos may not have those generated artifacts yet. To
    keep behavior consistent, always run the template engine at read-time.
    """
    path = find_start_prompt_path(project_root, prompt_id)
    raw = path.read_text(encoding="utf-8", errors="strict")
    return _render_start_prompt(project_root, raw, prompt_id=prompt_id)


def find_start_prompt_path(project_root: Path, prompt_id: str) -> Path:
    """Resolve the on-disk path for a start prompt by id.

    Returns the first matching path from the candidate dirs (project-composed
    takes precedence over bundled core).
    """
    want = _normalize_prompt_id(prompt_id)
    filename = f"{want}.md"

    for d in _candidate_prompt_dirs(project_root):
        path = d / filename
        if path.exists():
            return path

    available = list_start_prompts(project_root)
    if available:
        raise FileNotFoundError(
            f"Unknown start prompt '{prompt_id}'. Available: {', '.join(available)}"
        )
    raise FileNotFoundError(
        f"Unknown start prompt '{prompt_id}'. No start prompts found for project."
    )


__all__ = [
    "list_start_prompts",
    "find_start_prompt_path",
    "read_start_prompt",
]


def _render_start_prompt(project_root: Path, raw: str, *, prompt_id: str) -> str:
    """Render a START_* prompt through the TemplateEngine.

    This is intentionally side-effect free (no materialization).
    """
    # Load config (core + project overlays) and active packs so that:
    # - {{config.*}} resolves consistently with other composition surfaces
    # - {{fn:*}} loads any pack/project function overrides
    from edison.core.config import ConfigManager

    cfg_mgr = ConfigManager(repo_root=project_root)
    cfg = cfg_mgr.load_config(validate=False, include_packs=False)
    packs_section = cfg.get("packs", {}) or {}
    active = packs_section.get("active", []) or []
    packs = [str(p) for p in active if p] if isinstance(active, list) else []

    # Resolve includes against the composed view (core → packs → user → project).
    from edison.core.composition.includes import ComposedIncludeProvider
    from edison.core.composition.registries._types_manager import ComposableTypesManager
    from edison.core.composition.engine import TemplateEngine
    from edison.data import get_data_path as _get_data_path

    types_manager = ComposableTypesManager(project_root=project_root)
    include_provider = ComposedIncludeProvider(
        types_manager=types_manager,
        packs=tuple(packs),
        materialize=False,
    ).build()

    engine = TemplateEngine(
        config=cfg,
        packs=packs,
        project_root=project_root,
        source_dir=Path(_get_data_path("")),
        include_provider=include_provider,
        strip_section_markers=True,
    )

    rendered, _report = engine.process(
        raw,
        entity_name=_normalize_prompt_id(prompt_id),
        entity_type="start",
    )
    return rendered
