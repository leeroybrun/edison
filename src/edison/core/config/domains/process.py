"""Domain-specific configuration for process detection.

Provides cached access to process detection patterns including LLM processes,
Edison processes, and script markers for session ID inference.
"""
from __future__ import annotations

from functools import cached_property

from ..base import BaseDomainConfig

# Default values as fallbacks (kept small; config expands these as needed)
DEFAULT_LLM_NAMES = ["claude", "codex", "gemini", "cursor", "aider", "happy", "opencode"]
DEFAULT_EDISON_NAMES = ["edison", "python"]
DEFAULT_LLM_SCRIPT_MARKERS = ["happy", "claude", "codex", "cursor", "gemini", "aider", "opencode"]
DEFAULT_LLM_MARKER_MAP = {
    "happy": "happy",
    "claude": "claude",
    "codex": "codex",
    "cursor": "cursor",
    "gemini": "gemini",
    "aider": "aider",
    "opencode": "opencode",
}
DEFAULT_LLM_CMDLINE_EXCLUDES: dict[str, list[str]] = {}


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
    def llm_processes(self) -> list[str]:
        """Get list of known LLM/AI assistant process names.

        Returns:
            List of LLM process names (default: claude, codex, gemini, etc.).
        """
        names = self.section.get("llm_processes")
        if names is None:
            llm_section = self.section.get("llm")
            if isinstance(llm_section, dict):
                names = llm_section.get("processNames") or llm_section.get("process_names")
        if isinstance(names, list):
            return [str(n).lower() for n in names if str(n).strip()]
        return list(DEFAULT_LLM_NAMES)

    @cached_property
    def llm_script_markers(self) -> list[str]:
        """Get cmdline markers used to detect wrapper CLIs with generic process names.

        Returns:
            List of lowercase marker substrings to match against the full cmdline.
        """
        markers = self.section.get("llm_script_markers")
        if markers is None:
            llm_section = self.section.get("llm")
            if isinstance(llm_section, dict):
                markers = llm_section.get("scriptMarkers") or llm_section.get("script_markers")
        if isinstance(markers, list):
            return [str(m).strip().lower() for m in markers if str(m).strip()]
        return list(DEFAULT_LLM_SCRIPT_MARKERS)

    @cached_property
    def llm_marker_map(self) -> dict[str, str]:
        """Get marker -> canonical wrapper name mapping.

        Returns:
            Dict mapping lowercase marker keys to lowercase canonical wrapper names.
        """
        raw = self.section.get("llm_marker_map")
        if raw is None:
            llm_section = self.section.get("llm")
            if isinstance(llm_section, dict):
                raw = llm_section.get("markerMap") or llm_section.get("marker_map")
        if isinstance(raw, dict):
            out: dict[str, str] = {}
            for k, v in raw.items():
                key = str(k).strip().lower()
                val = str(v).strip().lower()
                if key and val:
                    out[key] = val
            if out:
                return out
        return dict(DEFAULT_LLM_MARKER_MAP)

    @cached_property
    def llm_cmdline_excludes(self) -> dict[str, list[str]]:
        """Get wrapper-specific cmdline substrings to exclude from LLM detection.

        Returns:
            Dict mapping canonical wrapper name -> list of cmdline substrings. If any
            substring matches the full cmdline, that process is NOT treated as an LLM wrapper.
        """
        raw = self.section.get("llm_cmdline_excludes")
        if not isinstance(raw, dict):
            return dict(DEFAULT_LLM_CMDLINE_EXCLUDES)

        out: dict[str, list[str]] = {}
        for k, v in raw.items():
            key = str(k).strip().lower()
            if not key:
                continue
            if isinstance(v, list):
                patterns = [str(p).strip().lower() for p in v if str(p).strip()]
            else:
                patterns = []
            if patterns:
                out[key] = patterns
        return out or dict(DEFAULT_LLM_CMDLINE_EXCLUDES)

    @cached_property
    def edison_processes(self) -> list[str]:
        """Get list of Edison process patterns.

        Returns:
            List of Edison process names (default: edison, python).
        """
        names = self.section.get("edison_processes")
        if isinstance(names, list):
            return [str(n).lower() for n in names if str(n).strip()]
        return list(DEFAULT_EDISON_NAMES)

    @cached_property
    def edison_script_markers(self) -> list[str]:
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

    def get_llm_processes(self) -> list[str]:
        """Get list of known LLM/AI assistant process names."""
        return self.llm_processes

    def get_llm_script_markers(self) -> list[str]:
        """Get cmdline markers used to detect wrapper CLIs."""
        return self.llm_script_markers

    def get_llm_marker_map(self) -> dict[str, str]:
        """Get marker -> canonical wrapper name mapping."""
        return self.llm_marker_map

    def get_llm_cmdline_excludes(self) -> dict[str, list[str]]:
        """Get wrapper-specific cmdline substrings to exclude from LLM detection."""
        return self.llm_cmdline_excludes

    def get_edison_processes(self) -> list[str]:
        """Get list of Edison process patterns."""
        return self.edison_processes

    def get_edison_script_markers(self) -> list[str]:
        """Get list of command-line markers that indicate Edison scripts."""
        return self.edison_script_markers


__all__ = [
    "ProcessConfig",
    "DEFAULT_LLM_NAMES",
    "DEFAULT_EDISON_NAMES",
    "DEFAULT_LLM_SCRIPT_MARKERS",
    "DEFAULT_LLM_MARKER_MAP",
    "DEFAULT_LLM_CMDLINE_EXCLUDES",
]
