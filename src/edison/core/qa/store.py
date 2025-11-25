"""QA record storage helpers (paths + JSONL I/O)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from ..legacy_guard import enforce_no_legacy_project_root
from ..paths.resolver import PathResolver
from ..paths.management import get_management_paths


enforce_no_legacy_project_root("lib.qa.store")


def qa_root(project_root: Optional[Path] = None) -> Path:
    root = project_root or PathResolver.resolve_project_root()
    mgmt_paths = get_management_paths(root)
    return mgmt_paths.get_qa_root()


def score_history_dir(project_root: Optional[Path] = None) -> Path:
    return qa_root(project_root) / "score-history"


def score_history_file(session_id: str, project_root: Optional[Path] = None) -> Path:
    return score_history_dir(project_root) / f"{session_id}.jsonl"


def append_jsonl(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


__all__ = [
    "qa_root",
    "score_history_dir",
    "score_history_file",
    "append_jsonl",
    "read_jsonl",
]
