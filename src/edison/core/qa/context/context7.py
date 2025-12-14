"""Context7 detection + marker validation helpers shared by task guards.

Design principles:
- No mocks or legacy fallbacks; configuration is loaded from YAML/JSON under
  the project configuration directory (resolved by Edison path rules).
- Package detection is driven by declarative `triggers` patterns with sensible
  defaults so guards keep working even when config is absent.
- Evidence is validated against the latest round only and must contain minimal
  metadata (package, topics, retrieved/version, docs) to count as present.
"""
from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from edison.core.utils.paths import PathResolver
from edison.core.utils.paths import get_management_paths
from edison.core.utils.patterns import matches_any_pattern
from edison.core.qa.evidence import EvidenceService
from edison.core.utils.git import get_changed_files
from edison.core.qa._utils import parse_primary_files
from edison.core.config.domains.context7 import Context7Config

logger = logging.getLogger(__name__)


def _load_triggers() -> Dict[str, List[str]]:
    """Load triggers from config.

    Returns:
        Dict mapping package->patterns. Empty dict means "no post-training packages configured".
    """
    cfg = Context7Config()
    triggers = cfg.get_triggers()
    return triggers


def _load_aliases() -> Dict[str, str]:
    """Load aliases from config.

    Returns:
        Dict mapping alias->canonical. Empty dict means "no aliases configured".
    """
    cfg = Context7Config()
    aliases = cfg.get_aliases()
    return aliases


def _project_root() -> Path:
    return PathResolver.resolve_project_root()


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
        from edison.core.config.domains.workflow import WorkflowConfig
        
        root = _project_root()
        mgmt_paths = get_management_paths(root)
        for base in (mgmt_paths.get_tasks_root(),):
            for state in WorkflowConfig().get_states("task"):
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
    triggers = _load_triggers()
    packages: Set[str] = set()

    candidates = _collect_candidate_files(task_path, session)
    if os.environ.get("DEBUG_CONTEXT7"):
        print(f"[CTX7] candidates={candidates}", file=sys.stderr)
    for rel in candidates:
        for pkg, pats in triggers.items():
            if matches_any_pattern(rel, pats):
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
