"""Tests for constitution.yaml configuration.

Constitution.yaml v2.0.0 has embedded content in prompts, so:
- mandatoryReads is empty (content embedded via {{include:}})
- optionalReads are for on-demand deep-dive
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml
import pytest

from edison.data import get_data_path

# Get path to bundled Edison constitution config
CONSTITUTION_CONFIG_PATH = get_data_path("config", "constitution.yaml")


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Load and parse a YAML file."""
    assert path.exists(), f"missing config file: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _get_role_config(cfg: Dict[str, Any], role: str) -> Dict[str, Any]:
    """Get role configuration from schema (constitutions.<role>)."""
    return cfg.get("constitutions", {}).get(role, {})


def _get_mandatory_reads(cfg: Dict[str, Any], role: str) -> List[Dict[str, Any]]:
    """Get mandatory reads for a role."""
    return _get_role_config(cfg, role).get("mandatoryReads", [])


def _get_optional_reads(cfg: Dict[str, Any], role: str) -> List[Dict[str, Any]]:
    """Get optional reads for a role."""
    return _get_role_config(cfg, role).get("optionalReads", [])


def test_constitution_file_exists() -> None:
    """Test that constitution.yaml exists at the expected location."""
    assert CONSTITUTION_CONFIG_PATH.exists(), (
        f"Constitution config file must exist at {CONSTITUTION_CONFIG_PATH}"
    )


def test_constitution_yaml_parses_without_errors() -> None:
    """Test that constitution.yaml is valid YAML and can be parsed."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    assert isinstance(cfg, dict), "Constitution config must be a dictionary"
    assert len(cfg) > 0, "Constitution config must not be empty"


def test_constitution_has_version() -> None:
    """Test that constitution.yaml contains a version field."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    assert "version" in cfg, "Constitution config must have a version field"
    # v2.0.0 uses embedded content
    assert cfg["version"] == "2.0.0", "Version must be 2.0.0"


def test_constitution_has_constitutions_section() -> None:
    """Test that constitution.yaml has the constitutions section."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    assert "constitutions" in cfg, "Constitution config must have a 'constitutions' section"
    assert isinstance(cfg["constitutions"], dict), "constitutions must be a dictionary"


def test_all_three_role_types_defined() -> None:
    """Test that all three role types are defined in constitutions section."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    constitutions = cfg.get("constitutions", {})

    required_roles = {"orchestrator", "agents", "validators"}
    actual_roles = set(constitutions.keys())

    assert required_roles == actual_roles, (
        f"constitutions must define exactly these roles: {required_roles}. "
        f"Found: {actual_roles}"
    )


def test_each_role_has_mandatory_and_optional_reads() -> None:
    """Test that each role has both mandatoryReads and optionalReads sections."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)

    for role in ["orchestrator", "agents", "validators"]:
        role_config = _get_role_config(cfg, role)
        assert "mandatoryReads" in role_config, (
            f"Role '{role}' must have 'mandatoryReads' section"
        )
        assert "optionalReads" in role_config, (
            f"Role '{role}' must have 'optionalReads' section"
        )


def test_each_read_has_path_and_purpose() -> None:
    """Test that each read entry (mandatory or optional) has both 'path' and 'purpose' fields."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)

    for role in ["orchestrator", "agents", "validators"]:
        for read_type in ["mandatoryReads", "optionalReads"]:
            reads = _get_role_config(cfg, role).get(read_type, [])

            assert isinstance(reads, list), (
                f"{read_type} for role '{role}' must be a list"
            )

            for idx, read_entry in enumerate(reads):
                assert isinstance(read_entry, dict), (
                    f"Read entry {idx} in {read_type} for role '{role}' must be a dictionary"
                )
                assert "path" in read_entry, (
                    f"Read entry {idx} in {read_type} for role '{role}' must have 'path' field"
                )
                assert "purpose" in read_entry, (
                    f"Read entry {idx} in {read_type} for role '{role}' must have 'purpose' field"
                )
                assert isinstance(read_entry["path"], str) and len(read_entry["path"]) > 0, (
                    f"Path in read entry {idx} in {read_type} for role '{role}' must be a non-empty string"
                )
                assert isinstance(read_entry["purpose"], str) and len(read_entry["purpose"]) > 0, (
                    f"Purpose in read entry {idx} in {read_type} for role '{role}' must be a non-empty string"
                )


