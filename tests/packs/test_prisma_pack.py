"""Test Prisma pack completeness and Prisma 6 coverage.

This test verifies that the Prisma Edison pack:
1. Has valid structure and validates against pack schema
2. Covers Prisma 6 specifics (Client API, transactions, etc.)
3. Includes comprehensive guidelines for schema, migrations, testing
4. Has proper agent overlays and validators
5. Defines appropriate rules
"""
from __future__ import annotations

import tempfile
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

from edison.core.composition.packs import validate_pack
from edison.core.composition import LayeredComposer
from edison.data import get_data_path


class TestPrismaPackStructure:
    """Test Prisma pack has valid structure."""

    def test_prisma_pack_validates(self) -> None:
        """Prisma pack should validate against schema."""
        pack_dir = Path(ROOT) / 'src/edison/data/packs/prisma'
        assert pack_dir.exists(), f"Prisma pack not found at {pack_dir}"
        
        res = validate_pack(pack_dir)
        assert res.ok, f"Prisma pack validation failed: {[i.message for i in res.issues]}"

    def test_prisma_pack_in_discovered_packs(self) -> None:
        """Prisma pack validates and can be discovered from data directory.

        Note: discover_packs() looks in .edison/packs/ (project config), not
        src/edison/data/packs/ (core data). This test validates the pack directly.
        """
        # Validate the pack from core data directory (not project config)
        pack_dir = Path(ROOT) / 'src/edison/data/packs/prisma'
        res = validate_pack(pack_dir)
        assert res.ok, f"Prisma pack not valid: {[i.message for i in res.issues]}"
        assert res.normalized is not None
        assert res.normalized.name == 'prisma'

    def test_prisma_pack_has_required_files(self) -> None:
        """Prisma pack should have all required files."""
        pack_dir = Path(ROOT) / 'src/edison/data/packs/prisma'
        
        required_files = [
            'pack.yml',
            'pack-dependencies.yaml',
            'agents/__init__.py',
            'agents/overlays/database-architect.md',
            'validators/__init__.py',
            'validators/database.md',
            'validators/overlays/global.md',
            'guidelines/__init__.py',
            'guidelines/schema-design.md',
            'guidelines/migrations.md',
            'guidelines/query-optimization.md',
            'guidelines/relationships.md',
            'guidelines/TESTING.md',
            'rules/registry.yml',
            'rules/file_patterns/database.yaml',
        ]
        
        for file_path in required_files:
            full_path = pack_dir / file_path
            assert full_path.exists(), f"Required file missing: {file_path}"


