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

# Default audit terms are intentionally empty.
# Projects should declare `project.audit_terms` in `.edison/config/project.yaml` when needed.
DEFAULT_PROJECT_TERMS: List[str] = []


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

        Resolution order:
        1. AGENTS_OWNER environment variable (highest priority)
        2. Config file (project.owner in YAML)
        3. Process tree detection (edison or LLM process)

        Returns:
            Owner string, or None if no owner could be determined.
        """
        # Check env var first (highest priority)
        env_owner = os.environ.get("AGENTS_OWNER", "").strip()
        if env_owner:
            return env_owner

        # Check config file
        owner_raw = self.section.get("owner")
        if isinstance(owner_raw, str) and owner_raw.strip():
            return owner_raw.strip()

        # Fall back to process detection
        try:
            from edison.core.utils.process.inspector import find_topmost_process
            process_name, _ = find_topmost_process()
            if process_name:
                return process_name
        except Exception:
            pass

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
        """Get owner, falling back to process name then current system user.

        Returns:
            Owner string, process name, or current username.
        """
        if self.owner:
            return self.owner
        # Try process-based detection before username fallback
        try:
            from edison.core.utils.process.inspector import find_topmost_process
            process_name, _ = find_topmost_process()
            if process_name:
                return process_name
        except Exception:
            pass
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
            terms.append(lower_name.replace("-", "_"))

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


__all__ = [
    "ProjectConfig",
    "DEFAULT_PROJECT_TERMS",
]




