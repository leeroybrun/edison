"""
TDD Test for better-auth Edison pack.
Verifies pack structure, required files, and pack validation.
"""
from __future__ import annotations

from pathlib import Path
import pytest
import sys

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


class TestBetterAuthPackStructure:
    """Test better-auth pack structure and required files."""

    @pytest.fixture
    def pack_dir(self) -> Path:
        """Get path to better-auth pack."""
        return Path('/Users/leeroy/Documents/Development/edison/src/edison/data/packs/better-auth')

    def test_pack_directory_exists(self, pack_dir: Path):
        """Pack directory must exist."""
        assert pack_dir.exists(), f"Pack directory {pack_dir} must exist"
        assert pack_dir.is_dir(), f"{pack_dir} must be a directory"

    def test_pack_yml_exists(self, pack_dir: Path):
        """pack.yml manifest must exist."""
        pack_yml = pack_dir / 'pack.yml'
        assert pack_yml.exists(), f"pack.yml must exist at {pack_yml}"

    def test_pack_yml_validates(self, pack_dir: Path):
        """pack.yml must validate against the canonical pack schema."""
        result = validate_pack(pack_dir)
        assert result.ok, f"Pack validation failed: {[i.message for i in result.issues]}"

    def test_agents_directory_exists(self, pack_dir: Path):
        """agents/ directory must exist."""
        agents_dir = pack_dir / 'agents'
        assert agents_dir.exists(), f"agents/ directory must exist at {agents_dir}"
        assert agents_dir.is_dir(), f"{agents_dir} must be a directory"

    def test_agents_overlays_directory_exists(self, pack_dir: Path):
        """agents/overlays/ directory must exist."""
        agents_overlays = pack_dir / 'agents' / 'overlays'
        assert agents_overlays.exists(), f"agents/overlays/ must exist at {agents_overlays}"
        assert agents_overlays.is_dir(), f"{agents_overlays} must be a directory"

    def test_agents_init_exists(self, pack_dir: Path):
        """agents/__init__.py must exist."""
        agents_init = pack_dir / 'agents' / '__init__.py'
        assert agents_init.exists(), f"agents/__init__.py must exist at {agents_init}"

    def test_validators_directory_exists(self, pack_dir: Path):
        """validators/ directory must exist."""
        validators_dir = pack_dir / 'validators'
        assert validators_dir.exists(), f"validators/ directory must exist at {validators_dir}"
        assert validators_dir.is_dir(), f"{validators_dir} must be a directory"

    def test_validators_overlays_directory_exists(self, pack_dir: Path):
        """validators/overlays/ directory must exist."""
        validators_overlays = pack_dir / 'validators' / 'overlays'
        assert validators_overlays.exists(), f"validators/overlays/ must exist at {validators_overlays}"
        assert validators_overlays.is_dir(), f"{validators_overlays} must be a directory"

    def test_validators_init_exists(self, pack_dir: Path):
        """validators/__init__.py must exist."""
        validators_init = pack_dir / 'validators' / '__init__.py'
        assert validators_init.exists(), f"validators/__init__.py must exist at {validators_init}"

    def test_guidelines_directory_exists(self, pack_dir: Path):
        """guidelines/ directory must exist."""
        guidelines_dir = pack_dir / 'guidelines'
        assert guidelines_dir.exists(), f"guidelines/ directory must exist at {guidelines_dir}"
        assert guidelines_dir.is_dir(), f"{guidelines_dir} must be a directory"

    def test_guidelines_init_exists(self, pack_dir: Path):
        """guidelines/__init__.py must exist."""
        guidelines_init = pack_dir / 'guidelines' / '__init__.py'
        assert guidelines_init.exists(), f"guidelines/__init__.py must exist at {guidelines_init}"

    def test_pack_root_init_exists(self, pack_dir: Path):
        """better-auth/__init__.py must exist."""
        root_init = pack_dir / '__init__.py'
        assert root_init.exists(), f"better-auth/__init__.py must exist at {root_init}"

    def test_pack_id_is_better_auth(self, pack_dir: Path):
        """Pack ID must be 'better-auth' in pack.yml."""
        pack_yml = pack_dir / 'pack.yml'
        content = pack_yml.read_text(encoding='utf-8')
        assert 'better-auth' in content.lower(), "pack.yml must contain 'better-auth' ID"

    def test_agent_overlay_auth_setup_exists(self, pack_dir: Path):
        """Agent overlay for API builder must exist."""
        overlay = pack_dir / 'agents' / 'overlays' / 'api-builder.md'
        assert overlay.exists(), f"Agent overlay api-builder.md must exist at {overlay}"

    def test_validator_overlay_security_exists(self, pack_dir: Path):
        """Validator overlay for security must exist."""
        overlay = pack_dir / 'validators' / 'overlays' / 'auth-security.md'
        assert overlay.exists(), f"Validator overlay auth-security.md must exist at {overlay}"

    def test_guideline_session_management_exists(self, pack_dir: Path):
        """Session management guideline must exist."""
        guideline = pack_dir / 'guidelines' / 'includes' / 'better-auth' / 'session-management.md'
        assert guideline.exists(), f"Guideline session-management.md must exist at {guideline}"

    def test_guideline_provider_config_exists(self, pack_dir: Path):
        """Provider configuration guideline must exist."""
        guideline = pack_dir / 'guidelines' / 'includes' / 'better-auth' / 'provider-configuration.md'
        assert guideline.exists(), f"Guideline provider-configuration.md must exist at {guideline}"

    def test_guideline_middleware_patterns_exists(self, pack_dir: Path):
        """Middleware patterns guideline must exist."""
        guideline = pack_dir / 'guidelines' / 'includes' / 'better-auth' / 'middleware-patterns.md'
        assert guideline.exists(), f"Guideline middleware-patterns.md must exist at {guideline}"

    def test_validator_global_overlay_exists(self, pack_dir: Path):
        """Global validator overlay must exist."""
        overlay = pack_dir / 'validators' / 'overlays' / 'global.md'
        assert overlay.exists(), f"Global validator overlay must exist at {overlay}"
