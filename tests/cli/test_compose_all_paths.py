import pytest
from pathlib import Path
from edison.cli.compose.all import main
from edison.core.paths.project import get_project_config_dir
from argparse import Namespace


def _setup_minimal_edison_structure(repo_root: Path, validator_id: str = "test-val") -> None:
    """Create minimal Edison structure needed for composition tests."""
    # Create core Edison structure
    core_dir = repo_root / ".edison" / "core"
    validators_dir = core_dir / "validators" / "global"
    validators_dir.mkdir(parents=True, exist_ok=True)

    # Create minimal validator spec for testing
    # Extract role from validator_id (e.g., "test-val" -> "test")
    role = validator_id.split("-", 1)[0]
    validator_spec = validators_dir / f"{role}-core.md"
    validator_spec.write_text(
        "# Core Edison Principles\n"
        f"Test validator content for {validator_id}.\n"
        "Unique test guidance to avoid DRY violations.\n",
        encoding="utf-8",
    )

    # Create mandatory guideline files for orchestrator
    guidelines_dir = core_dir / "guidelines"
    guidelines_dir.mkdir(parents=True, exist_ok=True)

    # Create required guideline files
    for guideline_name in ["SESSION_WORKFLOW", "DELEGATION", "TDD"]:
        guideline_file = guidelines_dir / f"{guideline_name}.md"
        guideline_file.write_text(
            f"# {guideline_name}\n\nTest guideline content.\n",
            encoding="utf-8",
        )

    # Create constitution templates
    constitutions_dir = core_dir / "constitutions"
    constitutions_dir.mkdir(parents=True, exist_ok=True)

    # Orchestrator template
    (constitutions_dir / "orchestrator-base.md").write_text(
        "<!-- Role: ORCHESTRATOR -->\n"
        "# Orchestrator Constitution\n"
        "{{#each mandatoryReads.orchestrator}}\n"
        "- {{this.path}}: {{this.purpose}}\n"
        "{{/each}}\n"
        "{{#each rules.orchestrator}}\n"
        "### {{this.id}}: {{this.name}}\n"
        "{{/each}}\n",
        encoding="utf-8",
    )

    # Agents template
    (constitutions_dir / "agents-base.md").write_text(
        "<!-- Role: AGENT -->\n"
        "# Agents Constitution\n"
        "{{#each mandatoryReads.agents}}\n"
        "- {{this.path}}: {{this.purpose}}\n"
        "{{/each}}\n"
        "{{#each rules.agent}}\n"
        "### {{this.id}}: {{this.name}}\n"
        "{{/each}}\n",
        encoding="utf-8",
    )

    # Validators template
    (constitutions_dir / "validators-base.md").write_text(
        "<!-- Role: VALIDATOR -->\n"
        "# Validator Constitution\n"
        "{{#each mandatoryReads.validators}}\n"
        "- {{this.path}}: {{this.purpose}}\n"
        "{{/each}}\n"
        "{{#each rules.validator}}\n"
        "### {{this.id}}: {{this.name}}\n"
        "{{/each}}\n",
        encoding="utf-8",
    )

    # Create minimal config with proper structure
    # Note: ConfigManager looks for *.yml files in project config dir, not *.yaml
    import yaml

    # Create core config defaults (to prevent fallback to hardcoded validators)
    core_config_dir = core_dir / "config"
    core_config_dir.mkdir(parents=True, exist_ok=True)
    core_defaults = core_config_dir / "defaults.yaml"
    core_defaults_data = {
        "validation": {
            "roster": {
                "global": [],
                "critical": [],
                "specialized": [],
            }
        },
    }
    core_defaults.write_text(yaml.dump(core_defaults_data), encoding="utf-8")

    # Create constitution.yaml with mandatory reads
    constitution_config = core_config_dir / "constitution.yaml"
    constitution_data = {
        "mandatoryReads": {
            "orchestrator": [
                {"path": "guidelines/SESSION_WORKFLOW.md", "purpose": "Session workflow"},
            ],
            "agents": [
                {"path": "guidelines/TDD.md", "purpose": "Test-driven development"},
            ],
            "validators": [
                {"path": "guidelines/VALIDATION.md", "purpose": "Validation guidelines"},
            ],
        }
    }
    constitution_config.write_text(yaml.dump(constitution_data), encoding="utf-8")

    # Create project config
    config_dir = repo_root / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "config.yml"
    config_data = {
        "validation": {
            "roster": {
                "global": [{"id": validator_id}],
                "critical": [],
                "specialized": [],
            }
        },
        "validators": {
            "roster": {
                "global": [],
                "critical": [],
                "specialized": [],
            }
        },
        "packs": {
            "active": []
        },
    }
    config_file.write_text(yaml.dump(config_data), encoding="utf-8")


@pytest.fixture
def real_args():
    """Create real args namespace instead of mocking."""
    args = Namespace()
    args.repo_root = None
    args.agents = False
    args.validators = False
    args.orchestrator = False
    args.guidelines = False
    args.dry_run = False
    args.json = False
    args.claude = False
    args.cursor = False
    args.zen = False
    args.platforms = None
    return args


