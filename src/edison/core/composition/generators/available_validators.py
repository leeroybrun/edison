"""Validator roster generator.

Generates AVAILABLE_VALIDATORS.md from ValidatorRegistry data.
Uses ComposableRegistry with context_vars for {{#each}} expansion.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

from ..registries._base import ComposableRegistry


def _utc_timestamp() -> str:
    """Generate UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


class ValidatorRosterGenerator(ComposableRegistry[str]):
    """Generator for AVAILABLE_VALIDATORS.md.

    Uses ComposableRegistry composition with validator data
    via context_vars for {{#each}} expansion.

    Template: data/generators/AVAILABLE_VALIDATORS.md
    Output: _generated/AVAILABLE_VALIDATORS.md
    """

    content_type: ClassVar[str] = "generators"
    file_pattern: ClassVar[str] = "AVAILABLE_VALIDATORS.md"

    def get_context_vars(self, name: str, packs: list[str]) -> dict[str, Any]:
        """Provide validator data for template expansion."""
        from dataclasses import asdict

        from edison.core.config.domains.qa import QAConfig
        from edison.core.registries.validators import ValidatorRegistry

        registry = ValidatorRegistry(project_root=self.project_root)
        validators_by_wave = registry.get_all_grouped()
        qa_config = QAConfig()
        waves = qa_config.get_waves()
        engines = qa_config.get_engines()

        # Convert ValidatorMetadata dataclasses to dicts
        def convert_validators(validators):
            return [asdict(v) for v in validators]

        # Get wave names
        wave_names = [w.get("name", "") for w in waves]

        # Build context for wave-based structure
        context: dict[str, Any] = {
            # Wave-based structure
            "waves": waves,
            "wave_names": wave_names,
            "validators_by_wave": {
                wave: convert_validators(validators_by_wave.get(wave, []))
                for wave in wave_names
            },
            # Engine information
            "engines": engines,
            "engine_names": list(engines.keys()),
            # All validators flat list
            "all_validators": convert_validators(registry.get_all()),
            # Metadata
            "generated_at": _utc_timestamp(),
        }

        # Provide named accessors for templates using {{#each <wave>_validators}}
        for wave in wave_names:
            context[f"{wave}_validators"] = convert_validators(validators_by_wave.get(wave, []))

        return context

    def write(self, output_dir: Path) -> Path:
        """Compose and write AVAILABLE_VALIDATORS.md.

        Args:
            output_dir: Directory for output file

        Returns:
            Path to written file
        """
        packs = self.get_active_packs()
        content = self.compose("AVAILABLE_VALIDATORS", packs)

        if not content:
            raise FileNotFoundError(
                f"Template 'AVAILABLE_VALIDATORS.md' not found in {self.content_type}/"
            )

        output_path = output_dir / "AVAILABLE_VALIDATORS.md"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.writer.write_text(output_path, content)
        return output_path


__all__ = ["ValidatorRosterGenerator"]
