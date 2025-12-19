"""Session archiving operations."""
from __future__ import annotations

import tarfile
from pathlib import Path

from edison.core.utils import ensure_directory, utc_now
from edison.core.utils.paths import resolve_project_root

from .._config import get_config
from ..core.id import validate_session_id
from .repository import SessionRepository


def _archive_root_dir() -> Path:
    root = resolve_project_root()
    rel_path = get_config().get_archive_root_path()
    return (root / rel_path).resolve()


def _archive_path_for_session(session_id: str) -> Path:
    stamp = utc_now().strftime("%Y-%m")
    return _archive_root_dir() / stamp / f"{session_id}.tar.gz"

def archive_session(session_id: str) -> Path:
    """Archive the session directory into ``.tar.gz`` under ``<project-management-dir>/archive/YYYY-MM/``.

    Preserves internal directory structure. Returns the archive path.
    """
    sid = validate_session_id(session_id)
    # Archive the directory containing the session JSON, regardless of layout.
    repo = SessionRepository()
    j = repo.get_session_json_path(sid)
    d = j.parent

    archive_path = _archive_path_for_session(sid)
    ensure_directory(archive_path.parent)

    # Build tar.gz preserving tree relative to session root for determinism
    with tarfile.open(archive_path, "w:gz") as tf:
        for p in d.rglob("*"):
            tf.add(p, arcname=str(p.relative_to(d)))

    return archive_path
