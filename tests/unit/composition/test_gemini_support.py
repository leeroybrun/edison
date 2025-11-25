"""Tests for Gemini support in Edison composition."""
from __future__ import annotations

from edison.data import read_yaml


class TestGeminiSupport:
    def test_gemini_global_in_validation_roster(self) -> None:
        """gemini-global must be present in validation.roster.global."""
        # Read validators config directly from data
        validators_cfg = read_yaml("config", "validators.yaml")
        global_validators = validators_cfg.get("validation", {}).get("roster", {}).get("global", []) or []

        gemini_validator = next(
            (v for v in global_validators if v.get("id") == "gemini-global"),
            None,
        )

        assert gemini_validator is not None, (
            "gemini-global must be in validation.roster.global. "
            f"Found validators: {[v.get('id') for v in global_validators]}"
        )

    def test_gemini_role_in_zen_composition(self) -> None:
        """Zen composition must support gemini model."""
        # Check if models config defines gemini
        models_cfg = read_yaml("config", "models.yaml")

        # Gemini is defined under delegation.models
        models = models_cfg.get("delegation", {}).get("models", {})

        # Check if gemini model exists
        assert "gemini" in models, (
            f"gemini must be in delegation.models. Found models: {list(models.keys())}"
        )
