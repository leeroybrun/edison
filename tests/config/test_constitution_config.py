from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import json

import jsonschema
import yaml
import pytest

from edison.data import get_data_path

# Get path to bundled Edison constitution config
CONSTITUTION_CONFIG_PATH = get_data_path("config", "constitution.yaml")


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Load and parse a YAML file."""
    assert path.exists(), f"missing config file: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def test_constitution_file_exists() -> None:
    """
    Test that constitution.yaml exists at the expected location.

    This is the RED phase - file does not exist yet.
    """
    assert CONSTITUTION_CONFIG_PATH.exists(), (
        f"Constitution config file must exist at {CONSTITUTION_CONFIG_PATH}"
    )


def test_constitution_yaml_parses_without_errors() -> None:
    """
    Test that constitution.yaml is valid YAML and can be parsed.

    This verifies the file structure is syntactically correct.
    """
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    assert isinstance(cfg, dict), "Constitution config must be a dictionary"
    assert len(cfg) > 0, "Constitution config must not be empty"


def test_constitution_has_version() -> None:
    """Test that constitution.yaml contains a version field."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    assert "version" in cfg, "Constitution config must have a version field"
    assert cfg["version"] == "1.0.0", "Version must be 1.0.0"


def test_all_three_role_types_defined() -> None:
    """
    Test that all three role types are defined in mandatoryReads.

    Required roles: orchestrator, agents, validators
    """
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    assert "mandatoryReads" in cfg, "Constitution must have mandatoryReads section"

    mandatory_reads = cfg["mandatoryReads"]
    assert isinstance(mandatory_reads, dict), "mandatoryReads must be a dictionary"

    required_roles = {"orchestrator", "agents", "validators"}
    actual_roles = set(mandatory_reads.keys())

    assert required_roles == actual_roles, (
        f"mandatoryReads must define exactly these roles: {required_roles}. "
        f"Found: {actual_roles}"
    )


def test_each_mandatory_read_has_path_and_purpose() -> None:
    """
    Test that each mandatory read entry has both 'path' and 'purpose' fields.

    This ensures the configuration structure is complete and usable.
    """
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    mandatory_reads = cfg["mandatoryReads"]

    for role, reads in mandatory_reads.items():
        assert isinstance(reads, list), f"Reads for role '{role}' must be a list"
        assert len(reads) > 0, f"Role '{role}' must have at least one mandatory read"

        for idx, read_entry in enumerate(reads):
            assert isinstance(read_entry, dict), (
                f"Read entry {idx} for role '{role}' must be a dictionary"
            )
            assert "path" in read_entry, (
                f"Read entry {idx} for role '{role}' must have 'path' field"
            )
            assert "purpose" in read_entry, (
                f"Read entry {idx} for role '{role}' must have 'purpose' field"
            )
            assert isinstance(read_entry["path"], str), (
                f"Path in read entry {idx} for role '{role}' must be a string"
            )
            assert isinstance(read_entry["purpose"], str), (
                f"Purpose in read entry {idx} for role '{role}' must be a string"
            )
            assert len(read_entry["path"]) > 0, (
                f"Path in read entry {idx} for role '{role}' must not be empty"
            )
            assert len(read_entry["purpose"]) > 0, (
                f"Purpose in read entry {idx} for role '{role}' must not be empty"
            )


def test_paths_reference_generated_locations() -> None:
    """
    Test that paths reference generated file locations (not source files).

    Paths should be relative paths like 'constitutions/ORCHESTRATORS.md'
    rather than source paths like 'src/edison/data/constitutions/ORCHESTRATORS.md'.
    """
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    mandatory_reads = cfg["mandatoryReads"]

    # Paths should NOT contain these source indicators
    forbidden_prefixes = ["src/", "edison/data/", "/", "./src/"]

    for role, reads in mandatory_reads.items():
        for idx, read_entry in enumerate(reads):
            path = read_entry["path"]
            for forbidden in forbidden_prefixes:
                assert not path.startswith(forbidden), (
                    f"Path '{path}' in read entry {idx} for role '{role}' must not "
                    f"start with '{forbidden}'. Use generated file locations like "
                    f"'constitutions/ORCHESTRATORS.md' instead."
                )


def test_orchestrator_mandatory_reads() -> None:
    """Test that orchestrator role has expected mandatory reads."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    orchestrator_reads = cfg["mandatoryReads"]["orchestrator"]

    # Check that we have the minimum expected reads
    assert len(orchestrator_reads) >= 7, (
        "Orchestrator must have at least 7 mandatory reads"
    )

    # Extract paths for validation
    paths = [read["path"] for read in orchestrator_reads]

    # Verify key paths are present
    expected_paths = [
        "constitutions/ORCHESTRATORS.md",
        "guidelines/orchestrators/SESSION_WORKFLOW.md",
        "guidelines/shared/DELEGATION.md",
        "AVAILABLE_AGENTS.md",
        "AVAILABLE_VALIDATORS.md",
        "guidelines/shared/TDD.md",
        "guidelines/shared/VALIDATION.md",
    ]

    for expected_path in expected_paths:
        assert expected_path in paths, (
            f"Orchestrator must have mandatory read for '{expected_path}'"
        )


def test_agents_mandatory_reads() -> None:
    """Test that agents role has expected mandatory reads."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    agents_reads = cfg["mandatoryReads"]["agents"]

    # Check that we have the minimum expected reads
    assert len(agents_reads) >= 7, (
        "Agents must have at least 7 mandatory reads"
    )

    # Extract paths for validation
    paths = [read["path"] for read in agents_reads]

    # Verify key paths are present
    expected_paths = [
        "constitutions/AGENTS.md",
        "guidelines/agents/MANDATORY_WORKFLOW.md",
        "guidelines/agents/OUTPUT_FORMAT.md",
        "guidelines/shared/TDD.md",
        "guidelines/shared/CONTEXT7.md",
        "guidelines/shared/QUALITY.md",
        "guidelines/shared/EPHEMERAL_SUMMARIES_POLICY.md",
    ]

    for expected_path in expected_paths:
        assert expected_path in paths, (
            f"Agents must have mandatory read for '{expected_path}'"
        )


def test_validators_mandatory_reads() -> None:
    """Test that validators role has expected mandatory reads."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    validators_reads = cfg["mandatoryReads"]["validators"]

    # Check that we have the minimum expected reads
    assert len(validators_reads) >= 4, (
        "Validators must have at least 4 mandatory reads"
    )

    # Extract paths for validation
    paths = [read["path"] for read in validators_reads]

    # Verify key paths are present
    expected_paths = [
        "constitutions/VALIDATORS.md",
        "guidelines/validators/VALIDATOR_WORKFLOW.md",
        "guidelines/validators/OUTPUT_FORMAT.md",
        "guidelines/shared/CONTEXT7.md",
    ]

    for expected_path in expected_paths:
        assert expected_path in paths, (
            f"Validators must have mandatory read for '{expected_path}'"
        )


def test_no_duplicate_paths_per_role() -> None:
    """Test that each role does not have duplicate paths in mandatory reads."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    mandatory_reads = cfg["mandatoryReads"]

    for role, reads in mandatory_reads.items():
        paths = [read["path"] for read in reads]
        unique_paths = set(paths)

        assert len(paths) == len(unique_paths), (
            f"Role '{role}' has duplicate paths in mandatory reads. "
            f"Found {len(paths)} total paths but only {len(unique_paths)} unique paths."
        )
