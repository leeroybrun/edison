from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from edison.core.utils.io import ensure_directory
from edison.core.utils.io.locking import acquire_file_lock


def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8", errors="replace")
        except Exception:
            return repr(value)
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    return value


def append_jsonl(*, path: Path, payload: dict[str, Any], repo_root: Path | None = None) -> None:
    """Append one JSON line to `path` with a file lock + fsync (fail-open)."""
    try:
        ensure_directory(path.parent)
    except Exception:
        return

    try:
        safe = {k: _json_safe(v) for k, v in payload.items()}
        line = json.dumps(safe, ensure_ascii=False) + "\n"
    except Exception:
        return

    try:
        with acquire_file_lock(path, repo_root=repo_root):
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
                try:
                    os.fsync(fh.fileno())
                except Exception:
                    pass
    except Exception:
        return


__all__ = ["append_jsonl"]
