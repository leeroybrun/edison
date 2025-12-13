"""Tests for ConstitutionRegistry (no mocks)."""
from __future__ import annotations

from pathlib import Path

from edison.core.composition.registries.constitutions import ConstitutionRegistry


def test_compose_constitution_agents_uses_bundled_core(tmp_path: Path) -> None:
    registry = ConstitutionRegistry(project_root=tmp_path)

    result = registry.compose("agents", packs=[])

    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0

    # Embedded constitution content should be present (no empty shells)
    assert "## TDD Principles (All Roles)" in result

    # Optional references should render from constitution.yaml (v2: optional reads)
    assert "## Optional References" in result
    assert "- guidelines/shared/" in result

    # Applicable rules should render (at least one heading)
    assert "## Applicable Rules" in result
    assert "\n### " in result
