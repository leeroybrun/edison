from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

from edison.data import get_data_path

AGENT_SPECS = {
    "api-builder": {
        "filename": "api-builder.md",
        "model": "codex",
        "description": "Backend API specialist for route handlers, validation, and data flow",
    },
    "component-builder": {
        "filename": "component-builder.md",
        "model": "claude",
        "description": "UI component specialist for accessible, responsive interfaces",
    },
    "database-architect": {
        "filename": "database-architect.md",
        "model": "codex",
        "description": "Database schema and migration specialist for reliable, performant data layers",
    },
    "code-reviewer": {
        "filename": "code-reviewer.md",
        "model": "claude",
        "description": "Code quality reviewer ensuring TDD compliance and actionable feedback",
    },
    "test-engineer": {
        "filename": "test-engineer.md",
        "model": "codex",
        "description": "Test automation and TDD guardian ensuring coverage and reliability",
    },
    "feature-implementer": {
        "filename": "feature-implementer.md",
        "model": "claude",
        "description": "Full-stack feature implementer delivering end-to-end product experiences",
    },
}

ALLOWED_TOOLS = ["Read", "Edit", "Write", "Grep", "Glob", "Bash"]
REQUIRED_KEYS = {
    "name",
    "description",
    "model",
    "palRole",
    "allowed_tools",
    "requires_validation",
    "constitution",
}
CONSTITUTION_PATH = "constitutions/AGENTS.md"


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that raises on duplicate keys."""


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.Node, deep: bool = False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise yaml.YAMLError(f"Duplicate key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _load_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8").lstrip("\ufeff")
    lines = text.splitlines()
    assert lines, f"{path} is empty"
    assert lines[0].strip() == "---", f"{path} missing starting frontmatter delimiter"

    try:
        end = lines[1:].index("---") + 1
    except ValueError as exc:
        raise AssertionError(f"{path} missing closing frontmatter delimiter") from exc

    header_text = "\n".join(lines[1:end])
    data = yaml.load(header_text, Loader=UniqueKeyLoader)
    assert isinstance(data, dict), f"{path} frontmatter did not parse to dict"
    return data


def test_agent_inventory_matches_plan() -> None:
    agents_dir = get_data_path("agents")
    files = {p.name for p in agents_dir.glob("*.md")}
    expected = {spec["filename"] for spec in AGENT_SPECS.values()}
    assert files == expected, "Agent files changed; update T-016 tests to match"


@pytest.mark.parametrize("agent_name,spec", AGENT_SPECS.items())
def test_agent_frontmatter_required_fields(agent_name: str, spec: dict) -> None:
    agents_dir = get_data_path("agents")
    path = agents_dir / spec["filename"]
    assert path.exists(), f"Missing agent file: {path}"

    fm = _load_frontmatter(path)

    missing = REQUIRED_KEYS - set(fm)
    assert not missing, f"{path} missing required frontmatter fields: {sorted(missing)}"

    assert "context7_ids" not in fm, f"{path} must not hardcode technology-specific context7_ids in core"

    assert fm["name"] == agent_name
    assert fm["description"] == spec["description"]
    assert fm["model"] == spec["model"]
    assert fm["palRole"] == f"{{{{project.palRoles.{agent_name}}}}}", "palRole must use project variable"
    assert fm["allowed_tools"] == ALLOWED_TOOLS
    assert fm["requires_validation"] is True
    assert fm["constitution"] == CONSTITUTION_PATH


@pytest.mark.parametrize("agent_name,spec", AGENT_SPECS.items())
def test_agent_frontmatter_yaml_parses_without_duplicates(agent_name: str, spec: dict) -> None:
    agents_dir = get_data_path("agents")
    path = agents_dir / spec["filename"]
    _ = _load_frontmatter(path)


def test_component_builder_has_server_client_examples() -> None:
    """Test that the Next.js pack overlay includes Server/Client examples.

    This validates T-027: Server/Client examples must be present to demonstrate
    Next.js 16 App Router patterns for when to use Server vs Client Components.
    """
    path = Path("src/edison/data/packs/nextjs/agents/overlays/component-builder.md")
    content = path.read_text(encoding="utf-8")

    # Check for Server Components section
    assert "## Server Components" in content, \
        "Missing '## Server Components' section header"

    # Check for Client Components section
    assert "## Client Components" in content, \
        "Missing '## Client Components' section header"

    # Check for 'use client' directive documentation
    assert "'use client'" in content or '"use client"' in content, \
        "Missing 'use client' directive documentation"

    # Check for actual code examples (using pseudocode blocks)
    server_example_start = content.find("## Server Components")
    client_example_start = content.find("## Client Components")

    assert server_example_start > 0, "Server Components section not found"
    assert client_example_start > 0, "Client Components section not found"

    # Server Components section should come before Client Components
    assert server_example_start < client_example_start, \
        "Server Components section should come before Client Components section"

    # Extract Server Components section content
    server_section = content[server_example_start:client_example_start]

    # Verify Server Components section has code examples
    assert "```" in server_section, \
        "Server Components section missing code examples"
    assert "async" in server_section or "fetch" in server_section or "database" in server_section, \
        "Server Components section should show async/data fetching patterns"

    # Extract Client Components section (from its start to next ## or end)
    next_section = content.find("\n## ", client_example_start + 1)
    if next_section > 0:
        client_section = content[client_example_start:next_section]
    else:
        client_section = content[client_example_start:]

    # Verify Client Components section has code examples
    assert "```" in client_section, \
        "Client Components section missing code examples"
    assert "useState" in client_section or "onClick" in client_section or "onChange" in client_section, \
        "Client Components section should show interactive/state patterns"


def _extract_context7_section(content: str, path: Path) -> str:
    heading = "## Context7 Knowledge Refresh (MANDATORY)"
    assert heading in content, f"{path} missing Context7 refresh heading"
    start = content.index(heading)
    return content[start:]


@pytest.mark.parametrize("agent_name,spec", AGENT_SPECS.items())
def test_agents_include_context7_examples(agent_name: str, spec: dict) -> None:
    """T-020: Agents must include Context7 usage examples tailored to their domain."""
    agents_dir = get_data_path("agents")
    path = agents_dir / spec["filename"]
    content = path.read_text(encoding="utf-8")

    heading = "## Context7 Knowledge Refresh (MANDATORY)"
    agent_heading = "# Agent:"

    assert heading in content, f"{path} missing Context7 Knowledge Refresh section"
    assert agent_heading in content, f"{path} missing Agent heading"
    assert content.index(heading) < content.index(agent_heading), \
        f"{path} Context7 section must appear immediately after frontmatter and before the Agent heading"

    section = _extract_context7_section(content, path)

    # Allow canonical include-section directive (single source of truth).
    canonical = "{{include-section:guidelines/includes/CONTEXT7.md#agent}}"
    if canonical in section:
        include_path = get_data_path("guidelines/includes", "CONTEXT7.md")
        inc = include_path.read_text(encoding="utf-8")
        m = re.search(
            r"<!--\s*section:\s*agent\s*-->\n(.+?)\n<!--\s*/section:\s*agent\s*-->",
            inc,
            flags=re.S | re.I,
        )
        assert m, "Canonical CONTEXT7 include section 'agent' missing"
        section = section.replace(canonical, m.group(1).strip())

    assert "Resolve Library ID" in section, f"{path} missing resolve step heading"
    assert "mcp__context7__resolve_library_id" in section, \
        f"{path} missing resolve_library_id example"
    assert "libraryName" in section, f"{path} resolve example missing libraryName"

    assert "Get Current Documentation" in section, f"{path} missing docs retrieval heading"
    assert "mcp__context7__get_library_docs" in section, \
        f"{path} missing get_library_docs example"
    assert "context7CompatibleLibraryID" in section, \
        f"{path} get-library-docs example missing context7CompatibleLibraryID"

    assert "config/context7.yaml" in section, \
        f"{path} must point to config/context7.yaml for versions"
