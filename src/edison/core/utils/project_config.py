from __future__ import annotations

"""Helpers for loading project metadata (name/owner/audit_terms) via ConfigManager."""

from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

import getpass
import os

from ..paths.project import get_project_config_dir

DEFAULT_PROJECT_TERMS = ["project", "app_", "better-auth", "odoo"]


def _resolve_repo_root(repo_root: Optional[Path | str]) -> Path:
    if repo_root is not None:
        try:
            return Path(repo_root).resolve()
        except Exception:
            pass
    try:
        from ..paths import resolver as paths_resolver

        return paths_resolver.PathResolver.resolve_project_root()
    except Exception:
        return Path.cwd().resolve()


@lru_cache(maxsize=4)
def _load_project_settings(repo_root: Path) -> Dict[str, object]:
    from ..config import ConfigManager

    cfg = ConfigManager(repo_root).load_config(validate=False)
    project = cfg.get("project") or {}
    if not isinstance(project, dict):
        project = {}

    name_raw = project.get("name")
    name = str(name_raw).strip() if name_raw is not None else ""
    if not name or (name == "project" and not _has_explicit_project_name(repo_root)):
        name = repo_root.name

    owner_raw = project.get("owner")
    owner = str(owner_raw).strip() if isinstance(owner_raw, str) and owner_raw.strip() else None

    audit_raw = project.get("audit_terms")
    if isinstance(audit_raw, list):
        audit_terms = [str(t).strip() for t in audit_raw if str(t).strip()]
    elif audit_raw is None:
        audit_terms = []
    else:
        text = str(audit_raw).strip()
        audit_terms = [text] if text else []

    return {
        "name": name,
        "owner": owner,
        "audit_terms": audit_terms,
    }


def get_project_settings(repo_root: Optional[Path | str] = None) -> Dict[str, object]:
    root = _resolve_repo_root(repo_root)
    settings = _load_project_settings(root)
    return {
        "name": str(settings.get("name", "project")),
        "owner": settings.get("owner"),
        "audit_terms": list(settings.get("audit_terms", [])),
    }


def get_project_name(repo_root: Optional[Path | str] = None) -> str:
    return str(get_project_settings(repo_root).get("name") or "project")


def get_project_owner(repo_root: Optional[Path | str] = None) -> str:
    owner = get_project_settings(repo_root).get("owner")
    if isinstance(owner, str) and owner.strip():
        return owner.strip()
    return getpass.getuser()


def get_project_audit_terms(repo_root: Optional[Path | str] = None) -> List[str]:
    return list(get_project_settings(repo_root).get("audit_terms") or [])


def project_terms(repo_root: Optional[Path | str] = None) -> List[str]:
    settings = get_project_settings(repo_root)
    terms: List[str] = list(DEFAULT_PROJECT_TERMS)

    project_name = str(settings.get("name", "")).strip()
    if project_name:
        lower_name = project_name.lower()
        terms.append(lower_name)
        terms.append(lower_name.replace("-", " "))

    for extra in settings.get("audit_terms", []):
        t = str(extra).strip().lower()
        if t:
            terms.append(t)

    unique: List[str] = []
    seen = set()
    for term in terms:
        if term and term not in seen:
            seen.add(term)
            unique.append(term)
    return unique


def substitute_project_tokens(raw: str, repo_root: Optional[Path | str] = None) -> str:
    if not isinstance(raw, str):
        return raw
    name = get_project_name(repo_root)
    return raw.replace("{PROJECT_NAME}", name)


def reset_project_config_cache() -> None:
    _load_project_settings.cache_clear()


def resolve_project_repo_root(repo_root: Optional[Path | str] = None) -> Path:
    return _resolve_repo_root(repo_root)


__all__ = [
    "DEFAULT_PROJECT_TERMS",
    "get_project_settings",
    "get_project_name",
    "get_project_owner",
    "get_project_audit_terms",
    "project_terms",
    "substitute_project_tokens",
    "reset_project_config_cache",
    "resolve_project_repo_root",
]
def _has_explicit_project_name(repo_root: Path) -> bool:
    overlay_dir = get_project_config_dir(repo_root, create=False) / "config"
    for filename in ("project.yml", "project.yaml"):
        if (overlay_dir / filename).exists():
            return True
    return any(key in os.environ for key in ("PROJECT_NAME", "EDISON_project__name"))
