"""Domain-specific configuration for process detection.

Provides cached access to process detection patterns including LLM processes,
Edison processes, and script markers for session ID inference.
"""
from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import List, Optional

from ..base import BaseDomainConfig
from edison.data import read_yaml as real_read_yaml, file_exists as real_file_exists

# Default values as fallbacks
DEFAULT_LLM_NAMES = ["claude", "codex", "gemini", "cursor", "aider", "happy"]
DEFAULT_EDISON_NAMES = ["edison", "python"]
DEFAULT_EDISON_MARKERS = [
    "edison",
    ".edison",
]


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
    def _process_yaml(self) -> dict[str, object]:
        """Load process.yaml from bundled data.

        Returns:
            Process configuration dict, or empty dict if not found.
        """
        if not real_file_exists("config", "process.yaml"):
            return {}

        try:
            raw_config = real_read_yaml("config", "process.yaml")
            return raw_config if isinstance(raw_config, dict) else {}
        except Exception:
            return {}

    @cached_property
    def llm_processes(self) -> List[str]:
        """Get list of known LLM/AI assistant process names.

        Returns:
            List of LLM process names (default: claude, codex, gemini, etc.).
        """
        names = self._process_yaml.get("llm_processes")
        if isinstance(names, list):
            return [str(n).lower() for n in names if str(n).strip()]
        return list(DEFAULT_LLM_NAMES)

    @cached_property
    def edison_processes(self) -> List[str]:
        """Get list of Edison process patterns.

        Returns:
            List of Edison process names (default: edison, python).
        """
        names = self._process_yaml.get("edison_processes")
        if isinstance(names, list):
            return [str(n).lower() for n in names if str(n).strip()]
        return list(DEFAULT_EDISON_NAMES)

    @cached_property
    def edison_script_markers(self) -> List[str]:
        """Get list of command-line markers that indicate Edison scripts.

        Returns:
            List of script markers to check in command lines.
        """
        markers = self._process_yaml.get("edison_script_markers")
        if isinstance(markers, list):
            return [str(m).lower() for m in markers if str(m).strip()]
        return list(DEFAULT_EDISON_MARKERS)

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
    "DEFAULT_EDISON_MARKERS",
]
