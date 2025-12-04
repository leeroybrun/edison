"""Validator roster generator.

Generates AVAILABLE_VALIDATORS.md from ValidatorRegistry data.
Uses ComposableRegistry with context_vars for {{#each}} expansion.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar, Dict, List

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
    
    def get_context_vars(self, name: str, packs: List[str]) -> Dict[str, Any]:
        """Provide validator data for template expansion."""
        from edison.core.registries.validators import ValidatorRegistry
        from dataclasses import asdict
        
        registry = ValidatorRegistry(project_root=self.project_root)
        validators_by_tier = registry.get_all_grouped()
        
        # Convert ValidatorMetadata dataclasses to dicts
        def convert_tier(validators):
            return [asdict(v) for v in validators]
        
        return {
            "global_validators": convert_tier(validators_by_tier.get("global", [])),
            "critical_validators": convert_tier(validators_by_tier.get("critical", [])),
            "specialized_validators": convert_tier(validators_by_tier.get("specialized", [])),
            "generated_at": _utc_timestamp(),
        }
    
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

