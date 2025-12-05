#!/usr/bin/env python3
from __future__ import annotations

"""Include resolution, caching, and cycle detection utilities for composition."""

import hashlib
import json
import re
from pathlib import Path
from typing import List, Optional, Set, Tuple

from edison.core.utils.paths import PathResolver
from edison.core.utils.io import write_json_atomic, read_json, ensure_directory
from edison.core.config.manager import ConfigManager
from edison.core.composition.output.writer import CompositionFileWriter

from edison.core.utils.paths import get_project_config_dir
from edison.core.utils.text.core import get_engine_version


def _get_max_depth() -> int:
    """Get max include depth from configuration."""
    try:
        cfg = ConfigManager().load_config(validate=False)
        return cfg.get("composition", {}).get("includes", {}).get("max_depth", 3)
    except Exception:
        # Fallback to safe default if config cannot be loaded
        return 3


class ComposeError(RuntimeError):
    """Composition failure (missing includes, cache violations, etc.)."""


_REPO_ROOT_OVERRIDE: Optional[Path] = None


def _repo_root() -> Path:
    """Resolve Edison repository root using the canonical PathResolver."""
    if _REPO_ROOT_OVERRIDE is not None:
        return _REPO_ROOT_OVERRIDE
    return PathResolver.resolve_project_root()


def _rel(path: Path) -> Path:
    """Return path relative to repo root when possible, else absolute.

    Avoids ValueError when working with bundled data files that live outside
    the active project root (common during CLI-driven composition).
    """

    root = _repo_root()
    try:
        return path.relative_to(root)
    except ValueError:
        return path.resolve()


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
    project_dir = get_project_config_dir(repo_root)
    project_prefix = f"{project_dir.name}/"

    # Absolute from repo root when path starts with '/' or the project config dir name
    if raw.startswith("/"):
        return repo_root / raw.lstrip("/")

    if raw.startswith(project_prefix):
        relative = raw[len(project_prefix) :]
        return project_dir / relative

    if raw.startswith("packs/"):
        base = project_dir if project_dir.exists() else repo_root / project_dir.name
        return base / raw

    # Allow shorthand `project/...` to point at the active project config dir
    if raw.startswith("project/"):
        relative = raw[len("project/") :]
        return project_dir / relative

    # Otherwise relative to current file
    return base_file.parent / target


_INCLUDE_RE = re.compile(r"\{\{\s*include:([^}]+)\}\}")
_INCLUDE_OPT_RE = re.compile(r"\{\{\s*include-optional:([^}]+)\}\}")


def resolve_includes(
    content: str,
    base_file: Path,
    *,
    depth: int = 0,
    stack: Optional[List[Path]] = None,
    deps: Optional[Set[Path]] = None,
    max_depth: Optional[int] = None,
) -> Tuple[str, List[Path]]:
    """Resolve include directives in ``content`` relative to ``base_file``.

    Returns expanded text and the list of dependency file paths in resolution order.
    Raises ComposeError on missing includes, circular refs, or depth overflow.

    T-016: NO LEGACY - safe_include() shim removed completely.
    Only modern syntax supported: {{include:path}} and {{include-optional:path}}

    Args:
        content: Content to resolve includes in
        base_file: Base file path for relative includes
        depth: Current recursion depth
        stack: Stack of files being processed (for cycle detection)
        deps: Set of dependencies discovered
        max_depth: Maximum include depth (defaults to config value)
    """
    if stack is None:
        stack = []
    if deps is None:
        deps = set()

    # Get max_depth from config if not provided
    if max_depth is None:
        max_depth = _get_max_depth()

    # T-016: NO LEGACY - Legacy shim removed (was lines 114-122)
    # Legacy {{safe_include('path', fallback='...')}} syntax is NO LONGER SUPPORTED
    # Use modern {{include-optional:path}} instead

    if depth > max_depth:
        chain = " -> ".join([str(_rel(p)) for p in stack])
        raise ComposeError(
            f"Include depth exceeded (>{max_depth}) while processing {_rel(base_file)}. Chain: {chain}"
        )

    # Process required includes
    def _expand_required(m: re.Match) -> str:
        raw = m.group(1)
        target = _normalize_include_target(raw, base_file).resolve()
        if target in stack:
            chain = " -> ".join([str(_rel(p)) for p in stack + [target]])
            raise ComposeError(f"Circular include detected: {chain}")
        if not target.exists():
            chain = " -> ".join([str(_rel(p)) for p in stack])
            raise ComposeError(
                f"Include not found: {_rel(target)} (from {_rel(base_file)}). Chain: {chain}"
            )
        deps.add(target)
        included = _read_text(target)
        expanded, _ = resolve_includes(
            included, target, depth=depth + 1, stack=stack + [target], deps=deps, max_depth=max_depth
        )
        return expanded

    # Process optional includes
    def _expand_optional(m: re.Match) -> str:
        raw = m.group(1)
        target = _normalize_include_target(raw, base_file).resolve()
        if target in stack:
            chain = " -> ".join([str(_rel(p)) for p in stack + [target]])
            raise ComposeError(f"Circular include detected: {chain}")
        if not target.exists():
            return ""  # silent skip
        deps.add(target)
        included = _read_text(target)
        expanded, _ = resolve_includes(
            included, target, depth=depth + 1, stack=stack + [target], deps=deps, max_depth=max_depth
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
    h.update(get_engine_version().encode("utf-8"))
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
    return proj_dir / "_generated" / "validators"


def _write_cache(validator_id: str, text: str, deps: List[Path], content_hash: str) -> Path:
    out_dir = ensure_directory(_cache_dir())
    out_path = out_dir / f"{validator_id}.md"

    # Use CompositionFileWriter for unified file writing
    writer = CompositionFileWriter(base_dir=_repo_root())
    writer.write_text(out_path, text)

    # Write manifest entry per artifact for traceability
    manifest_path = out_dir / "manifest.json"
    try:
        existing = read_json(manifest_path, default={})
        existing[validator_id] = {
            "path": str(_rel(out_path)),
            "hash": content_hash,
            "engineVersion": get_engine_version(),
            "dependencies": [str(_rel(p)) for p in deps],
        }
        write_json_atomic(manifest_path, existing, indent=2)
    except Exception:
        # Non-fatal
        pass
    return out_path


def validate_composition(text: str) -> None:
    if not text.strip():
        raise ComposeError("Composed prompt is empty after processing.")
    # Check for validator-related keywords (case-insensitive)
    text_lower = text[:1000].lower()
    has_validator_marker = "validator" in text_lower or "validation" in text_lower
    if not has_validator_marker:
        raise ComposeError("Missing core section marker in composed prompt.")


def get_cache_dir() -> Path:
    """Get composed artifacts cache directory, creating it when missing."""
    d = ensure_directory(_cache_dir())
    return d


__all__ = [
    "ComposeError",
    "resolve_includes",
    "_read_text",
    "_hash_files",
    "_write_cache",
    "_cache_dir",
    "_repo_root",
    "get_cache_dir",
    "validate_composition",
]