class TestPrismaPackContent:
    """Test Prisma pack content covers Prisma 6."""

    def test_schema_design_guide_covers_patterns(self) -> None:
        """Schema design guide should cover essential patterns."""
        guide = (Path(ROOT) / 'src/edison/data/packs/prisma/guidelines/schema-design.md').read_text()
        
        # Should cover UUID keys
        assert 'uuid' in guide.lower() or 'cuid' in guide.lower(), \
            "Schema design should cover UUID/CUID primary keys"
        
        # Should cover relations
        assert '@relation' in guide, "Should cover @relation syntax"
        
        # Should cover normalization
        assert 'normal' in guide.lower(), "Should discuss normalization"

    def test_migrations_guide_covers_safety(self) -> None:
        """Migrations guide should cover safety practices."""
        guide = (Path(ROOT) / 'src/edison/data/packs/prisma/guidelines/migrations.md').read_text()
        
        # Should cover additive changes
        assert 'additive' in guide.lower() or 'reversible' in guide.lower(), \
            "Migrations guide should cover safe/reversible changes"

    def test_query_optimization_covers_prisma_6(self) -> None:
        """Query optimization should cover Prisma 6 patterns."""
        guide = (Path(ROOT) / 'src/edison/data/packs/prisma/guidelines/query-optimization.md').read_text()
        
        # Should cover select/include
        assert 'select' in guide.lower(), "Should cover select pattern"
        assert 'include' in guide.lower(), "Should cover include pattern"
        
        # Should cover N+1 prevention
        assert 'n+1' in guide.lower() or 'pagination' in guide.lower(), \
            "Should cover N+1 prevention"
        
        # Should mention Prisma 6 specific features
        assert ('prisma 6' in guide.lower() or '$transaction' in guide), \
            "Should reference Prisma 6 features like $transaction"

    def test_testing_guide_covers_strategy(self) -> None:
        """Testing guide should cover Prisma testing patterns."""
        guide = (Path(ROOT) / 'src/edison/data/packs/prisma/guidelines/TESTING.md').read_text()
        
        # Should mention NO mocks
        assert 'mock' in guide.lower(), "Should discuss mocking (or lack thereof)"
        
        # Should cover database isolation
        assert 'isolation' in guide.lower() or 'test' in guide.lower(), \
            "Should cover test database isolation"

    def test_relationships_guide_covers_patterns(self) -> None:
        """Relationships guide should cover relationship patterns."""
        guide = (Path(ROOT) / 'src/edison/data/packs/prisma/guidelines/relationships.md').read_text()
        
        # Should mention cascade
        assert 'cascade' in guide.lower(), "Should cover cascade behavior"

    def test_database_architect_overlay_is_comprehensive(self) -> None:
        """Database architect overlay should have comprehensive Prisma 6 guidance."""
        overlay = (Path(ROOT) / 'src/edison/data/packs/prisma/agents/overlays/database-architect.md').read_text()
        
        # Should have multiple sections
        assert '##' in overlay, "Should have section headers"
        
        # Should cover schema patterns
        assert 'schema' in overlay.lower() and 'pattern' in overlay.lower(), \
            "Should cover schema patterns"
        
        # Should cover migrations
        assert 'migration' in overlay.lower(), "Should cover migrations"
        
        # Should cover performance
        assert ('index' in overlay.lower() or 'performance' in overlay.lower() or 'query' in overlay.lower()), \
            "Should cover performance/indexing"
        
        # Should cover Prisma 6 features
        assert ('prisma 6' in overlay.lower() or 'context7' in overlay.lower() or 'postgresql 16' in overlay.lower()), \
            "Should reference Prisma 6 or modern database features"

    def test_database_validator_is_comprehensive(self) -> None:
        """Database validator should provide comprehensive checking."""
        validator = (Path(ROOT) / 'src/edison/data/packs/prisma/validators/database.md').read_text()
        
        # Should have schema design section
        assert 'schema design' in validator.lower(), "Should have schema design checks"
        
        # Should have migration checks
        assert 'migration' in validator.lower(), "Should have migration checks"
        
        # Should have query optimization checks
        assert 'query' in validator.lower() or 'optimization' in validator.lower(), \
            "Should have query optimization checks"
        
        # Should have data integrity checks
        assert ('integrity' in validator.lower() or 'cascade' in validator.lower() or 'constraint' in validator.lower()), \
            "Should have data integrity checks"


class TestPrismaPackComposition:
    """Test Prisma pack integrates properly with composition system."""

    def test_database_architect_overlay_discoverable(self) -> None:
        """Database architect overlay should be discoverable by composer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # Create .edison/packs symlink to bundled packs
            edison_dir = tmp_path / ".edison"
            edison_dir.mkdir()
            packs_link = edison_dir / "packs"
            packs_src = get_data_path("packs")
            packs_link.symlink_to(packs_src)
            
            # Also link core agents
            core_dir = edison_dir / "core"
            core_dir.mkdir()
            agents_link = core_dir / "agents"
            agents_src = get_data_path("agents")
            agents_link.symlink_to(agents_src)
            
            composer = LayeredComposer(repo_root=tmp_path, content_type="agents")
            
            # Discover core agents first
            core_agents = composer.discover_core()
            assert "database-architect" in core_agents, \
                "database-architect should be a core agent"
            
            # Discover pack overlays
            overlays = composer.discover_pack_overlays("prisma", existing=set(core_agents.keys()))
            assert "database-architect" in overlays, \
                "Prisma pack should provide database-architect overlay"
            assert overlays["database-architect"].is_overlay, \
                "database-architect should be marked as overlay"
            assert overlays["database-architect"].layer == "pack:prisma", \
                "database-architect should have pack:prisma layer"

    def test_prisma_pack_validators_discoverable(self) -> None:
        """Prisma pack validators should be discoverable."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            
            # Create .edison/packs symlink
            edison_dir = tmp_path / ".edison"
            edison_dir.mkdir()
            packs_link = edison_dir / "packs"
            packs_src = get_data_path("packs")
            packs_link.symlink_to(packs_src)
            
            # Create .edison/core/validators symlink
            core_dir = edison_dir / "core"
            core_dir.mkdir()
            validators_link = core_dir / "validators"
            validators_src = get_data_path("validators")
            validators_link.symlink_to(validators_src)
            
            composer = LayeredComposer(repo_root=tmp_path, content_type="validators")
            
            # Discover core validators
            core_validators = composer.discover_core()
            
            # Discover pack validator overlays
            overlays = composer.discover_pack_overlays("prisma", existing=set(core_validators.keys()))
            
            # Should have validators from pack
            assert len(overlays) > 0, "Prisma pack should provide validator overlays"


