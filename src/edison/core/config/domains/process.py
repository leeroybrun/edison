"""Domain-specific configuration for process detection.

Provides cached access to process detection patterns including LLM processes,
Edison processes, and script markers for session ID inference.
"""
from __future__ import annotations

from functools import cached_property
from typing import List

from ..base import BaseDomainConfig

# Default values as fallbacks (kept small; config expands these as needed)
DEFAULT_LLM_NAMES = ["claude", "codex", "gemini", "cursor", "aider", "happy"]
DEFAULT_EDISON_NAMES = ["edison", "python"]


class ProcessConfig(BaseDomainConfig):
    """Domain-specific configuration accessor for process detection.

    Provides typed, cached access to process detection configuration including:
    - LLM process names
    - Edison process names
    - Script markers for command-line detection

    Extends BaseDomainConfig for consistent caching and repo_root handling.
    """

    def _config_section(self) -> str:
        return "process"

    @cached_property
    def llm_processes(self) -> List[str]:
        """Get list of known LLM/AI assistant process names.

        Returns:
            List of LLM process names (default: claude, codex, gemini, etc.).
        """
        names = self.section.get("llm_processes")
        if isinstance(names, list):
            return [str(n).lower() for n in names if str(n).strip()]
        return list(DEFAULT_LLM_NAMES)

    @cached_property
    def edison_processes(self) -> List[str]:
        """Get list of Edison process patterns.

        Returns:
            List of Edison process names (default: edison, python).
        """
        names = self.section.get("edison_processes")
        if isinstance(names, list):
            return [str(n).lower() for n in names if str(n).strip()]
        return list(DEFAULT_EDISON_NAMES)

    @cached_property
    def edison_script_markers(self) -> List[str]:
        """Get list of command-line markers that indicate Edison scripts.

        Returns:
            List of script markers to check in command lines.
        """
        markers = self.section.get("edison_script_markers")

        if isinstance(markers, list):
            return [str(m).strip().lower() for m in markers if str(m).strip()]

        # Dynamic fallback: include configured project config dir marker rather than
        # hardcoding ".edison".
        try:
            from edison.core.utils.paths import get_project_config_dir

            return ["edison", get_project_config_dir(self.repo_root, create=False).name.lower()]
        except Exception:
            return ["edison", ".edison"]

    def get_llm_processes(self) -> List[str]:
        """Get list of known LLM/AI assistant process names."""
        return self.llm_processes

    def get_edison_processes(self) -> List[str]:
        """Get list of Edison process patterns."""
        return self.edison_processes

    def get_edison_script_markers(self) -> List[str]:
        """Get list of command-line markers that indicate Edison scripts."""
        return self.edison_script_markers


__all__ = [
    "ProcessConfig",
    "DEFAULT_LLM_NAMES",
    "DEFAULT_EDISON_NAMES",
]
