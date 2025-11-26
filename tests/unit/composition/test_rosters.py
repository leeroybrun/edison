from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from edison.core.composition.agents import AgentRegistry
from edison.core.composition.rosters import generate_available_agents


def _read(path: Path) -> str:
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
    content = _read(output_path)

    assert "<!-- GENERATED FILE - DO NOT EDIT DIRECTLY -->" in content
    match = re.search(r"<!-- Generated:\s*([^>]+) -->", content)
    assert match, "Generated header must include timestamp"
    # Validate ISO timestamp format
    datetime.fromisoformat(match.group(1).strip())


def test_agent_table_includes_all_registry_agents(tmp_path: Path) -> None:
    output_path = tmp_path / ".edison" / "_generated" / "AVAILABLE_AGENTS.md"
    registry = AgentRegistry(repo_root=tmp_path)

    expected_names = {agent["name"] for agent in registry.get_all()}

    generate_available_agents(output_path, repo_root=tmp_path)
    table_names = set(_table_names(_read(output_path)))

    assert table_names, "Agent table must not be empty"
    assert table_names == expected_names, "Agent table must list all registry agents"


def test_generator_uses_registry_not_hardcoded_names(tmp_path: Path) -> None:
    repo_root = tmp_path / "custom"
    agents_dir = repo_root / ".edison" / "core" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    (agents_dir / "innovation-core.md").write_text(
        """---
name: innovation
description: "Innovation specialist"
model: codex
type: strategist
---

# Agent: Innovation
""",
        encoding="utf-8",
    )

    output_path = repo_root / ".edison" / "_generated" / "AVAILABLE_AGENTS.md"
    generate_available_agents(output_path, repo_root=repo_root)

    table_names = set(_table_names(_read(output_path)))

    assert table_names == {"innovation"}, (
        "Generator must read agents from registry instead of hardcoded templates"
    )
