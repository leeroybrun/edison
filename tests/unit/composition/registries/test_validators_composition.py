"""Test ValidatorRegistry composition features.

ValidatorRegistry should extend ComposableRegistry[str] to enable
file-based composition like AgentRegistry, while keeping config-based roster.
"""
from pathlib import Path
import pytest
import tempfile

from edison.core.composition.registries.validators import ValidatorRegistry


class TestValidatorComposition:
    """Test validator composition from markdown files."""

    def test_validator_registry_extends_composable_registry(self):
        """ValidatorRegistry should extend ComposableRegistry."""
        registry = ValidatorRegistry()

        # Should have content_type defined
        assert hasattr(registry, 'content_type')
        assert registry.content_type == "validators"

        # Should have file_pattern defined
        assert hasattr(registry, 'file_pattern')
        assert registry.file_pattern == "*.md"

    def test_compose_validator_returns_string(self):
        """compose_validator() should compose validator prompt from real bundled data."""
        # Use real bundled data - global validator exists
        registry = ValidatorRegistry()

        # Compose the global validator (it exists in src/edison/data/validators/global/)
        result = registry.compose_validator("global")

        # Assertions
        assert result is not None
        assert isinstance(result, str)
        assert "# Global Validator" in result
        assert "Validation" in result

    def test_compose_validator_with_pack_overlay(self):
        """compose_validator() should compose with pack overlays."""
        # Use real bundled data - security validator exists in core
        registry = ValidatorRegistry()

        # Compose security validator (exists in src/edison/data/validators/critical/)
        # Using python pack which may have overlays
        result = registry.compose_validator("security", packs=["python"])

        # Should contain core security content
        assert result is not None
        assert isinstance(result, str)
        assert "Security" in result

    def test_compose_validator_returns_none_for_nonexistent(self):
        """compose_validator() should return None for non-existent validator."""
        registry = ValidatorRegistry()

        # Try to compose a validator that doesn't exist
        result = registry.compose_validator("this-validator-does-not-exist")

        assert result is None

    def test_validator_registry_keeps_config_based_roster_methods(self):
        """ValidatorRegistry should keep existing config-based roster methods."""
        registry = ValidatorRegistry()

        # These config-based methods should still exist and work
        assert hasattr(registry, 'get_all_grouped')
        assert hasattr(registry, 'list_names')
        assert hasattr(registry, 'exists')
        assert hasattr(registry, 'get')

        # They should work with config (not files)
        grouped = registry.get_all_grouped()
        assert isinstance(grouped, dict)
        assert 'global' in grouped or 'critical' in grouped or 'specialized' in grouped


class TestValidatorRegistryStrategy:
    """Test ValidatorRegistry composition strategy configuration."""

    def test_validator_strategy_config(self):
        """ValidatorRegistry should have correct strategy config."""
        registry = ValidatorRegistry()

        config = registry.get_strategy_config()

        # Validators should use sections but NO deduplication
        assert config['enable_sections'] is True
        assert config['enable_dedupe'] is False
        assert config['enable_template_processing'] is True
