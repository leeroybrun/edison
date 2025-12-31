"""Preset inference from changed files.

Infers the appropriate validation preset based on file patterns.
Uses deterministic rules to ensure reproducible preset selection.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Literal

from edison.core.qa.policy.config import PresetConfigLoader


@dataclass(frozen=True, slots=True)
class PresetInferenceResult:
    """Result of preset inference.

    Attributes:
        preset_name: Name of the inferred preset
        matched_patterns: Patterns that matched the changed files
        confidence: Confidence level of the inference
        was_escalated: Whether the preset was escalated from initial inference
        escalation_reason: Reason for escalation if applicable
    """

    preset_name: str
    matched_patterns: list[str] = field(default_factory=list)
    confidence: Literal["high", "medium", "low"] = "medium"
    was_escalated: bool = False
    escalation_reason: str = ""


# Preset priority order (higher index = higher priority/strictness)
PRESET_PRIORITY: dict[str, int] = {
    "quick": 0,
    "standard": 1,
    "strict": 2,
}

# Default file pattern rules for preset inference
# These are used if no custom rules are configured
DEFAULT_INFERENCE_RULES: list[dict[str, object]] = [
    # Docs-only patterns -> quick preset
    {
        "patterns": ["docs/**", "*.md", "**/*.md", "LICENSE", "LICENSE.*"],
        "preset": "quick",
        "priority": 10,
    },
    # Config/CI patterns -> standard preset
    {
        "patterns": [
            "pyproject.toml",
            "package.json",
            "*.yaml",
            "*.yml",
            ".github/**",
            "Makefile",
            "Dockerfile",
            "docker-compose*.yml",
        ],
        "preset": "standard",
        "priority": 20,
    },
    # Source code patterns -> standard preset
    {
        "patterns": [
            "src/**",
            "lib/**",
            "app/**",
            "apps/**",
            "packages/**",
            "*.py",
            "*.ts",
            "*.tsx",
            "*.js",
            "*.jsx",
            "*.go",
            "*.rs",
        ],
        "preset": "standard",
        "priority": 30,
    },
    # Test patterns -> standard preset
    {
        "patterns": ["tests/**", "test/**", "**/*_test.*", "**/*.test.*", "**/*.spec.*"],
        "preset": "standard",
        "priority": 25,
    },
]


class PresetInference:
    """Infers validation preset from changed files.

    Uses deterministic pattern matching rules to select the appropriate
    validation preset based on which files were changed.

    The inference follows these principles:
    1. Match files against configured patterns
    2. Select the highest-priority matching preset
    3. Escalate if mixed patterns require stricter validation

    Example:
        inference = PresetInference()
        result = inference.infer_preset(["docs/README.md"])
        # result.preset_name == "quick"

        result = inference.infer_preset(["src/app.py"])
        # result.preset_name == "standard"
    """

    def __init__(self, project_root: Optional[Path] = None) -> None:
        """Initialize preset inference.

        Args:
            project_root: Optional project root path. Auto-detected if not provided.
        """
        self._project_root = project_root
        self._config_loader: Optional[PresetConfigLoader] = None

    @property
    def project_root(self) -> Path:
        """Get project root, resolving lazily if needed."""
        if self._project_root is None:
            from edison.core.utils.paths import PathResolver
            self._project_root = PathResolver.resolve_project_root()
        return self._project_root

    @property
    def config_loader(self) -> PresetConfigLoader:
        """Get config loader (lazy init)."""
        if self._config_loader is None:
            self._config_loader = PresetConfigLoader(project_root=self.project_root)
        return self._config_loader

    def infer_preset(self, changed_files: list[str]) -> PresetInferenceResult:
        """Infer the appropriate preset from changed files.

        Args:
            changed_files: List of file paths that were changed

        Returns:
            PresetInferenceResult with the inferred preset and metadata
        """
        if not changed_files:
            # No files changed - use minimal validation
            return PresetInferenceResult(
                preset_name="quick",
                confidence="high",
            )

        # Load custom rules or use defaults
        rules = self.config_loader.load_inference_rules()
        if not rules:
            rules = DEFAULT_INFERENCE_RULES

        # Match files against rules
        matches: list[tuple[str, int, list[str]]] = []  # (preset, priority, patterns)

        for rule in rules:
            patterns = rule.get("patterns", [])
            if isinstance(patterns, str):
                patterns = [patterns]
            if not isinstance(patterns, list):
                continue

            preset = str(rule.get("preset", "standard"))
            priority = int(rule.get("priority", 0))

            matched_patterns = self._match_files(changed_files, patterns)
            if matched_patterns:
                matches.append((preset, priority, matched_patterns))

        if not matches:
            # No patterns matched - default to standard
            return PresetInferenceResult(
                preset_name="standard",
                confidence="low",
            )

        # Find the highest priority match
        matches.sort(key=lambda x: x[1], reverse=True)
        highest_preset, _, highest_patterns = matches[0]

        # Check for escalation (if lower-priority preset was matched too)
        initial_preset = None
        was_escalated = False
        escalation_reason = ""

        for preset, priority, _ in matches:
            preset_prio = PRESET_PRIORITY.get(preset, 1)
            if initial_preset is None:
                initial_preset = preset
            elif PRESET_PRIORITY.get(highest_preset, 1) > PRESET_PRIORITY.get(preset, 1):
                # Higher preset overrides lower - this is escalation
                if not was_escalated:
                    was_escalated = True
                    escalation_reason = f"Escalated from {preset} due to {highest_preset} patterns"

        # Determine final preset (highest strictness wins)
        final_preset = highest_preset
        for preset, _, _ in matches:
            if PRESET_PRIORITY.get(preset, 1) > PRESET_PRIORITY.get(final_preset, 1):
                final_preset = preset
                was_escalated = True
                escalation_reason = f"Escalated to {final_preset} due to mixed file types"

        # Determine confidence
        confidence: Literal["high", "medium", "low"]
        if len(matches) == 1:
            confidence = "high"
        elif len(matches) == 2:
            confidence = "medium"
        else:
            confidence = "low"

        return PresetInferenceResult(
            preset_name=final_preset,
            matched_patterns=highest_patterns,
            confidence=confidence,
            was_escalated=was_escalated,
            escalation_reason=escalation_reason,
        )

    def _match_files(self, files: list[str], patterns: list[str]) -> list[str]:
        """Match files against patterns.

        Args:
            files: List of file paths
            patterns: List of glob patterns

        Returns:
            List of patterns that matched at least one file
        """
        from edison.core.utils.patterns import matches_any_pattern

        matched: list[str] = []
        for pattern in patterns:
            for file_path in files:
                if matches_any_pattern(file_path, [pattern]):
                    if pattern not in matched:
                        matched.append(pattern)
                    break

        return matched


__all__ = ["PresetInference", "PresetInferenceResult"]