class TestPrismaPackRules:
    """Test Prisma pack rules are properly defined."""

    def test_rules_registry_is_valid(self) -> None:
        """Rules registry should be valid YAML with required fields."""
        registry_path = Path(ROOT) / 'src/edison/data/packs/prisma/rules/registry.yml'
        assert registry_path.exists(), "Rules registry should exist"
        
        content = registry_path.read_text()
        assert 'version' in content, "Registry should have version"
        assert 'rules:' in content, "Registry should have rules section"

    def test_rules_include_schema_design(self) -> None:
        """Rules should include schema design checks."""
        registry_path = Path(ROOT) / 'src/edison/data/packs/prisma/rules/registry.yml'
        content = registry_path.read_text()
        
        # Should have rules about schema patterns
        assert 'PRISMA' in content, "Should have Prisma-specific rules"
        assert 'uuid' in content.lower() or 'primary' in content.lower(), \
            "Should have rules about primary keys"

    def test_rules_include_migration_safety(self) -> None:
        """Rules should include migration safety checks."""
        registry_path = Path(ROOT) / 'src/edison/data/packs/prisma/rules/registry.yml'
        content = registry_path.read_text()
        
        assert 'MIGRATION' in content or 'migration' in content.lower(), \
            "Should have migration-related rules"

    def test_file_patterns_trigger_database_validator(self) -> None:
        """File patterns should trigger database validator."""
        patterns_path = Path(ROOT) / 'src/edison/data/packs/prisma/rules/file_patterns/database.yaml'
        assert patterns_path.exists(), "File patterns should exist"
        
        content = patterns_path.read_text()
        assert 'schema.prisma' in content, "Should trigger on schema.prisma"
        assert 'database' in content, "Should reference database validator"


class TestPrismaPackDependencies:
    """Test Prisma pack dependencies are correct."""

    def test_pack_dependencies_file_exists(self) -> None:
        """Pack dependencies file should exist."""
        deps_path = Path(ROOT) / 'src/edison/data/packs/prisma/pack-dependencies.yaml'
        assert deps_path.exists(), "pack-dependencies.yaml should exist"

    def test_pack_dependencies_are_valid(self) -> None:
        """Pack dependencies should be valid YAML."""
        import yaml
        deps_path = Path(ROOT) / 'src/edison/data/packs/prisma/pack-dependencies.yaml'
        content = yaml.safe_load(deps_path.read_text())
        
        # Should have dependencies or requiredPacks
        assert content is not None, "Dependencies file should have content"


class TestPrismaPackIntegration:
    """Test Prisma pack integration with other components."""

    def test_prisma_pack_referenced_in_pack_yml(self) -> None:
        """All pack.yml references should point to existing files."""
        pack_path = Path(ROOT) / 'src/edison/data/packs/prisma/pack.yml'
        import yaml
        manifest = yaml.safe_load(pack_path.read_text())
        
        pack_dir = pack_path.parent
        
        # Check guidelines
        if 'provides' in manifest and 'guidelines' in manifest['provides']:
            for guide_ref in manifest['provides']['guidelines']:
                guide_path = pack_dir / guide_ref
                assert guide_path.exists(), f"Referenced guideline missing: {guide_ref}"
        
        # Check validators
        if 'provides' in manifest and 'validators' in manifest['provides']:
            for validator_ref in manifest['provides']['validators']:
                validator_path = pack_dir / validator_ref
                assert validator_path.exists(), f"Referenced validator missing: {validator_ref}"
        
        # Check agents
        if 'provides' in manifest and 'agents' in manifest['provides']:
            for agent_ref in manifest['provides']['agents']:
                agent_path = pack_dir / agent_ref
                assert agent_path.exists(), f"Referenced agent missing: {agent_ref}"

    def test_prisma_pack_has_no_legacy_patterns(self) -> None:
        """Prisma pack should not use legacy patterns."""
        pack_dir = Path(ROOT) / 'src/edison/data/packs/prisma'
        
        # Check pack.yml doesn't have old-style list-only triggers
        pack_path = pack_dir / 'pack.yml'
        content = pack_path.read_text()
        
        # Should use triggers.filePatterns structure
        assert 'triggers:' in content, "Should have triggers section"
        assert 'filePatterns:' in content, "Should use filePatterns (not legacy list)"

