"""T-022: Test that no hardcoded wilson-* palRole values exist in core Edison files.

This test validates that:
1. No "wilson-" prefix appears in core agent files
2. No "wilson-" prefix appears in core config files
3. All palRole values use template variables like {{project.palRoles.agent-name}}
4. Project-specific palRoles are defined in project overlay, NOT in core

Related: T-016 (YAML Frontmatter - dependency)
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from edison.data import get_data_path


def test_no_wilson_prefix_in_agent_files() -> None:
    """Verify no agent file contains hardcoded 'wilson-' prefix in palRole.

    palRole values should use template variables like:
    palRole: "{{project.palRoles.api-builder}}"

    NOT hardcoded project names like:
    palRole: wilson-api-builder
    """
    agents_dir = get_data_path("agents")
    agent_files = list(agents_dir.glob("*.md"))

    assert agent_files, "No agent files found - check agents directory"

    violations = []
    for agent_file in agent_files:
        content = agent_file.read_text(encoding="utf-8")

        # Search for "wilson-" anywhere in the file
        if "wilson-" in content.lower():
            # Get line numbers for better error reporting
            lines_with_wilson = [
                (i + 1, line.strip())
                for i, line in enumerate(content.splitlines())
                if "wilson-" in line.lower()
            ]
            violations.append((agent_file.name, lines_with_wilson))

    assert not violations, (
        "Found hardcoded 'wilson-' prefix in agent files. "
        "Use template variables like {{project.palRoles.agent-name}} instead:\n"
        + "\n".join(
            f"  {filename}: {lines}"
            for filename, lines in violations
        )
    )


def test_no_wilson_prefix_in_config_files() -> None:
    """Verify no config file contains hardcoded 'wilson-' prefix.

    Config files should reference agents by template variables, not hardcoded names.
    Project-specific palRoles belong in .edison/config/project.yaml overlay.
    """
    config_dir = get_data_path("config")
    config_files = list(config_dir.glob("*.yaml"))

    assert config_files, "No config files found - check config directory"

    violations = []
    for config_file in config_files:
        content = config_file.read_text(encoding="utf-8")

        # Search for "wilson-" anywhere in the file
        if "wilson-" in content.lower():
            # Get line numbers for better error reporting
            lines_with_wilson = [
                (i + 1, line.strip())
                for i, line in enumerate(content.splitlines())
                if "wilson-" in line.lower()
            ]
            violations.append((config_file.name, lines_with_wilson))

    assert not violations, (
        "Found hardcoded 'wilson-' prefix in config files. "
        "Project-specific config belongs in .edison/config/project.yaml overlay:\n"
        + "\n".join(
            f"  {filename}: {lines}"
            for filename, lines in violations
        )
    )


def test_no_wilson_prefix_in_validator_files() -> None:
    """Verify no validator file contains hardcoded 'wilson-' prefix.

    Validators are core components and should not reference project-specific names.
    """
    validators_dir = get_data_path("validators")
    validator_files = []

    # Recursively find all .md files in validators directory
    for tier_dir in validators_dir.iterdir():
        if tier_dir.is_dir():
            validator_files.extend(tier_dir.glob("*.md"))

    # Validators are optional, but if they exist, they shouldn't have wilson- prefix
    if not validator_files:
        pytest.skip("No validator files found - skipping test")

    violations = []
    for validator_file in validator_files:
        content = validator_file.read_text(encoding="utf-8")

        # Search for "wilson-" anywhere in the file
        if "wilson-" in content.lower():
            # Get line numbers for better error reporting
            lines_with_wilson = [
                (i + 1, line.strip())
                for i, line in enumerate(content.splitlines())
                if "wilson-" in line.lower()
            ]
            violations.append((validator_file.name, lines_with_wilson))

    assert not violations, (
        "Found hardcoded 'wilson-' prefix in validator files. "
        "Validators are core components and should not reference project-specific names:\n"
        + "\n".join(
            f"  {filename}: {lines}"
            for filename, lines in violations
        )
    )


def test_agent_palroles_use_template_variables() -> None:
    """Verify all agent palRole values use template variable syntax.

    This is the CORRECT pattern for core Edison agents:
    palRole: "{{project.palRoles.api-builder}}"

    This allows projects to define their own palRole mappings in:
    .edison/config/project.yaml
    """
    agents_dir = get_data_path("agents")
    agent_files = list(agents_dir.glob("*.md"))

    assert agent_files, "No agent files found - check agents directory"

    # Pattern to match palRole in YAML frontmatter
    palrole_pattern = re.compile(r'^palRole:\s*"?\{\{project\.palRoles\.[a-z0-9-]+\}\}"?', re.MULTILINE)

    violations = []
    for agent_file in agent_files:
        content = agent_file.read_text(encoding="utf-8")

        # Extract frontmatter (between first and second ---)
        lines = content.splitlines()
        if not lines or lines[0].strip() != "---":
            violations.append((agent_file.name, "Missing frontmatter start delimiter"))
            continue

        try:
            end_idx = lines[1:].index("---") + 1
            frontmatter = "\n".join(lines[1:end_idx])
        except ValueError:
            violations.append((agent_file.name, "Missing frontmatter end delimiter"))
            continue

        # Check if palRole exists and uses correct template
        if "palRole:" not in frontmatter:
            violations.append((agent_file.name, "Missing palRole field in frontmatter"))
            continue

        if not palrole_pattern.search(frontmatter):
            # Extract the actual palRole line for error reporting
            palrole_line = [line for line in frontmatter.splitlines() if "palRole:" in line]
            violations.append((
                agent_file.name,
                f"palRole does not use template variable syntax: {palrole_line[0] if palrole_line else 'NOT FOUND'}"
            ))

    assert not violations, (
        "Agent files have incorrect palRole format. Must use {{project.palRoles.agent-name}}:\n"
        + "\n".join(
            f"  {filename}: {error}"
            for filename, error in violations
        )
    )


def test_no_hardcoded_project_names_in_core() -> None:
    """Comprehensive test: no project-specific names in core Edison files.

    This test ensures Edison core remains project-agnostic.
    Project-specific configuration belongs in .edison/config/project.yaml overlay.
    """
    # Collect all .md and .yaml files
    all_files = []

    # Get agent files
    agents_dir = get_data_path("agents")
    all_files.extend(agents_dir.glob("*.md"))

    # Get config files
    config_dir = get_data_path("config")
    all_files.extend(config_dir.glob("*.yaml"))

    # Add validators if they exist
    validators_dir = get_data_path("validators")
    if validators_dir.exists():
        for tier_dir in validators_dir.iterdir():
            if tier_dir.is_dir():
                all_files.extend(tier_dir.glob("*.md"))

    assert all_files, "No core files found to validate"

    # List of project-specific prefixes that should NOT appear in core
    forbidden_prefixes = [
        "wilson-",
        "leadgen-",
        # Add other known project prefixes here if needed
    ]

    violations = []
    for filepath in all_files:
        content = filepath.read_text(encoding="utf-8")

        for prefix in forbidden_prefixes:
            if prefix in content.lower():
                # Get line numbers
                lines_with_prefix = [
                    (i + 1, line.strip())
                    for i, line in enumerate(content.splitlines())
                    if prefix in line.lower()
                ]
                violations.append((filepath.name, prefix, lines_with_prefix))

    assert not violations, (
        "Found project-specific names in core Edison files. "
        "Core files must be project-agnostic. "
        "Move project config to .edison/config/project.yaml overlay:\n"
        + "\n".join(
            f"  {filepath} contains '{prefix}': {lines}"
            for filepath, prefix, lines in violations
        )
    )
