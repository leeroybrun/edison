"""Context7 detection + marker validation helpers shared by task guards.

Design principles:
- No mocks or legacy fallbacks; configuration is loaded from YAML/JSON under
  the project `.agents` directory when present.
- Package detection is driven by declarative `triggers` patterns with sensible
  defaults so guards keep working even when config is absent.
- Evidence is validated against the latest round only and must contain minimal
  metadata (package, topics, retrieved/version, docs) to count as present.
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import yaml

from edison.core.paths import PathResolver
from edison.core.paths.project import get_project_config_dir
from edison.core.paths.management import get_management_paths
from edison.core.qa import evidence as qa_evidence
from edison.core.git.operations import get_changed_files


DEFAULT_TRIGGERS: Dict[str, List[str]] = {
    "react": ["*.tsx", "*.jsx", "**/components/**/*"],
    "next": ["app/**/*", "**/route.ts", "**/layout.tsx", "**/page.tsx"],
    "zod": ["**/*.schema.ts", "**/*.validation.ts", "**/*schema.ts"],
    "prisma": [
        "**/*.prisma",
        "**/prisma/schema.*",
        "**/prisma/migrations/**/*",
        "**/prisma/seeds/**/*",
    ],
}

ALIASES = {
    "react-dom": "react",
    "next/router": "next",
    "nextjs": "next",
    "@prisma/client": "prisma",
    "prisma-client": "prisma",
}


def _project_root() -> Path:
    return PathResolver.resolve_project_root()


def load_validator_config(*, fail_closed: bool = False) -> Dict:
    """Load Context7 validator config from the project.

    When ``fail_closed`` is True, missing config raises SystemExit to satisfy
    the explicit guard tests; otherwise an empty dict is returned.
    """
    root = _project_root()
    config_root = get_project_config_dir(root)
    candidates = [
        config_root / "config" / "validators.yml",
        config_root / "validators" / "config.json",
    ]
    for path in candidates:
        if path.exists():
            try:
                if path.suffix == ".yml" or path.suffix == ".yaml":
                    return yaml.safe_load(path.read_text()) or {}
                return json.loads(path.read_text())
            except Exception:
                # Treat unreadable config as missing in fail_closed mode
                if fail_closed:
                    raise SystemExit("Context7 config invalid or unreadable")
                return {}
    if fail_closed:
        raise SystemExit("Context7 config missing (validators.yml)")
    return {}


def _merge_triggers(cfg: Dict) -> Dict[str, List[str]]:
    triggers = {k: list(v) for k, v in DEFAULT_TRIGGERS.items()}
    packages = (cfg.get("postTrainingPackages") or {}) if isinstance(cfg, dict) else {}
    for pkg, meta in packages.items():
        pats = meta.get("triggers") if isinstance(meta, dict) else None
        if not pats:
            continue
        existing = triggers.get(pkg, [])
        merged = list(dict.fromkeys([*existing, *pats]))
        triggers[pkg] = merged
    return triggers


def _parse_primary_files(task_path: Path) -> List[str]:
    """Extract Primary Files / Areas list from a task markdown file."""
    files: List[str] = []
    try:
        text = task_path.read_text(errors="ignore")
    except Exception:
        return files

    capture = False
    for line in text.splitlines():
        if "Primary Files / Areas" in line:
            capture = True
            continue
        if capture:
            if line.startswith("## "):
                break
            if line.strip().startswith("-"):
                files.append(line.split("-", 1)[1].strip())
    return files


def _collect_candidate_files(task_path: Path, session: Optional[Dict]) -> List[str]:
    """Gather file paths (relative) that might imply Context7 packages."""
    candidates: List[str] = []
    candidates.extend(_parse_primary_files(task_path))

    # If the task exists in .project/tasks across states, inspect those copies too.
    try:
        root = _project_root()
        mgmt_paths = get_management_paths(root)
        for base in (root / "tasks", mgmt_paths.get_tasks_root()):
            for state in ("todo", "wip", "blocked", "done", "validated"):
                path = base / state / task_path.name
                if path.exists():
                    candidates.extend(_parse_primary_files(path))
    except Exception:
        pass

    # Worktree scan (session-aware)
    try:
        wt_path = Path((session or {}).get("git", {}).get("worktreePath", ""))
        if wt_path.exists():
            diff_files: List[Path] = []
            try:
                diff_files = get_changed_files(wt_path, session_id=None)
            except Exception:
                diff_files = []
            if diff_files:
                candidates.extend([p.as_posix() for p in diff_files])
            else:
                for path in wt_path.rglob("*"):
                    if not path.is_file():
                        continue
                    rel = path.relative_to(wt_path).as_posix()
                    # Keep the list focused to avoid noise
                    if any(
                        rel.endswith(ext)
                        for ext in (".ts", ".tsx", ".jsx", ".prisma", ".sql")
                    ) or "prisma/" in rel or "app/" in rel:
                        candidates.append(rel)
    except Exception:
        pass

    return candidates


def _normalize(pkg: str) -> str:
    pkg = pkg.lower().strip()
    for alias, canon in ALIASES.items():
        if pkg.startswith(alias):
            return canon
    return pkg


def detect_packages(task_path: Path, session: Optional[Dict]) -> Set[str]:
    """Detect which post-training packages are implicated by file patterns/content."""
    cfg = load_validator_config(fail_closed=False)
    triggers = _merge_triggers(cfg)
    packages: Set[str] = set()

    candidates = _collect_candidate_files(task_path, session)
    if os.environ.get("DEBUG_CONTEXT7"):
        print(f"[CTX7] candidates={candidates}", file=sys.stderr)
    for rel in candidates:
        for pkg, pats in triggers.items():
            if any(fnmatch.fnmatch(rel, pat) for pat in pats):
                packages.add(_normalize(pkg))
        # Additional heuristics
        lower_rel = rel.lower()
        if lower_rel.endswith(".prisma") or "/prisma/" in lower_rel:
            packages.add("prisma")
    # Content-based zod detection (files in worktree)
    try:
        wt_path = Path((session or {}).get("git", {}).get("worktreePath", ""))
        if wt_path.exists():
            for ts_file in wt_path.rglob("*.ts"):
                try:
                    if "zod" in ts_file.read_text(encoding="utf-8"):
                        packages.add("zod")
                except Exception:
                    continue
    except Exception:
        pass

    return packages


def _latest_round_dir(task_id: str) -> Optional[Path]:
    base = qa_evidence.get_evidence_dir(task_id)
    round_id = qa_evidence.get_latest_round(task_id)
    if round_id is None:
        return None
    rd = base / f"round-{round_id}"
    return rd if rd.is_dir() else None


def _marker_valid(text: str) -> bool:
    lowered = text.lower()
    return (
        "package:" in lowered
        and "topics:" in lowered
        and ("retrieved:" in lowered or "version:" in lowered or "date:" in lowered)
        and ("docs:" in lowered or "doc:" in lowered or "link:" in lowered)
    )


def missing_packages(task_id: str, packages: Iterable[str]) -> List[str]:
    """Return the list of packages lacking valid Context7 markers."""
    pkgs = sorted({_normalize(p) for p in packages})
    if not pkgs:
        return []
    rd = _latest_round_dir(task_id)
    if rd is None:
        return pkgs

    missing: List[str] = []
    for pkg in pkgs:
        marker_txt = rd / f"context7-{pkg}.txt"
        marker_md = rd / f"context7-{pkg}.md"
        path = marker_txt if marker_txt.exists() else marker_md if marker_md.exists() else None
        if not path:
            missing.append(pkg)
            continue
        try:
            if not _marker_valid(path.read_text()):
                missing.append(pkg)
        except Exception:
            missing.append(pkg)
    return missing


__all__ = [
    "load_validator_config",
    "detect_packages",
    "missing_packages",
]
