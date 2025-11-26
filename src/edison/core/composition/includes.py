#!/usr/bin/env python3
from __future__ import annotations

"""Include resolution, caching, and cycle detection utilities for composition."""

import hashlib
import json
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple

from edison.core.utils.git import get_repo_root

from ..paths.project import get_project_config_dir
from ..utils.text import ENGINE_VERSION

# Engine constants
MAX_DEPTH = 3


class ComposeError(RuntimeError):
    """Composition failure (missing includes, cache violations, etc.)."""


_REPO_ROOT_OVERRIDE: Optional[Path] = None


def _repo_root() -> Path:
    """Resolve Edison repository root using the shared git utility."""
    if _REPO_ROOT_OVERRIDE is not None:
        return _REPO_ROOT_OVERRIDE
    return get_repo_root()


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    return path.read_text(encoding="utf-8")


def _normalize_include_target(raw: str, base_file: Path) -> Path:
    raw = raw.strip()
    # Allow quotes in include path and strip them
    if (raw.startswith("'") and raw.endswith("'")) or (raw.startswith('"') and raw.endswith('"')):
        raw = raw[1:-1]

    target = Path(raw)
    repo_root = _repo_root()
    # Absolute from repo root when path starts with '/' or a repo-root child like '.edison' or project config dir
    if raw.startswith("/") or raw.startswith(".edison/"):
        if raw.startswith(".edison/") and repo_root.name == ".edison":
            return repo_root / raw[len(".edison/") :]
        return repo_root / raw.lstrip("/")

    if raw.startswith("packs/"):
        base = repo_root if repo_root.name == ".edison" else repo_root / ".edison"
        return base / raw

    project_dir = get_project_config_dir(repo_root)
    project_prefix = f"{project_dir.name}/"

    # Allow shorthand `project/...` to point at the active project config dir
    if raw.startswith("project/"):
        relative = raw[len("project/") :]
        return project_dir / relative

    if raw.startswith(project_prefix):
        relative = raw[len(project_prefix) :]
        return project_dir / relative
    # Otherwise relative to current file
    return base_file.parent / target


_INCLUDE_RE = re.compile(r"\{\{\s*include:([^}]+)\}\}")
_INCLUDE_OPT_RE = re.compile(r"\{\{\s*include-optional:([^}]+)\}\}")
_SAFE_INCLUDE_RE = re.compile(
    r"\{\{\s*safe_include\(\s*['\"]([^'\"]+)['\"]\s*,\s*fallback=['\"][^'\"]*['\"]\s*\)\s*\}\}"
)


