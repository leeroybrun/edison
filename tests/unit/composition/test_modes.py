"""Tests for composition modes.

TDD: RED - Write failing tests first, then implement.
Tests the CompositionMode enum and mode-specific composers.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from typing import Dict, List


class TestCompositionMode:
    """Tests for CompositionMode enum."""
    
    def test_composition_mode_section_exists(self) -> None:
        """SECTION mode should exist for section-based composition."""
        from edison.core.composition.core.modes import CompositionMode
        
        assert hasattr(CompositionMode, "SECTION")
        assert CompositionMode.SECTION.value == "section"
    
    def test_composition_mode_concatenate_exists(self) -> None:
        """CONCATENATE mode should exist for paragraph-based composition."""
        from edison.core.composition.core.modes import CompositionMode
        
        assert hasattr(CompositionMode, "CONCATENATE")
        assert CompositionMode.CONCATENATE.value == "concatenate"
    
    def test_composition_mode_yaml_merge_exists(self) -> None:
        """YAML_MERGE mode should exist for YAML-based merging."""
        from edison.core.composition.core.modes import CompositionMode
        
        assert hasattr(CompositionMode, "YAML_MERGE")
        assert CompositionMode.YAML_MERGE.value == "yaml_merge"
    
    def test_default_mode_is_section(self) -> None:
        """Default mode should be SECTION."""
        from edison.core.composition.core.modes import CompositionMode, DEFAULT_MODE
        
        assert DEFAULT_MODE == CompositionMode.SECTION


class TestConcatenateComposer:
    """Tests for ConcatenateComposer (guideline-style composition)."""
    
    def test_concatenate_composer_merges_layers(self) -> None:
        """Concatenate composer should merge core + pack + project layers."""
        from edison.core.composition.core.modes import ConcatenateComposer
        
        composer = ConcatenateComposer()
        
        core_text = "# Core Guideline\n\nCore paragraph one.\n\nCore paragraph two."
        pack_texts = {"react": "React specific paragraph."}
        project_text = "Project-specific additions."
        
        result = composer.compose(
            core_text=core_text,
            pack_texts=pack_texts,
            project_text=project_text,
        )
        
        # All content should be present
        assert "Core Guideline" in result
        assert "Core paragraph one" in result
        assert "React specific paragraph" in result
        assert "Project-specific additions" in result
    
    def test_concatenate_composer_deduplicates_paragraphs(self) -> None:
        """Concatenate composer should deduplicate identical paragraphs."""
        from edison.core.composition.core.modes import ConcatenateComposer
        
        composer = ConcatenateComposer(shingle_size=12, min_shingles=1)
        
        # Repeated text (12+ words to trigger shingle detection)
        repeated = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu paragraph content"
        
        core_text = f"# Core\n\n{repeated}"
        pack_texts = {"react": repeated}  # Duplicate
        project_text = ""
        
        result = composer.compose(
            core_text=core_text,
            pack_texts=pack_texts,
            project_text=project_text,
        )
        
        # The duplicate should be removed from packs (project priority > packs > core)
        # So core keeps it, pack's duplicate is removed
        count = result.count("alpha beta gamma delta")
        assert count == 1, f"Duplicate paragraph should be removed, found {count} occurrences"
    
    def test_concatenate_composer_respects_priority_order(self) -> None:
        """Project > Packs > Core priority for deduplication."""
        from edison.core.composition.core.modes import ConcatenateComposer
        
        composer = ConcatenateComposer(shingle_size=12, min_shingles=1)
        
        # Same content in all layers
        repeated = "shared content alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu"
        
        core_text = f"Core header.\n\n{repeated}"
        pack_texts = {"react": f"React header.\n\n{repeated}"}
        project_text = f"Project header.\n\n{repeated}"
        
        result = composer.compose(
            core_text=core_text,
            pack_texts=pack_texts,
            project_text=project_text,
        )
        
        # All headers should be present
        assert "Core header" in result
        assert "React header" in result
        assert "Project header" in result
        
        # Shared content should appear only once
        count = result.count("shared content alpha beta")
        assert count == 1, f"Shared content should appear once, found {count}"
    
    def test_concatenate_composer_handles_empty_layers(self) -> None:
        """Concatenate composer should handle empty layers gracefully."""
        from edison.core.composition.core.modes import ConcatenateComposer
        
        composer = ConcatenateComposer()
        
        result = composer.compose(
            core_text="Core only content.",
            pack_texts={},
            project_text="",
        )
        
        assert "Core only content" in result
        assert result.strip()  # Should not be empty
    
    def test_concatenate_composer_from_config(self, tmp_path) -> None:
        """ConcatenateComposer.from_config should read from config dict."""
        from edison.core.composition.core.modes import ConcatenateComposer
        
        config = {
            "composition": {
                "dryDetection": {
                    "shingleSize": 8,
                    "minShingles": 5,
                }
            }
        }
        
        composer = ConcatenateComposer.from_config(config)
        
        assert composer.shingle_size == 8
        assert composer.min_shingles == 5
    
    def test_concatenate_composer_from_config_uses_defaults(self) -> None:
        """ConcatenateComposer.from_config should use defaults for missing values."""
        from edison.core.composition.core.modes import ConcatenateComposer
        
        config = {"composition": {}}  # No dryDetection
        
        composer = ConcatenateComposer.from_config(config)
        
        assert composer.shingle_size == 12  # Default
        assert composer.min_shingles == 3   # Default


class TestModeDispatcher:
    """Tests for mode-based composition dispatch."""
    
    def test_get_composer_for_section_mode(self) -> None:
        """get_composer should return SectionComposer for SECTION mode."""
        from edison.core.composition.core.modes import CompositionMode, get_composer
        from edison.core.composition.core.sections import SectionComposer
        
        composer = get_composer(CompositionMode.SECTION)
        assert isinstance(composer, SectionComposer)
    
    def test_get_composer_for_concatenate_mode(self) -> None:
        """get_composer should return ConcatenateComposer for CONCATENATE mode."""
        from edison.core.composition.core.modes import CompositionMode, get_composer, ConcatenateComposer
        
        composer = get_composer(CompositionMode.CONCATENATE)
        assert isinstance(composer, ConcatenateComposer)
    
    def test_get_mode_from_string(self) -> None:
        """get_mode should parse string to CompositionMode."""
        from edison.core.composition.core.modes import CompositionMode, get_mode
        
        assert get_mode("section") == CompositionMode.SECTION
        assert get_mode("concatenate") == CompositionMode.CONCATENATE
        assert get_mode("yaml_merge") == CompositionMode.YAML_MERGE
    
    def test_get_mode_returns_default_for_none(self) -> None:
        """get_mode should return DEFAULT_MODE for None."""
        from edison.core.composition.core.modes import get_mode, DEFAULT_MODE
        
        assert get_mode(None) == DEFAULT_MODE
    
    def test_get_mode_returns_default_for_unknown(self) -> None:
        """get_mode should return DEFAULT_MODE for unknown strings."""
        from edison.core.composition.core.modes import get_mode, DEFAULT_MODE
        
        assert get_mode("unknown_mode") == DEFAULT_MODE