def test_paths_reference_generated_locations() -> None:
    """Test that paths reference generated file locations (not source files)."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)

    # Paths should NOT contain these source indicators
    forbidden_prefixes = ["src/", "edison/data/", "/", "./src/"]

    for role in ["orchestrator", "agents", "validators"]:
        for read_type in ["mandatoryReads", "optionalReads"]:
            reads = _get_role_config(cfg, role).get(read_type, [])

            for idx, read_entry in enumerate(reads):
                path = read_entry["path"]
                for forbidden in forbidden_prefixes:
                    assert not path.startswith(forbidden), (
                        f"Path '{path}' in {read_type} entry {idx} for role '{role}' must not "
                        f"start with '{forbidden}'. Use generated file locations like "
                        f"'guidelines/shared/QUALITY_PATTERNS.md' instead."
                    )


def test_mandatory_reads_empty_in_v2() -> None:
    """Test that mandatoryReads is empty in v2.0.0 (content is embedded).

    In v2.0.0, all critical content is embedded in constitution/prompt files
    via {{include:}} and {{include-section:}}. No separate reads needed.
    """
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)

    for role in ["orchestrator", "agents", "validators"]:
        mandatory_reads = _get_mandatory_reads(cfg, role)
        assert len(mandatory_reads) == 0, (
            f"Role '{role}' mandatoryReads should be empty in v2.0.0 (content is embedded)"
        )


def test_orchestrator_optional_reads() -> None:
    """Test that orchestrator role has expected optional reads."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    optional_reads = _get_optional_reads(cfg, "orchestrator")

    # Orchestrator should have optional reads for on-demand lookup
    assert len(optional_reads) >= 1, (
        "Orchestrator should have at least 1 optional read"
    )

    paths = [read["path"] for read in optional_reads]

    # Verify key optional paths exist
    expected_optional = [
        "AVAILABLE_AGENTS.md",
        "AVAILABLE_VALIDATORS.md",
    ]

    for expected_path in expected_optional:
        assert expected_path in paths, (
            f"Orchestrator should have optional read for '{expected_path}'"
        )


def test_agents_optional_reads() -> None:
    """Test that agents role has expected optional reads."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    optional_reads = _get_optional_reads(cfg, "agents")

    # Agents should have optional reads for deep-dive
    assert len(optional_reads) >= 1, (
        "Agents should have at least 1 optional read"
    )

    paths = [read["path"] for read in optional_reads]

    # Verify at least one quality/patterns read exists
    quality_reads = [p for p in paths if "QUALITY" in p or "PATTERNS" in p]
    assert len(quality_reads) >= 1, (
        "Agents should have optional read for quality patterns"
    )


def test_validators_optional_reads() -> None:
    """Test that validators role has expected optional reads."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)
    optional_reads = _get_optional_reads(cfg, "validators")

    # Validators should have optional reads
    assert len(optional_reads) >= 1, (
        "Validators should have at least 1 optional read"
    )

    paths = [read["path"] for read in optional_reads]

    # Verify at least one quality/patterns read exists
    quality_reads = [p for p in paths if "QUALITY" in p or "OUTPUT" in p]
    assert len(quality_reads) >= 1, (
        "Validators should have optional read for quality patterns or output format"
    )


def test_no_duplicate_paths_per_role() -> None:
    """Test that each role does not have duplicate paths in reads."""
    cfg = _load_yaml(CONSTITUTION_CONFIG_PATH)

    for role in ["orchestrator", "agents", "validators"]:
        role_config = _get_role_config(cfg, role)

        # Check mandatory reads
        mandatory_paths = [read["path"] for read in role_config.get("mandatoryReads", [])]
        unique_mandatory = set(mandatory_paths)
        assert len(mandatory_paths) == len(unique_mandatory), (
            f"Role '{role}' has duplicate paths in mandatory reads."
        )

        # Check optional reads
        optional_paths = [read["path"] for read in role_config.get("optionalReads", [])]
        unique_optional = set(optional_paths)
        assert len(optional_paths) == len(unique_optional), (
            f"Role '{role}' has duplicate paths in optional reads."
        )

        # Check no overlap between mandatory and optional
        overlap = unique_mandatory & unique_optional
        assert len(overlap) == 0, (
            f"Role '{role}' has paths in both mandatory and optional reads: {overlap}"
        )
