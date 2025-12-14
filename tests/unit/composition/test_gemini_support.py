"""Tests for Gemini support in Edison composition."""
from __future__ import annotations

from edison.data import read_yaml


class TestGeminiSupport:
    def test_gemini_global_in_validation_roster(self) -> None:
        """global-gemini must be present in validation.validators (config-driven roster)."""
        # Read validators config directly from data
        validators_cfg = read_yaml("config", "validators.yaml")
        validators = validators_cfg.get("validation", {}).get("validators", {}) or {}
        assert "global-gemini" in validators, (
            "global-gemini must be defined in validation.validators. "
            f"Found validators: {list(validators.keys())}"
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