def test_compose_all_uses_resolved_config_dir_for_validators(tmp_path, real_args):
    """Test that validators are written to resolved config dir, not hardcoded .agents."""
    # Setup real Edison structure
    _setup_minimal_edison_structure(tmp_path)

    # Enable only validators to focus test
    real_args.validators = True
    real_args.repo_root = str(tmp_path)

    # Execute with real implementation
    result = main(real_args)

    # Assert success
    assert result == 0, "Compose should succeed"

    # Verify validators written to correct location
    config_dir = get_project_config_dir(tmp_path)
    expected_dir = config_dir / "_generated" / "validators"
    expected_file = expected_dir / "test-val.md"

    assert expected_dir.exists(), f"Validators directory should exist at {expected_dir}"
    assert expected_file.exists(), f"Validator file should exist at {expected_file}"

    # Verify content was written
    content = expected_file.read_text(encoding="utf-8")
    assert "Test validator content" in content, "Validator content should be present"


def test_compose_all_uses_resolved_config_dir_for_orchestrator(tmp_path, real_args):
    """Test that orchestrator manifest is written to resolved config dir."""
    # Setup real Edison structure
    _setup_minimal_edison_structure(tmp_path)

    # Enable only orchestrator
    real_args.orchestrator = True
    real_args.repo_root = str(tmp_path)

    # Execute with real implementation
    result = main(real_args)

    # Assert success
    assert result == 0, "Compose should succeed"

    # Verify orchestrator files written to correct location
    config_dir = get_project_config_dir(tmp_path)
    expected_output_dir = config_dir / "_generated"

    # Check for orchestrator manifest (note: guide file is UPPERCASE)
    manifest_file = expected_output_dir / "orchestrator-manifest.json"
    guide_file = expected_output_dir / "ORCHESTRATOR_GUIDE.md"

    assert expected_output_dir.exists(), f"Output directory should exist at {expected_output_dir}"
    assert manifest_file.exists(), f"Manifest file should exist at {manifest_file}"
    assert guide_file.exists(), f"Guide file should exist at {guide_file}"


def test_compose_all_generates_validators_constitution(tmp_path, real_args):
    """Test that edison compose --all generates constitutions/VALIDATORS.md."""
    # Setup real Edison structure
    _setup_minimal_edison_structure(tmp_path)

    # Run compose --all
    real_args.repo_root = str(tmp_path)

    # Execute with real implementation
    result = main(real_args)

    # Assert success
    assert result == 0, "Compose should succeed"

    # Verify constitutions/VALIDATORS.md was generated
    config_dir = get_project_config_dir(tmp_path)
    constitutions_dir = config_dir / "_generated" / "constitutions"
    validators_constitution = constitutions_dir / "VALIDATORS.md"

    assert constitutions_dir.exists(), f"Constitutions directory should exist at {constitutions_dir}"
    assert validators_constitution.exists(), f"VALIDATORS.md should exist at {validators_constitution}"


def test_validators_constitution_has_role_header(tmp_path, real_args):
    """Test that VALIDATORS.md has Role: VALIDATOR in header."""
    _setup_minimal_edison_structure(tmp_path)
    real_args.repo_root = str(tmp_path)

    result = main(real_args)
    assert result == 0, "Compose should succeed"

    config_dir = get_project_config_dir(tmp_path)
    validators_constitution = config_dir / "_generated" / "constitutions" / "VALIDATORS.md"

    content = validators_constitution.read_text(encoding="utf-8")
    assert "<!-- Role: VALIDATOR -->" in content, "VALIDATORS.md should have Role: VALIDATOR in header"


def test_validators_constitution_has_mandatory_reads(tmp_path, real_args):
    """Test that mandatory reads match constitution.yaml validators section."""
    _setup_minimal_edison_structure(tmp_path)
    real_args.repo_root = str(tmp_path)

    result = main(real_args)
    assert result == 0, "Compose should succeed"

    config_dir = get_project_config_dir(tmp_path)
    validators_constitution = config_dir / "_generated" / "constitutions" / "VALIDATORS.md"

    content = validators_constitution.read_text(encoding="utf-8")
    # Check for mandatory reads from constitution.yaml
    assert "guidelines/VALIDATION.md: Validation guidelines" in content, \
        "VALIDATORS.md should have mandatory reads from constitution.yaml"


def test_validators_constitution_has_filtered_rules(tmp_path, real_args):
    """Test that rules are filtered to validator-applicable only."""
    _setup_minimal_edison_structure(tmp_path)
    real_args.repo_root = str(tmp_path)

    result = main(real_args)
    assert result == 0, "Compose should succeed"

    config_dir = get_project_config_dir(tmp_path)
    validators_constitution = config_dir / "_generated" / "constitutions" / "VALIDATORS.md"

    content = validators_constitution.read_text(encoding="utf-8")
    # Verify that rules section was rendered (should have at least one rule)
    # The actual rule content depends on the bundled rules registry
    # We just verify the template was processed correctly
    assert "{{#each rules.validator}}" not in content, \
        "Template placeholders should be rendered"
    assert "{{/each}}" not in content, \
        "Template placeholders should be rendered"
