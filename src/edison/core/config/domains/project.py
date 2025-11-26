"""Domain-specific configuration for project metadata.

Provides cached access to project metadata (name, owner, audit terms).
"""
from __future__ import annotations

import getpass
import os
from functools import cached_property
from pathlib import Path
from typing import List, Optional

from ..base import BaseDomainConfig
from edison.core.utils.paths import get_project_config_dir

DEFAULT_PROJECT_TERMS = ["project", "app_", "better-auth", "odoo"]


class ProjectConfig(BaseDomainConfig):
    """Domain-specific configuration accessor for project metadata.

    Provides typed, cached access to project configuration including:
    - Project name
    - Project owner
    - Audit terms

    Extends BaseDomainConfig for consistent caching and repo_root handling.
    """

    def _config_section(self) -> str:
        return "project"

    def _has_explicit_project_name(self) -> bool:
        """Check if project name is explicitly configured."""
        overlay_dir = get_project_config_dir(self.repo_root, create=False) / "config"
        for filename in ("project.yml", "project.yaml"):
            if (overlay_dir / filename).exists():
                return True
        return any(key in os.environ for key in ("PROJECT_NAME", "EDISON_project__name"))

    @cached_property
    def name(self) -> str:
        """Get the project name.

        Returns:
            Project name from config, or repo directory name as fallback.
        """
        name_raw = self.section.get("name")
        name = str(name_raw).strip() if name_raw is not None else ""
        if not name or (name == "project" and not self._has_explicit_project_name()):
            name = self.repo_root.name
        return name

    @cached_property
    def owner(self) -> Optional[str]:
        """Get the project owner.

        Returns:
            Owner string if configured, None otherwise.
        """
        owner_raw = self.section.get("owner")
        if isinstance(owner_raw, str) and owner_raw.strip():
            return owner_raw.strip()
        return None

    @cached_property
    def audit_terms(self) -> List[str]:
        """Get the list of audit terms.

        Returns:
            List of audit terms for the project.
        """
        audit_raw = self.section.get("audit_terms")
        if isinstance(audit_raw, list):
            return [str(t).strip() for t in audit_raw if str(t).strip()]
        elif audit_raw is None:
            return []
        else:
            text = str(audit_raw).strip()
            return [text] if text else []

    def get_owner_or_user(self) -> str:
        """Get owner, falling back to current system user.

        Returns:
            Owner string or current username.
        """
        if self.owner:
            return self.owner
        return getpass.getuser()

    def get_project_terms(self) -> List[str]:
        """Get combined project terms for auditing.

        Combines default terms with project name and audit terms.

        Returns:
            List of unique project terms.
        """
        terms: List[str] = list(DEFAULT_PROJECT_TERMS)

        if self.name:
            lower_name = self.name.lower()
            terms.append(lower_name)
            terms.append(lower_name.replace("-", " "))

        for extra in self.audit_terms:
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

    def substitute_project_tokens(self, raw: str) -> str:
        """Substitute project tokens in a string.

        Args:
            raw: String potentially containing {PROJECT_NAME} tokens.

        Returns:
            String with tokens replaced.
        """
        if not isinstance(raw, str):
            return raw
        return raw.replace("{PROJECT_NAME}", self.name)


# ---------------------------------------------------------------------------
# Module-level helper functions (backward compatibility)
# ---------------------------------------------------------------------------


def get_project_settings(repo_root: Optional[Path] = None) -> dict:
    """Get project settings as a dict."""
    cfg = ProjectConfig(repo_root=repo_root)
    return {
        "name": cfg.name,
        "owner": cfg.owner,
        "audit_terms": cfg.audit_terms,
    }


def get_project_name(repo_root: Optional[Path] = None) -> str:
    """Get project name."""
    return ProjectConfig(repo_root=repo_root).name


def get_project_owner(repo_root: Optional[Path] = None) -> str:
    """Get project owner (or current user as fallback)."""
    return ProjectConfig(repo_root=repo_root).get_owner_or_user()


def get_project_audit_terms(repo_root: Optional[Path] = None) -> List[str]:
    """Get project audit terms."""
    return ProjectConfig(repo_root=repo_root).audit_terms


def project_terms(repo_root: Optional[Path] = None) -> List[str]:
    """Get combined project terms for auditing."""
    return ProjectConfig(repo_root=repo_root).get_project_terms()


def substitute_project_tokens(raw: str, repo_root: Optional[Path] = None) -> str:
    """Substitute project tokens in a string."""
    return ProjectConfig(repo_root=repo_root).substitute_project_tokens(raw)


__all__ = [
    "ProjectConfig",
    "DEFAULT_PROJECT_TERMS",
    "get_project_settings",
    "get_project_name",
    "get_project_owner",
    "get_project_audit_terms",
    "project_terms",
    "substitute_project_tokens",
]
