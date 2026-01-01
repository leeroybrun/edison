"""Domain-specific configuration for TDD enforcement.

This domain reads the top-level `tdd` config section.
"""
from __future__ import annotations

from functools import cached_property
from typing import Any, List

from ..base import BaseDomainConfig


class TDDConfig(BaseDomainConfig):
    def _config_section(self) -> str:
        return "tdd"

    @cached_property
    def enforce_red_green_refactor(self) -> bool:
        return bool(self.section.get("enforceRedGreenRefactor", True))

    @cached_property
    def require_evidence(self) -> bool:
        return bool(self.section.get("requireEvidence", True))

    @cached_property
    def hmac_validation(self) -> bool:
        # When true, HMAC must be present+valid (in addition to key env var being set).
        return bool(self.section.get("hmacValidation", False))

    @cached_property
    def test_file_globs(self) -> List[str]:
        raw = self.section.get("testFileGlobs", [])
        if not isinstance(raw, list):
            return []
        return [str(v).strip() for v in raw if str(v).strip()]

    @cached_property
    def blocked_test_tokens(self) -> List[str]:
        raw = self.section.get("blockedTestTokens", [])
        if not isinstance(raw, list):
            return []
        return [str(v) for v in raw if str(v)]

    @cached_property
    def verification_script(self) -> str | None:
        raw = self.section.get("verificationScript")
        s = str(raw).strip() if raw is not None else ""
        return s or None

    @cached_property
    def hmac_key_env_var(self) -> str:
        raw = self.section.get("hmacKeyEnvVar")
        s = str(raw).strip() if raw is not None else ""
        return s or "project_EVIDENCE_HMAC_KEY"


__all__ = ["TDDConfig"]

