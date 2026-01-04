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
from typing import Any, Dict, Iterable, List, Optional, Set

from edison.core.context.files import FileContextService
from edison.core.utils.paths import PathResolver
from edison.core.utils.patterns import matches_any_pattern
from edison.core.qa.evidence import EvidenceService
from edison.core.config.domains.context7 import Context7Config
from edison.core.utils.text.frontmatter import parse_frontmatter

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


def _extract_task_id(task_path: Path) -> str:
    """Extract the canonical task id from a task markdown file.

    Falls back to filename stem for robustness.
    """
    try:
        text = task_path.read_text(encoding="utf-8", errors="ignore")
        doc = parse_frontmatter(text)
        raw = doc.frontmatter.get("id")
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    except Exception as e:
        logger.debug("Failed to extract task id from %s: %s", task_path, e)

    return task_path.stem


def _parse_primary_files(task_path: Path) -> List[str]:
    """Parse "Primary Files / Areas" from a task markdown file.

    This is intentionally tolerant: some tasks may be incomplete or missing
    frontmatter, but still declare their scope in the body.
    """
    try:
        text = task_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    lines = text.splitlines()
    start_idx: int | None = None
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("## primary files"):
            start_idx = i + 1
            break

    if start_idx is None:
        return []

    out: List[str] = []
    for line in lines[start_idx:]:
        s = line.strip()
        if s.startswith("## "):
            break
        if not s.startswith("- "):
            continue
        item = s[2:].strip()
        if not item or "<<fill:" in item.lower() or item.startswith("<<"):
            continue
        out.append(item)
    return out


def _collect_candidate_files_with_trace(task_path: Path, session: Optional[Dict]) -> tuple[List[str], bool]:
    """Gather file paths (relative) that might imply Context7 packages.

    Returns (candidates, used_fallback_heuristic).
    """
    candidates: List[str] = []
    used_fallback = True

    primary = _parse_primary_files(task_path)
    if primary:
        candidates.extend(primary)
        used_fallback = False

    try:
        task_id = _extract_task_id(task_path)
        session_id = str((session or {}).get("id") or (session or {}).get("sessionId") or "").strip() or None

        ctx = FileContextService(project_root=_project_root()).get_for_task(task_id, session_id=session_id)
        for p in (ctx.all_files or []):
            s = str(p).strip()
            if s and s not in candidates:
                candidates.append(s)
        used_fallback = used_fallback or (ctx.source not in {"implementation_report", "task_spec"})
        return candidates, used_fallback
    except Exception as e:
        logger.debug("Failed to collect candidate files for Context7 detection: %s", e)
        return candidates, used_fallback


def _collect_candidate_files(task_path: Path, session: Optional[Dict]) -> List[str]:
    candidates, _used_fallback = _collect_candidate_files_with_trace(task_path, session)
    return candidates


def _normalize(pkg: str) -> str:
    """Normalize package name using config-loaded aliases."""
    pkg = pkg.lower().strip()
    aliases = _load_aliases()
    for alias, canon in aliases.items():
        if pkg.startswith(alias):
            return canon
    return pkg


def _detect_packages_from_candidates(candidates: Iterable[str], triggers: Dict[str, List[str]]) -> Set[str]:
    packages: Set[str] = set()
    for rel in candidates:
        rel_s = str(rel or "").strip()
        if not rel_s:
            continue
        for pkg, pats in triggers.items():
            raw_pkg = str(pkg or "").strip()
            if raw_pkg == "+" or not raw_pkg:
                continue
            if matches_any_pattern(rel_s, pats):
                packages.add(_normalize(raw_pkg))
    return packages


def detect_packages(task_path: Path, session: Optional[Dict]) -> Set[str]:
    """Detect which post-training packages are implicated by file patterns/content."""
    triggers = _load_triggers()

    candidates, _used_fallback = _collect_candidate_files_with_trace(task_path, session)
    if os.environ.get("DEBUG_CONTEXT7"):
        print(f"[CTX7] candidates={candidates}", file=sys.stderr)
    packages = _detect_packages_from_candidates(candidates, triggers)

    # Content-based detection using configured patterns
    try:
        wt_raw = (session or {}).get("git", {}).get("worktreePath")
        wt_path = Path(wt_raw) if isinstance(wt_raw, (str, Path)) and str(wt_raw).strip() else _project_root()
        if wt_path.exists():
            ctx7_cfg = Context7Config()
            content_detection = ctx7_cfg.get_content_detection()

            for pkg, detection_cfg in content_detection.items():
                raw_pkg = str(pkg or "").strip()
                if raw_pkg == "+" or not raw_pkg:
                    continue
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
                                packages.add(_normalize(raw_pkg))
                                break
                    except (OSError, UnicodeDecodeError) as e:
                        logger.debug("Failed to read file %s for content detection: %s", file_path, e)
                        continue
    except (OSError, RuntimeError, ValueError) as e:
        logger.debug("Failed to perform content-based package detection: %s", e)

    return packages


def detect_packages_detailed(task_path: Path, session: Optional[Dict]) -> Dict[str, Any]:
    """Detect packages and return a detailed detection trace."""
    candidates, used_fallback = _collect_candidate_files_with_trace(task_path, session)
    packages = _detect_packages_from_candidates(candidates, _load_triggers())
    return {
        "packages": sorted(packages),
        "candidates": list(candidates),
        "usedFallback": bool(used_fallback),
    }


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
REQUIRED_MARKER_FIELDS = ["libraryId", "topics", "queriedAt"]


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

    # Edison markers must be machine-parseable; non-frontmatter markers are invalid.
    if not content.lstrip().startswith("---"):
        return {"status": "invalid", "package": package, "missing_fields": REQUIRED_MARKER_FIELDS[:]}

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
    "detect_packages_detailed",
    "missing_packages",
    "classify_marker",
    "classify_packages",
    "missing_packages_detailed",
    "REQUIRED_MARKER_FIELDS",
]
