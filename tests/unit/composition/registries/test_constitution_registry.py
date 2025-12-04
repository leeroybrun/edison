"""Tests for ConstitutionRegistry (no mocks)."""
from __future__ import annotations

from pathlib import Path

from edison.core.composition.registries.constitutions import ConstitutionRegistry


def test_compose_constitution_agents_uses_bundled_core(tmp_path: Path) -> None:
    registry = ConstitutionRegistry(project_root=tmp_path)

    result = registry.compose_constitution("agents")

    # compose_constitution now returns a string directly
    assert result is not None
    assert isinstance(result, str)
    # The bundled constitution should contain Agent-related content
    assert len(result) > 0
