"""Read/list files under the project-composed `.edison/_generated/` directory.

These helpers intentionally do NOT fall back to bundled templates. They are meant
to support a "developer composes, LLM reads" workflow where the LLM is instructed
to load the composed, canonical artifacts from `_generated/`.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from edison.core.utils.paths.project import get_project_config_dir


@dataclass(frozen=True)
class GeneratedFile:
    name: str
    path: Path
    relpath: str


def _extract_markdown_summary(path: Path, *, max_bytes: int = 8192) -> str:
    if path.suffix.lower() != ".md":
        return ""
    try:
        with path.open("r", encoding="utf-8", errors="strict") as f:
            text = f.read(max_bytes)
    except Exception:
        return ""

    lines = text.splitlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("#"):
            start_idx = i + 1
            break

    for line in lines[start_idx:]:
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            continue
        if s.startswith("{{") and s.endswith("}}"):
            continue
        return s
    return ""


def _reject_path_separators(value: str, *, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    if "/" in text or "\\" in text:
        raise ValueError(f"{field} must not contain path separators")
    if text in {".", ".."} or ".." in text:
        raise ValueError(f"{field} must not contain '..'")
    return text


def _normalize_type(value: Optional[str]) -> Optional[Path]:
    if value is None:
        return None
    text = str(value).strip().replace("\\", "/")
    if not text:
        return None
    # Allow nested subfolders (e.g., guidelines/agents) but disallow traversal/absolute paths.
    cleaned = text.strip("/")
    if not cleaned:
        return None
    parts = [p for p in cleaned.split("/") if p]
    if not parts:
        return None
    for part in parts:
        if part in {".", ".."}:
            raise ValueError("type must not contain '..'")
        if ":" in part:
            raise ValueError("type must not contain ':'")
    return Path(*parts)


def get_generated_root(project_root: Path) -> Path:
    cfg_dir = get_project_config_dir(project_root, create=False)
    return cfg_dir / "_generated"


def list_generated_files(
    project_root: Path,
    *,
    type: Optional[str] = None,
    recursive: bool = False,
) -> List[GeneratedFile]:
    root = get_generated_root(project_root)
    sub = _normalize_type(type)
    base = (root / sub) if sub else root

    if not base.exists():
        return []

    iterator = base.rglob("*") if recursive else base.glob("*")
    files: List[GeneratedFile] = []
    for p in sorted(iterator):
        if not p.is_file():
            continue
        rel = str(p.relative_to(root)).replace("\\", "/")
        files.append(GeneratedFile(name=p.name, path=p, relpath=rel))
    return files


def resolve_generated_file_path(
    project_root: Path,
    *,
    type: Optional[str] = None,
    name: str,
) -> Path:
    root = get_generated_root(project_root)
    sub = _normalize_type(type)
    base = (root / sub) if sub else root

    raw = _reject_path_separators(name, field="name")
    p = Path(raw)
    filename = raw if p.suffix else f"{raw}.md"
    path = base / filename

    root_real = root.resolve()
    path_real = path.resolve()
    if path_real != root_real and root_real not in path_real.parents:
        raise ValueError("Resolved path escapes _generated root")

    if not path.exists():
        raise FileNotFoundError(f"Generated file not found: {path}")
    return path


def list_generated_files_payload(
    project_root: Path,
    *,
    type: Optional[str] = None,
    recursive: bool = False,
) -> List[Dict[str, Any]]:
    return [
        {
            "name": f.name,
            "relpath": f.relpath,
            "path": str(f.path),
            "summary": _extract_markdown_summary(f.path),
        }
        for f in list_generated_files(project_root, type=type, recursive=recursive)
    ]


def read_generated_file_content(
    project_root: Path,
    *,
    type: Optional[str] = None,
    name: str,
    section: Optional[str] = None,
) -> tuple[Path, str]:
    """Read a composed artifact under `.edison/_generated/`.

    Args:
        project_root: Repo root.
        type: Optional `_generated` subfolder (supports nested, e.g. guidelines/shared).
        name: File name (without extension is OK; defaults to .md).
        section: Optional SECTION marker to extract (same semantics as {{include-section:}}).

    Returns:
        (path, content) where content is either the full file or the extracted section.
    """
    path = resolve_generated_file_path(project_root, type=type, name=name)
    content = path.read_text(encoding="utf-8", errors="strict")

    if section:
        from edison.core.composition.core.sections import SectionParser

        extracted = SectionParser().extract_section(content, str(section).strip())
        if extracted is None:
            raise KeyError(f"Section '{section}' not found in {path}")
        content = extracted

    return path, content
