"""Tests for pack-specific agent overlays.

These tests verify that packs provide agent overlays that extend core agents.
With the unified composition system:
- Core agents are defined in `agents/{agent}.md`
- Pack overlays are in `packs/{pack}/agents/overlays/{agent}.md`
- Pack overlays EXTEND core agents, they don't define NEW agents

The discover_pack_overlays method finds overlays, not new agents.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from edison.core.composition import LayeredComposer
from edison.data import get_data_path


def test_nextjs_pack_provides_component_builder_overlay() -> None:
    """Verify nextjs pack provides an overlay for component-builder."""
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
        assert "component-builder" in core_agents
        
        # Discover pack overlays
        overlays = composer.discover_pack_overlays("nextjs", existing=set(core_agents.keys()))
        assert "component-builder" in overlays
        assert overlays["component-builder"].is_overlay
        assert overlays["component-builder"].layer == "pack:nextjs"


def test_prisma_pack_provides_database_architect_overlay() -> None:
    """Verify prisma pack provides an overlay for database-architect."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
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
        assert "database-architect" in core_agents
        
        # Discover pack overlays
        overlays = composer.discover_pack_overlays("prisma", existing=set(core_agents.keys()))
        assert "database-architect" in overlays
        assert overlays["database-architect"].is_overlay
        assert overlays["database-architect"].layer == "pack:prisma"


def test_fastify_pack_provides_api_builder_overlay() -> None:
    """Verify fastify pack provides an overlay for api-builder."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        edison_dir = tmp_path / ".edison"
        edison_dir.mkdir()
        packs_link = edison_dir / "packs"
        packs_src = get_data_path("packs")
        packs_link.symlink_to(packs_src)
        
        core_dir = edison_dir / "core"
        core_dir.mkdir()
        agents_link = core_dir / "agents"
        agents_src = get_data_path("agents")
        agents_link.symlink_to(agents_src)
        
        composer = LayeredComposer(repo_root=tmp_path, content_type="agents")
        core_agents = composer.discover_core()
        assert "api-builder" in core_agents
        
        overlays = composer.discover_pack_overlays("fastify", existing=set(core_agents.keys()))
        assert "api-builder" in overlays
        assert overlays["api-builder"].is_overlay
