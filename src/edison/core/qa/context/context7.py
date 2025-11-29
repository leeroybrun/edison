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
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

import yaml

from edison.core.utils.paths import PathResolver
from edison.core.utils.paths import get_project_config_dir
from edison.core.utils.paths import get_management_paths
from edison.core.qa.evidence import EvidenceService
from edison.core.utils.git import get_changed_files
from edison.core.qa._utils import parse_primary_files
from edison.core.config.domains.context7 import Context7Config

logger = logging.getLogger(__name__)


def _load_triggers() -> Dict[str, List[str]]:
    """Load triggers from config.

    Raises:
        RuntimeError: If triggers configuration is not available.
    """
    cfg = Context7Config()
    triggers = cfg.get_triggers()
    if not triggers:
        raise RuntimeError(
            "Context7 triggers configuration missing; "
            "define triggers in context7.yml or .edison/config/context7.yml"
        )
    return triggers


def _load_aliases() -> Dict[str, str]:
    """Load aliases from config.

    Raises:
        RuntimeError: If aliases configuration is not available.
    """
    cfg = Context7Config()
    aliases = cfg.get_aliases()
    if not aliases:
        raise RuntimeError(
            "Context7 aliases configuration missing; "
            "define aliases in context7.yml or .edison/config/context7.yml"
        )
    return aliases


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
                from edison.core.utils.io import read_yaml, read_json

                if path.suffix == ".yml" or path.suffix == ".yaml":
                    return read_yaml(path, raise_on_error=True) or {}

                return read_json(path)
            except (FileNotFoundError, OSError) as e:
                logger.debug("Config file not readable at %s: %s", path, e)
                if fail_closed:
                    raise SystemExit("Context7 config invalid or unreadable")
                return {}
            except ValueError as e:
                logger.error("Invalid YAML/JSON in config file %s: %s", path, e)
                if fail_closed:
                    raise SystemExit("Context7 config invalid or unreadable")
                return {}
    if fail_closed:
        raise SystemExit("Context7 config missing (validators.yml)")
    return {}


def _merge_triggers(cfg: Dict) -> Dict[str, List[str]]:
    """Merge config-loaded triggers with validator config overrides."""
    # Start with config-loaded triggers (or fallback defaults)
    triggers = {k: list(v) for k, v in _load_triggers().items()}

    # Merge in any validator config overrides
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
    """Extract Primary Files / Areas list from a task markdown file.

    This is a thin wrapper around the shared parse_primary_files() utility
    that handles reading the file content from a Path object.
    """
    try:
        text = task_path.read_text(errors="ignore")
    except (FileNotFoundError, OSError) as e:
        logger.debug("Failed to read task file %s: %s", task_path, e)
        return []

    return parse_primary_files(text)


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
    except (FileNotFoundError, OSError, RuntimeError) as e:
        logger.debug("Failed to scan task states: %s", e)

    # Worktree scan (session-aware)
    try:
        wt_path = Path((session or {}).get("git", {}).get("worktreePath", ""))
        if wt_path.exists():
            diff_files: List[Path] = []
            try:
                diff_files = get_changed_files(wt_path, session_id=None)
            except (OSError, RuntimeError) as e:
                logger.debug("Failed to get changed files from worktree: %s", e)
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
    except (OSError, ValueError, RuntimeError) as e:
        logger.debug("Failed to scan worktree for candidate files: %s", e)

    return candidates


def _normalize(pkg: str) -> str:
    """Normalize package name using config-loaded aliases."""
    pkg = pkg.lower().strip()
    aliases = _load_aliases()
    for alias, canon in aliases.items():
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

    # Content-based detection using configured patterns
    try:
        wt_path = Path((session or {}).get("git", {}).get("worktreePath", ""))
        if wt_path.exists():
            ctx7_cfg = Context7Config()
            content_detection = ctx7_cfg.get_content_detection()

            for pkg, detection_cfg in content_detection.items():
                file_patterns = detection_cfg.get("filePatterns", [])
                search_patterns = detection_cfg.get("searchPatterns", [])

                if not file_patterns or not search_patterns:
                    continue

                # Find files matching the patterns
                for pattern in file_patterns:
                    for file_path in wt_path.glob(pattern):
                        if not file_path.is_file():
                            continue
                        try:
                            content = file_path.read_text(encoding="utf-8")
                            # Check if any search pattern matches
                            for search_pattern in search_patterns:
                                if re.search(search_pattern, content):
                                    packages.add(_normalize(pkg))
                                    break
                        except (OSError, UnicodeDecodeError) as e:
                            logger.debug("Failed to read file %s for content detection: %s", file_path, e)
                            continue
    except (OSError, RuntimeError, ValueError) as e:
        logger.debug("Failed to perform content-based package detection: %s", e)

    return packages


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

    ev_svc = EvidenceService(task_id)
    rd = ev_svc.get_current_round_dir()
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
        except (FileNotFoundError, OSError, UnicodeDecodeError) as e:
            logger.warning("Failed to read marker file %s: %s", path, e)
            missing.append(pkg)
    return missing


__all__ = [
    "load_validator_config",
    "detect_packages",
    "missing_packages",
]
