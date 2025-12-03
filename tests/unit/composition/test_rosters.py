from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from edison.core.composition import AgentRegistry, generate_available_agents, generate_canonical_entry


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _table_names(markdown: str) -> list[str]:
    lines = markdown.splitlines()
    names: list[str] = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("| Agent |"):
            in_table = True
            continue
        if in_table and stripped.startswith("|---"):
            continue
        if in_table:
            if not stripped.startswith("|"):
                break
            cells = [c.strip() for c in stripped.split("|")[1:-1]]
            if cells and cells[0]:
                names.append(cells[0])
    return names


def test_available_agents_file_written_to_generated_dir(tmp_path: Path) -> None:
    output_path = tmp_path / ".edison" / "_generated" / "AVAILABLE_AGENTS.md"

    generate_available_agents(output_path, repo_root=tmp_path)

    assert output_path.exists(), "AVAILABLE_AGENTS.md must be written to .edison/_generated"


def test_generation_header_contains_iso_timestamp(tmp_path: Path) -> None:
    output_path = tmp_path / ".edison" / "_generated" / "AVAILABLE_AGENTS.md"

    generate_available_agents(output_path, repo_root=tmp_path)
    content = _read_file(output_path)

    assert "AUTO-GENERATED FILE - DO NOT EDIT MANUALLY" in content
    match = re.search(r"Generated at:\s*([0-9T:.-]+)", content)
    assert match, "Generated header must include timestamp"
    datetime.fromisoformat(match.group(1).strip())


def test_agent_table_includes_all_registry_agents(tmp_path: Path) -> None:
    output_path = tmp_path / ".edison" / "_generated" / "AVAILABLE_AGENTS.md"
    registry = AgentRegistry(project_root=tmp_path)

    # Get expected names from core agents
    expected_names = set(registry.discover_core().keys())

    generate_available_agents(output_path, repo_root=tmp_path)
    table_names = set(_table_names(_read_file(output_path)))

    assert table_names, "Agent table must not be empty"
    assert table_names == expected_names, "Agent table must list all registry agents"


def test_generator_uses_registry_not_hardcoded_names(tmp_path: Path) -> None:
    """Test that generator reads from registry (bundled core agents).
    
    Architecture: Core agents are ALWAYS from bundled edison.data package.
    NO .edison/core/ - that is LEGACY.
    Project-level agents can be added at .edison/agents/ but core is bundled.
    """
    repo_root = tmp_path / "custom"
    repo_root.mkdir(parents=True, exist_ok=True)
    
    # Create minimal project structure
    (repo_root / ".edison").mkdir(parents=True, exist_ok=True)

    output_path = repo_root / ".edison" / "_generated" / "AVAILABLE_AGENTS.md"
    generate_available_agents(output_path, repo_root=repo_root)

    table_names = set(_table_names(_read_file(output_path)))

    # Should discover bundled core agents, not from .edison/core/
    assert "api-builder" in table_names, (
        "Generator must read agents from bundled registry"
    )
    assert len(table_names) >= 4, (
        "Generator must discover multiple bundled agents"
    )


def test_canonical_entry_generated_at_repo_root(tmp_path: Path) -> None:
    """Test that canonical entry (AGENTS.md) is generated at repo root."""
    output_path = tmp_path / "AGENTS.md"

    generate_canonical_entry(output_path, repo_root=tmp_path)

    assert output_path.exists(), "AGENTS.md must be written to repo root"


def test_canonical_entry_replaces_placeholders(tmp_path: Path) -> None:
    """Test that all template placeholders are replaced."""
    output_path = tmp_path / "AGENTS.md"

    generate_canonical_entry(output_path, repo_root=tmp_path)
    content = _read_file(output_path)

    # Check that placeholders are replaced
    assert "{{source_layers}}" not in content, "{{source_layers}} must be replaced"
    assert "{{timestamp}}" not in content, "{{timestamp}} must be replaced"
    assert "{{EXTENSIBLE_SECTIONS}}" not in content, "{{EXTENSIBLE_SECTIONS}} must be replaced"
    assert "{{APPEND_SECTIONS}}" not in content, "{{APPEND_SECTIONS}} must be replaced"
    assert "{{PROJECT_EDISON_DIR}}" not in content, "{{PROJECT_EDISON_DIR}} must be resolved"


def test_canonical_entry_contains_constitution_paths(tmp_path: Path) -> None:
    """Test that generated file contains constitution file paths."""
    output_path = tmp_path / "AGENTS.md"

    generate_canonical_entry(output_path, repo_root=tmp_path)
    content = _read_file(output_path)

    # Check for key content
    assert "MANDATORY: Constitution" in content, "Must contain constitution header"
    assert "Orchestrator" in content, "Must reference Orchestrator role"
    assert "Agent (Implementer)" in content, "Must reference Agent role"
    assert "Validator" in content, "Must reference Validator role"


def test_canonical_entry_includes_generation_metadata(tmp_path: Path) -> None:
    """Test that generated file includes metadata in HTML comments."""
    output_path = tmp_path / "AGENTS.md"

    generate_canonical_entry(output_path, repo_root=tmp_path)
    content = _read_file(output_path)

    # Check for generated header metadata
    assert "<!-- GENERATED BY EDISON - DO NOT EDIT -->" in content, "Must have generation warning"
    assert "<!-- Source:" in content, "Must include source layers info"
    assert "<!-- Generated:" in content, "Must include generation timestamp"
    assert "<!-- Regenerate: edison compose" in content, "Must include regeneration command"
