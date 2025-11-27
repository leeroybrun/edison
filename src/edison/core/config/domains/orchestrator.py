"""Domain-specific configuration for orchestrators.

Provides access to orchestrator configuration with schema validation and templating.
"""
from __future__ import annotations

import copy
import random
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from jsonschema import ValidationError

from ..base import BaseDomainConfig
from ..manager import ConfigManager
from edison.core.utils.time import utc_timestamp


class _SafeDict(dict):
    """dict that preserves unknown placeholders instead of raising."""

    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive
        return "{" + key + "}"


class OrchestratorConfig(BaseDomainConfig):
    """Access orchestrator configuration with schema validation and templating.

    Extends BaseDomainConfig for consistent caching and repo_root handling.
    """

    def __init__(self, repo_root: Optional[Path] = None, *, validate: bool = True) -> None:
        super().__init__(repo_root=repo_root)
        self._orchestrator_config = self._config.get("orchestrators", {}) or {}

        if not self._orchestrator_config:
            raise ValueError("Missing orchestrators configuration")

        if validate:
            self.validate()

    def _config_section(self) -> str:
        return "orchestrators"

    # --- Public API -----------------------------------------------------
    def get_default_profile_name(self) -> str:
        default = self._orchestrator_config.get("default")
        if default:
            return str(default)
        profiles = self.list_profiles()
        if not profiles:
            raise ValueError("No orchestrator profiles configured")
        return profiles[0]

    def list_profiles(self) -> list[str]:
        profiles = self._orchestrator_config.get("profiles", {})
        if isinstance(profiles, dict):
            return list(profiles.keys())
        return []

    def get_profile(
        self,
        name: Optional[str] = None,
        *,
        context: Optional[Mapping[str, Any]] = None,
        expand: bool = False,
    ) -> Dict[str, Any]:
        profiles = self._orchestrator_config.get("profiles", {}) or {}
        if not isinstance(profiles, dict):
            raise ValueError("Invalid orchestrator profiles configuration")

        target = name or self.get_default_profile_name()
        if target not in profiles:
            raise KeyError(f"Unknown orchestrator profile '{target}'")

        profile = copy.deepcopy(profiles[target])
        if expand:
            tokens = self._build_tokens(context or {})
            profile = self._expand(profile, tokens)
        return profile

    def validate(self) -> None:
        """Validate orchestrator config against schema and self-checks."""
        mgr = ConfigManager(self._repo_root)
        mgr.validate_schema(
            self._orchestrator_config, "config/orchestrator-config.schema.json"
        )

        default = self._orchestrator_config.get("default")
        profiles = self._orchestrator_config.get("profiles", {})
        if not isinstance(profiles, dict) or not profiles:
            raise ValidationError("orchestrators.profiles must be a non-empty object")

        for name, profile in profiles.items():
            if not isinstance(profile, dict):
                raise ValidationError(f"Profile '{name}' must be an object")
            if not profile.get("command"):
                raise ValidationError(f"Profile '{name}' is missing required 'command'")

            initial = profile.get("initial_prompt")
            if isinstance(initial, dict):
                method = initial.get("method")
                if method is not None:
                    allowed_methods = {"stdin", "file", "arg", "env"}
                    if method not in allowed_methods:
                        raise ValidationError(
                            f"Profile '{name}' initial_prompt.method must be one of {sorted(allowed_methods)}"
                        )

        if default and isinstance(profiles, dict) and default not in profiles:
            raise ValueError(f"Default orchestrator '{default}' not found in profiles")

    # --- Internal helpers -----------------------------------------------
    def _build_tokens(self, context: Mapping[str, Any]) -> Dict[str, str]:
        tokens: Dict[str, Any] = {
            "project_root": context.get("project_root") or str(self.repo_root),
            "session_worktree": context.get("session_worktree"),
            "session_id": context.get("session_id"),
            "timestamp": context.get("timestamp"),
            "shortid": context.get("shortid"),
        }

        if not tokens.get("timestamp"):
            tokens["timestamp"] = utc_timestamp()

        if not tokens.get("shortid"):
            tokens["shortid"] = self._generate_shortid()

        # Drop None values so placeholders remain untouched when missing
        return {k: str(v) for k, v in tokens.items() if v is not None}

    def _expand(self, value: Any, tokens: Mapping[str, str]) -> Any:
        if isinstance(value, str):
            return value.format_map(_SafeDict(tokens))
        if isinstance(value, list):
            return [self._expand(v, tokens) for v in value]
        if isinstance(value, dict):
            return {k: self._expand(v, tokens) for k, v in value.items()}
        return value

    def _generate_shortid(self, length: int = 6) -> str:
        alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
        return "".join(random.choice(alphabet) for _ in range(length))


__all__ = ["OrchestratorConfig"]



