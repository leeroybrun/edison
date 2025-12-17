"""Start prompt discovery and loading.

Start prompts are Markdown templates intended to bootstrap an LLM session.

Resolution order (fail-closed):
1. Project-composed prompts: `<project>/.edison/_generated/start/START_*.md`
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
    """Read a start prompt by id (accepts with/without START_ prefix)."""
    return find_start_prompt_path(project_root, prompt_id).read_text(encoding="utf-8", errors="strict")


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
