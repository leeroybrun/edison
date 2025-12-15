"""
Test Motion Pack (framer-motion/motion) structure and content.

STRICT TDD: RED -> GREEN -> REFACTOR
This test validates that the Motion pack is complete with:
1. pack.yml manifest
2. agents/overlays/ directory with animation-specific guidance
3. validators/overlays/ directory with animation validation
4. rules/ directory with motion-specific rules
5. guidelines/ directory with motion patterns and best practices
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

_cur = Path(__file__).resolve()
ROOT = None
for i in range(1, 10):
    if i >= len(_cur.parents):
        break
    cand = _cur.parents[i]
    if (cand / '.git').exists():
        ROOT = cand
        break
assert ROOT is not None, 'cannot locate repository root (.git)'

from edison.core.composition.packs import (
    validate_pack,
)


class TestMotionPackStructure:
    """Test Motion pack directory structure and manifest."""

    @pytest.fixture
    def motion_pack_dir(self) -> Path:
        """Get path to motion pack directory."""
        return ROOT / 'src/edison/data/packs/motion'

    def test_motion_pack_directory_exists(self, motion_pack_dir: Path):
        """Motion pack directory should exist."""
        assert motion_pack_dir.exists(), f"Motion pack directory not found at {motion_pack_dir}"
        assert motion_pack_dir.is_dir(), f"Motion pack path is not a directory: {motion_pack_dir}"

    def test_motion_pack_manifest_exists(self, motion_pack_dir: Path):
        """Motion pack must have pack.yml manifest."""
        pack_yml = motion_pack_dir / 'pack.yml'
        assert pack_yml.exists(), f"Motion pack manifest not found at {pack_yml}"

    def test_motion_pack_validates_ok(self, motion_pack_dir: Path):
        """Motion pack should validate with no errors."""
        res = validate_pack(motion_pack_dir)
        assert res.ok, f"Motion pack validation failed: {[i.message for i in res.issues]}"

    def test_motion_pack_has_validators_directory(self, motion_pack_dir: Path):
        """Motion pack must have validators directory."""
        validators_dir = motion_pack_dir / 'validators'
        assert validators_dir.exists(), f"validators directory not found at {validators_dir}"
        assert validators_dir.is_dir(), f"validators path is not a directory: {validators_dir}"

    def test_motion_pack_has_validators_overlay(self, motion_pack_dir: Path):
        """Motion pack must have validators/overlays/ directory with global.md."""
        overlays_dir = motion_pack_dir / 'validators' / 'overlays'
        assert overlays_dir.exists(), f"validators/overlays directory not found at {overlays_dir}"
        
        global_overlay = overlays_dir / 'global.md'
        assert global_overlay.exists(), f"validators/overlays/global.md not found at {global_overlay}"

    def test_motion_pack_has_agents_overlays(self, motion_pack_dir: Path):
        """Motion pack must have agents/overlays directory with guidance for component-builder."""
        agents_dir = motion_pack_dir / 'agents'
        assert agents_dir.exists(), f"agents directory not found at {agents_dir}"
        
        overlays_dir = agents_dir / 'overlays'
        assert overlays_dir.exists(), f"agents/overlays directory not found at {overlays_dir}"
        
        # Component builder overlay for animations in React components
        builder_overlay = overlays_dir / 'component-builder.md'
        assert builder_overlay.exists(), f"agents/overlays/component-builder.md not found at {builder_overlay}"

    def test_motion_pack_has_guidelines(self, motion_pack_dir: Path):
        """Motion pack must have guidelines directory with animation patterns."""
        guidelines_dir = motion_pack_dir / 'guidelines'
        assert guidelines_dir.exists(), f"guidelines directory not found at {guidelines_dir}"
        
        # Required guidelines
        required_guides = [
            'includes/motion/animate-presence.md',
            'includes/motion/layout-animations.md',
            'includes/motion/gesture-handling.md',
            'includes/motion/variants-system.md',
            'includes/motion/performance.md',
        ]
        
        for guide in required_guides:
            guide_path = guidelines_dir / guide
            assert guide_path.exists(), f"guideline not found at {guide_path}"

    def test_motion_pack_has_rules(self, motion_pack_dir: Path):
        """Motion pack must have rules directory with motion-specific validation rules."""
        rules_dir = motion_pack_dir / 'rules'
        assert rules_dir.exists(), f"rules directory not found at {rules_dir}"
        
        # Check for registry
        registry = rules_dir / 'registry.yml'
        assert registry.exists(), f"rules registry not found at {registry}"

    def test_motion_pack_manifest_content(self, motion_pack_dir: Path):
        """Motion pack manifest should have required fields and content."""
        pack_yml = motion_pack_dir / 'pack.yml'
        content = pack_yml.read_text(encoding='utf-8')
        
        # Check for essential fields
        assert 'name:' in content, "pack.yml should have name field"
        assert 'version:' in content, "pack.yml should have version field"
        assert 'description:' in content, "pack.yml should have description field"
        assert 'Motion' in content or 'motion' in content, "pack.yml should reference Motion/motion"
        assert 'framer-motion' in content.lower() or 'motion' in content, "pack.yml should reference framer-motion/motion"
        assert 'triggers:' in content, "pack.yml should have triggers section"
        assert 'filePatterns:' in content, "pack.yml should specify file patterns"

    def test_motion_pack_validators_overlay_content(self, motion_pack_dir: Path):
        """Motion pack validators overlay should have content."""
        overlay = motion_pack_dir / 'validators' / 'overlays' / 'global.md'
        content = overlay.read_text(encoding='utf-8')
        
        # Should reference motion patterns
        content_lower = content.lower()
        assert len(content) > 100, "Validators overlay should have substantial content"
        assert any(x in content_lower for x in ['animation', 'motion', 'animate', 'variant']), \
            "Validators overlay should reference animation patterns"

    def test_motion_pack_agents_overlay_content(self, motion_pack_dir: Path):
        """Motion pack component-builder overlay should guide animations in components."""
        overlay = motion_pack_dir / 'agents' / 'overlays' / 'component-builder.md'
        content = overlay.read_text(encoding='utf-8')
        
        content_lower = content.lower()
        assert len(content) > 100, "Agent overlay should have substantial content"
        assert any(x in content_lower for x in ['motion', 'animate', 'animation']), \
            "Agent overlay should reference motion/animation patterns"

    def test_motion_pack_guidelines_content(self, motion_pack_dir: Path):
        """Motion pack guidelines should have substantive content."""
        guidelines_dir = motion_pack_dir / 'guidelines' / 'includes' / 'motion'
        
        # Each guide should have content
        for guide_file in guidelines_dir.glob('*.md'):
            content = guide_file.read_text(encoding='utf-8')
            assert len(content) > 50, f"{guide_file.name} should have substantive content"
            assert '#' in content, f"{guide_file.name} should have markdown headers"

    def test_motion_pack_validators_motion_md_exists(self, motion_pack_dir: Path):
        """Motion pack must have validators/motion.md main validator."""
        motion_validator = motion_pack_dir / 'validators' / 'motion.md'
        assert motion_validator.exists(), f"validators/motion.md not found at {motion_validator}"
        
        content = motion_validator.read_text(encoding='utf-8')
        assert len(content) > 500, "motion.md validator should have substantial content"
        assert 'Motion' in content or 'motion' in content, "motion.md should reference Motion patterns"

    def test_motion_pack_rules_registry_content(self, motion_pack_dir: Path):
        """Motion pack rules registry should define validation rules."""
        registry = motion_pack_dir / 'rules' / 'registry.yml'
        content = registry.read_text(encoding='utf-8')
        
        content_lower = content.lower()
        assert 'rules:' in content, "rules registry should have rules section"
        assert any(x in content_lower for x in ['animate', 'motion', 'layout', 'gpu', 'gesture']), \
            "rules registry should define motion-specific rules"
