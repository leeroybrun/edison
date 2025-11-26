"""Session archiving operations."""
from __future__ import annotations

import tarfile
from datetime import datetime
from pathlib import Path

from ..file_io.utils import ensure_dir
from ..paths.resolver import PathResolver
from .store import sanitize_session_id, get_session_json_path
from .config import SessionConfig

_CONFIG = SessionConfig()

def _archive_root_dir() -> Path:
    root = PathResolver.resolve_project_root()
    rel_path = _CONFIG.get_archive_root_path()
    return (root / rel_path).resolve()

def _archive_path_for_session(session_id: str) -> Path:
    stamp = datetime.now().strftime("%Y-%m")
    return _archive_root_dir() / stamp / f"{session_id}.tar.gz"

def archive_session(session_id: str) -> Path:
    """Archive the session directory into ``.tar.gz`` under ``.project/archive/YYYY-MM/``.

    Preserves internal directory structure. Returns the archive path.
    """
    sid = sanitize_session_id(session_id)
    # Archive the directory containing the session JSON, regardless of layout.
    j = get_session_json_path(sid)
    d = j.parent

    archive_path = _archive_path_for_session(sid)
    ensure_dir(archive_path.parent)

    # Build tar.gz preserving tree relative to session root for determinism
    with tarfile.open(archive_path, "w:gz") as tf:
        for p in d.rglob("*"):
            tf.add(p, arcname=str(p.relative_to(d)))

    return archive_path