def resolve_includes(
    content: str,
    base_file: Path,
    *,
    depth: int = 0,
    stack: Optional[List[Path]] = None,
    deps: Optional[Set[Path]] = None,
) -> Tuple[str, List[Path]]:
    """Resolve include directives in ``content`` relative to ``base_file``.

    Returns expanded text and the list of dependency file paths in resolution order.
    Raises ComposeError on missing includes, circular refs, or depth overflow.
    """
    if stack is None:
        stack = []
    if deps is None:
        deps = set()

    # Legacy shim: convert ``safe_include('path', fallback='...')`` from older
    # templates into the modern ``include-optional:path`` form so callers do
    # not need to migrate all content in lockstep with the engine.
    if "{{" in content:
        def _to_optional(m: re.Match) -> str:
            target = m.group(1)
            return f"{{{{include-optional:{target}}}}}"

        content = _SAFE_INCLUDE_RE.sub(_to_optional, content)

    if depth > MAX_DEPTH:
        chain = " -> ".join([str(p.relative_to(_repo_root())) for p in stack])
        raise ComposeError(
            f"Include depth exceeded (>{MAX_DEPTH}) while processing {base_file.relative_to(_repo_root())}. Chain: {chain}"
        )

    # Process required includes
    def _expand_required(m: re.Match) -> str:
        raw = m.group(1)
        target = _normalize_include_target(raw, base_file).resolve()
        if target in stack:
            chain = " -> ".join([str(p.relative_to(_repo_root())) for p in stack + [target]])
            raise ComposeError(f"Circular include detected: {chain}")
        if not target.exists():
            chain = " -> ".join([str(p.relative_to(_repo_root())) for p in stack])
            raise ComposeError(
                f"Include not found: {target.relative_to(_repo_root())} (from {base_file.relative_to(_repo_root())}). Chain: {chain}"
            )
        deps.add(target)
        included = _read_text(target)
        expanded, _ = resolve_includes(
            included, target, depth=depth + 1, stack=stack + [target], deps=deps
        )
        return expanded

    # Process optional includes
    def _expand_optional(m: re.Match) -> str:
        raw = m.group(1)
        target = _normalize_include_target(raw, base_file).resolve()
        if target in stack:
            chain = " -> ".join([str(p.relative_to(_repo_root())) for p in stack + [target]])
            raise ComposeError(f"Circular include detected: {chain}")
        if not target.exists():
            return ""  # silent skip
        deps.add(target)
        included = _read_text(target)
        expanded, _ = resolve_includes(
            included, target, depth=depth + 1, stack=stack + [target], deps=deps
        )
        return expanded

    # One pass each; nesting handled via recursive calls
    content = _INCLUDE_RE.sub(_expand_required, content)
    content = _INCLUDE_OPT_RE.sub(_expand_optional, content)

    return content, list(deps)


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hash_files(paths: List[Path], extra: Optional[str] = None) -> str:
    h = hashlib.sha256()
    h.update(ENGINE_VERSION.encode("utf-8"))
    if extra:
        h.update(extra.encode("utf-8"))
    root = _repo_root()
    for p in sorted(set(paths)):
        try:
            rel = p.relative_to(root)
        except ValueError:
            rel = p
        h.update(str(rel).encode("utf-8"))
        if p.exists():
            h.update(p.read_bytes())
    return h.hexdigest()


def _cache_dir() -> Path:
    """Get composed artifacts cache directory (project-scoped)."""
    root = _repo_root()
    proj_dir = get_project_config_dir(root)
    old = root / ".edison" / "core" / ".cache" / "composed"
    if old.exists():
        rel = old.relative_to(root)
        raise ComposeError(
            f"Legacy cache path detected: {rel}. "
            "Edison no longer writes or reads from this location. "
            f"Move artifacts to {proj_dir.name}/.cache/composed and delete the old directory."
        )
    return proj_dir / ".cache" / "composed"


def _write_cache(validator_id: str, text: str, deps: List[Path], content_hash: str) -> Path:
    out_dir = _cache_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{validator_id}.md"
    out_path.write_text(text, encoding="utf-8")
    # Write manifest entry per artifact for traceability
    manifest_path = out_dir / "manifest.json"
    try:
        existing = {}
        if manifest_path.exists():
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        existing[validator_id] = {
            "path": str(out_path.relative_to(_repo_root())),
            "hash": content_hash,
            "engineVersion": ENGINE_VERSION,
            "dependencies": [str(p.relative_to(_repo_root())) for p in deps],
        }
        manifest_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    except Exception:
        # Non-fatal
        pass
    return out_path


def validate_composition(text: str) -> None:
    if not text.strip():
        raise ComposeError("Composed prompt is empty after processing.")
    # Ensure obvious compose markers present (support both legacy and template-based composition)
    has_legacy_marker = "# Core Edison Principles" in text
    # Check for validator-related keywords (case-insensitive)
    text_lower = text[:1000].lower()
    has_validator_marker = "validator" in text_lower or "validation" in text_lower
    if not has_legacy_marker and not has_validator_marker:
        raise ComposeError("Missing core section marker in composed prompt.")


def get_cache_dir() -> Path:
    """Get composed artifacts cache directory, creating it when missing."""
    d = _cache_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d


__all__ = [
    "ComposeError",
    "resolve_includes",
    "_read_text",
    "_hash_files",
    "_write_cache",
    "_cache_dir",
    "_repo_root",
    "_REPO_ROOT_OVERRIDE",
    "get_cache_dir",
    "validate_composition",
    "MAX_DEPTH",
]
