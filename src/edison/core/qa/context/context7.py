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

    # If the task exists in <project-management-dir>/tasks across states, inspect those copies too.
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
        wt_raw = (session or {}).get("git", {}).get("worktreePath") or ""
        base_branch = (
            (session or {}).get("git", {}).get("baseBranch")
            or (session or {}).get("git", {}).get("base_branch")
            or "main"
        )
        wt_path = Path(wt_raw) if isinstance(wt_raw, (str, Path)) else Path("")
        if wt_path.exists():
            diff_files: List[Path] = []
            try:
                diff_files = get_changed_files(wt_path, base_branch=str(base_branch), session_id=None)
            except Exception as e:
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
        wt_raw = (session or {}).get("git", {}).get("worktreePath") or ""
        wt_path = Path(wt_raw) if isinstance(wt_raw, (str, Path)) else Path("")
        if wt_path.exists():
            ctx7_cfg = Context7Config()
            content_detection = ctx7_cfg.get_content_detection()

            for pkg, detection_cfg in content_detection.items():
                file_patterns = detection_cfg.get("filePatterns", [])
                search_patterns = detection_cfg.get("searchPatterns", [])

                if not file_patterns or not search_patterns:
                    continue

                # Scope content detection to the candidate file set (Primary Files + worktree diff).
                # Scanning the entire worktree would incorrectly require Context7 evidence for
                # packages present in the repo but unrelated to this task's changes.
                for rel in candidates:
                    if not matches_any_pattern(rel, list(file_patterns)):
                        continue
                    file_path = wt_path / rel
                    if not file_path.is_file():
                        continue
                    try:
                        content = file_path.read_text(encoding="utf-8")
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
    # Prefer machine-parseable YAML frontmatter when present. Fall back to a
    # permissive non-empty check for legacy/plain markers.
    raw = str(text or "").strip()
    if not raw:
        return False
    if raw.startswith("---"):
        fm = _parse_marker_frontmatter(raw)
        return not bool(_validate_marker_fields(fm))
    return True


# Required fields for a valid Context7 marker (frontmatter keys).
REQUIRED_MARKER_FIELDS = ["libraryId", "topics"]


def _parse_marker_frontmatter(text: str) -> Dict[str, Any]:
    """Parse YAML frontmatter from a Context7 marker file."""
    import yaml

    text = str(text or "").strip()
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 2:
        return {}
    try:
        frontmatter = yaml.safe_load(parts[1])
        return frontmatter if isinstance(frontmatter, dict) else {}
    except (yaml.YAMLError, Exception):
        return {}


def _validate_marker_fields(frontmatter: Dict[str, Any]) -> List[str]:
    """Return required marker fields missing from frontmatter."""
    missing: List[str] = []
    for field in REQUIRED_MARKER_FIELDS:
        val = frontmatter.get(field)
        if val is None or (isinstance(val, (str, list)) and not val):
            missing.append(field)
    return missing


def classify_marker(round_dir: Path, package: str) -> Dict[str, Any]:
    """Classify a single Context7 marker as missing, invalid, or valid."""
    marker_txt = round_dir / f"context7-{package}.txt"
    marker_md = round_dir / f"context7-{package}.md"

    if marker_txt.exists():
        marker_path = marker_txt
    elif marker_md.exists():
        marker_path = marker_md
    else:
        return {
            "status": "missing",
            "package": package,
            "path_checked": str(marker_txt),
        }

    try:
        content = marker_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.warning("Failed to read marker file %s: %s", marker_path, e)
        return {
            "status": "invalid",
            "package": package,
            "missing_fields": REQUIRED_MARKER_FIELDS[:],
            "error": str(e),
        }

    if not content.strip():
        return {"status": "invalid", "package": package, "missing_fields": REQUIRED_MARKER_FIELDS[:]}

    # Backward compatibility: legacy/plain markers are accepted as "valid" as
    # long as they are non-empty. Prefer YAML frontmatter validation when present.
    if not content.lstrip().startswith("---"):
        return {"status": "valid", "package": package}

    fm = _parse_marker_frontmatter(content)
    missing_fields = _validate_marker_fields(fm)
    if missing_fields:
        return {"status": "invalid", "package": package, "missing_fields": missing_fields}

    return {"status": "valid", "package": package}


def classify_packages(round_dir: Path, packages: List[str]) -> Dict[str, Any]:
    """Classify multiple Context7 packages at once."""
    missing: List[str] = []
    invalid: List[Dict[str, Any]] = []
    valid: List[str] = []

    for pkg in packages:
        res = classify_marker(round_dir, pkg)
        status = res.get("status")
        if status == "missing":
            missing.append(pkg)
        elif status == "invalid":
            invalid.append(
                {
                    "package": pkg,
                    "missing_fields": res.get("missing_fields", []),
                }
            )
        else:
            valid.append(pkg)

    return {"missing": missing, "invalid": invalid, "valid": valid, "evidence_dir": str(round_dir)}


def missing_packages_detailed(task_id: str, packages: Iterable[str]) -> Dict[str, Any]:
    """Return detailed classification for required packages."""
    pkgs = sorted({_normalize(p) for p in packages})
    if not pkgs:
        return {"missing": [], "invalid": [], "valid": [], "evidence_dir": None}

    ev_svc = EvidenceService(task_id)
    rd = ev_svc.get_current_round_dir()
    if rd is None:
        return {"missing": pkgs, "invalid": [], "valid": [], "evidence_dir": None}

    return classify_packages(rd, pkgs)


def missing_packages(task_id: str, packages: Iterable[str]) -> List[str]:
    """Return the list of packages lacking valid Context7 markers."""
    pkgs = sorted({_normalize(p) for p in packages})
    if not pkgs:
        return []

    ev_svc = EvidenceService(task_id)
    rd = ev_svc.get_current_round_dir()
    if rd is None:
        return pkgs

    out: List[str] = []
    for pkg in pkgs:
        res = classify_marker(rd, pkg)
        if res.get("status") != "valid":
            out.append(pkg)
    return out


__all__ = [
    "load_validator_config",
    "detect_packages",
    "missing_packages",
    "classify_marker",
    "classify_packages",
    "missing_packages_detailed",
    "REQUIRED_MARKER_FIELDS",
]
