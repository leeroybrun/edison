"""Tests for Gemini support in Edison composition."""
from __future__ import annotations

from pathlib import Path

from edison.core.composition import CompositionEngine
from edison.core.paths.project import get_project_config_dir
from edison.core.config import ConfigManager

# For tests that need a repo root reference
ROOT = Path(__file__).resolve().parent.parent.parent.parent


class TestGeminiSupport:
    def test_gemini_global_in_validation_roster(self) -> None:
        """gemini-global must be present in validation.roster.global."""
        cfg = ConfigManager(repo_root=ROOT).load_config(validate=False)
        global_validators = (cfg.get("validation", {}) or {}).get("roster", {}).get("global", []) or []

        gemini_validator = next(
            (v for v in global_validators if v.get("id") == "gemini-global"),
            None,
        )

        assert gemini_validator is not None, (
            "gemini-global must be in validation.roster.global. "
            f"Found validators: {[v.get('id') for v in global_validators]}"
        )

    def test_gemini_role_in_zen_composition(self) -> None:
        """Zen composition must support gemini role."""
        cfg = ConfigManager(repo_root=ROOT).load_config(validate=False)
        zen_cfg = cfg.get("zen", {}) or {}
        roles = zen_cfg.get("roles", [])

        assert "gemini" in roles, (
            f"gemini must be in zen.roles. Found roles: {roles}"
        )
