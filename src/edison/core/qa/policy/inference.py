"""Preset inference from file context.

Infers the appropriate validation preset based on the files
changed in a task. Implements escalation rules:
- Docs-only changes -> quick preset
- Code changes -> standard or higher
- Config changes -> standard or higher
"""
from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from .config import PresetConfigLoader


class PresetInference:
    """Infers validation preset from file context.

    Analyzes changed files to determine the appropriate preset.
    Uses configurable patterns for escalation decisions.

    Example:
        inference = PresetInference(project_root=Path("/my/project"))
        preset_id = inference.infer_preset_from_files(["src/module.py"])
        # Returns "standard" because .py files are code
    """

    # Default patterns if not configured
    DEFAULT_DOC_PATTERNS: list[str] = [
        "*.md",
        "*.rst",
        "*.txt",
        "docs/*",
        "docs/**/*",
        "*.adoc",
        "CHANGELOG*",
        "README*",
        "LICENSE*",
        "AUTHORS*",
        "CONTRIBUTING*",
    ]

    DEFAULT_CODE_PATTERNS: list[str] = [
        "*.py",
        "*.ts",
        "*.tsx",
        "*.js",
        "*.jsx",
        "*.go",
        "*.rs",
        "*.java",
        "*.kt",
        "*.swift",
        "*.c",
        "*.cpp",
        "*.h",
        "*.hpp",
        "*.cs",
        "*.rb",
        "*.php",
    ]

    DEFAULT_CONFIG_PATTERNS: list[str] = [
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "package.json",
        "tsconfig.json",
        "*.yaml",
        "*.yml",
        "Makefile",
        "Dockerfile",
        "docker-compose*.yml",
        ".env*",
    ]

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize the inference engine.

        Args:
            project_root: Project root directory. Auto-detected if not provided.
        """
        self._project_root = project_root
        self._config_loader = PresetConfigLoader(project_root=project_root)

    def _get_escalation_patterns(self) -> dict[str, list[str]]:
        """Get escalation patterns from config or defaults."""
        escalation_cfg = self._config_loader.get_escalation_config()

        code_patterns = escalation_cfg.get("code_patterns")
        config_patterns = escalation_cfg.get("config_patterns")
        doc_patterns = escalation_cfg.get("doc_patterns")

        return {
            "code": code_patterns if isinstance(code_patterns, list) else self.DEFAULT_CODE_PATTERNS,
            "config": config_patterns if isinstance(config_patterns, list) else self.DEFAULT_CONFIG_PATTERNS,
            "doc": doc_patterns if isinstance(doc_patterns, list) else self.DEFAULT_DOC_PATTERNS,
        }

    def _matches_any_pattern(self, file_path: str, patterns: list[str]) -> bool:
        """Check if a file path matches any of the given patterns."""
        # Get just the filename and path components
        path = Path(file_path)
        filename = path.name

        for pattern in patterns:
            # Try matching against full path
            if fnmatch(file_path, pattern):
                return True
            # Try matching against just filename
            if fnmatch(filename, pattern):
                return True
            # Try matching path parts
            for part in path.parts:
                if fnmatch(part, pattern):
                    return True
        return False

    def classify_file(self, file_path: str) -> str:
        """Classify a file as 'doc', 'code', 'config', or 'other'.

        Args:
            file_path: Path to the file

        Returns:
            Classification string
        """
        patterns = self._get_escalation_patterns()

        # Check in order: doc, code, config (most specific first)
        if self._matches_any_pattern(file_path, patterns["doc"]):
            return "doc"
        if self._matches_any_pattern(file_path, patterns["code"]):
            return "code"
        if self._matches_any_pattern(file_path, patterns["config"]):
            return "config"
        return "other"

    def infer_preset_from_files(self, files: list[str]) -> str:
        """Infer the appropriate preset from a list of files.

        Rules:
        - If no files or all docs: "quick"
        - If any code or config files: "standard"
        - Otherwise: use default from config

        Args:
            files: List of file paths

        Returns:
            Preset ID (e.g., "quick", "standard")
        """
        if not files:
            # Empty file list - use default preset
            return self._config_loader.get_default_preset_id()

        classifications = [self.classify_file(f) for f in files]

        # Check for code or config files
        has_code = "code" in classifications
        has_config = "config" in classifications
        has_other = "other" in classifications

        # Escalation logic: code or config changes require standard validation
        if has_code or has_config or has_other:
            return "standard"

        # All files are docs - quick is sufficient
        return "quick"

    def should_escalate(self, current_preset: str, files: list[str]) -> tuple[bool, str | None]:
        """Determine if the current preset should be escalated.

        Args:
            current_preset: Current preset ID
            files: List of file paths

        Returns:
            Tuple of (should_escalate, reason)
        """
        if current_preset != "quick":
            # Only escalate from quick
            return False, None

        inferred = self.infer_preset_from_files(files)
        if inferred != "quick":
            return True, f"Code or config changes detected, escalating from {current_preset} to {inferred}"

        return False, None


__all__ = ["PresetInference"]
