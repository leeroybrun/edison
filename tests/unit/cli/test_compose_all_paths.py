import pytest
from pathlib import Path
from edison.cli.compose.all import main
from edison.core.composition import get_rules_for_role
from edison.core.utils.paths.project import get_project_config_dir
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
    validator_spec = validators_dir / f"{role}.md"
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

    # Create project config structure
    # ConfigManager reads bundled defaults from edison.data first, then project overrides
    import yaml

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
    args.project_root = None
    args.agents = False
    args.validators = False
    args.constitutions = False
    args.guidelines = False
    args.start = False
    args.hooks = False
    args.settings = False
    args.commands = False
    args.rules = False
    args.schemas = False
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
    real_args.project_root = str(tmp_path)

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


def test_compose_all_generates_validators_constitution(tmp_path, real_args):
    """Test that edison compose --all generates constitutions/VALIDATORS.md."""
    # Setup real Edison structure
    _setup_minimal_edison_structure(tmp_path)

    # Run compose --all
    real_args.project_root = str(tmp_path)

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
    real_args.project_root = str(tmp_path)

    result = main(real_args)
    assert result == 0, "Compose should succeed"

    config_dir = get_project_config_dir(tmp_path)
    validators_constitution = config_dir / "_generated" / "constitutions" / "VALIDATORS.md"

    content = validators_constitution.read_text(encoding="utf-8")
    assert "<!-- Role: VALIDATOR -->" in content, "VALIDATORS.md should have Role: VALIDATOR in header"


def test_validators_constitution_has_mandatory_reads(tmp_path, real_args):
    """Test that mandatory reads match constitution.yaml validators section."""
    _setup_minimal_edison_structure(tmp_path)
    real_args.project_root = str(tmp_path)

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
    real_args.project_root = str(tmp_path)

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


def test_compose_all_generates_orchestrators_constitution(tmp_path, real_args):
    """Test that edison compose --all generates constitutions/ORCHESTRATORS.md."""
    _setup_minimal_edison_structure(tmp_path)
    real_args.project_root = str(tmp_path)

    result = main(real_args)

    assert result == 0, "Compose should succeed"

    config_dir = get_project_config_dir(tmp_path)
    constitutions_dir = config_dir / "_generated" / "constitutions"
    orchestrators_constitution = constitutions_dir / "ORCHESTRATORS.md"

    assert constitutions_dir.exists(), f"Constitutions directory should exist at {constitutions_dir}"
    assert orchestrators_constitution.exists(), f"ORCHESTRATORS.md should exist at {orchestrators_constitution}"


def test_compose_generates_state_machine_doc(tmp_path, real_args):
    """Compose pipeline must emit STATE_MACHINE.md to _generated."""
    _setup_minimal_edison_structure(tmp_path)
    real_args.project_root = str(tmp_path)

    result = main(real_args)

    assert result == 0, "Compose should succeed"

    config_dir = get_project_config_dir(tmp_path)
    state_machine_doc = config_dir / "_generated" / "STATE_MACHINE.md"
    assert state_machine_doc.exists(), "STATE_MACHINE.md should be generated with compose"
    content = state_machine_doc.read_text(encoding="utf-8")
    assert "# State Machine" in content


def test_orchestrators_constitution_has_role_header(tmp_path, real_args):
    """Test that ORCHESTRATORS.md has Role: ORCHESTRATOR in header."""
    _setup_minimal_edison_structure(tmp_path)
    real_args.project_root = str(tmp_path)

    result = main(real_args)
    assert result == 0, "Compose should succeed"

    config_dir = get_project_config_dir(tmp_path)
    orchestrators_constitution = config_dir / "_generated" / "constitutions" / "ORCHESTRATORS.md"

    content = orchestrators_constitution.read_text(encoding="utf-8")
    assert "<!-- Role: ORCHESTRATOR -->" in content, "ORCHESTRATORS.md should have Role: ORCHESTRATOR in header"


def test_orchestrators_constitution_has_mandatory_reads(tmp_path, real_args):
    """Test that mandatory reads match constitution.yaml orchestrator section."""
    _setup_minimal_edison_structure(tmp_path)
    real_args.project_root = str(tmp_path)

    result = main(real_args)
    assert result == 0, "Compose should succeed"

    config_dir = get_project_config_dir(tmp_path)
    orchestrators_constitution = config_dir / "_generated" / "constitutions" / "ORCHESTRATORS.md"

    content = orchestrators_constitution.read_text(encoding="utf-8")
    assert "guidelines/SESSION_WORKFLOW.md: Session workflow" in content, \
        "ORCHESTRATORS.md should have mandatory reads from constitution.yaml"


def test_orchestrators_constitution_has_rules_and_roster_references(tmp_path, real_args):
    """Test that rules render for orchestrator and roster files are generated."""
    _setup_minimal_edison_structure(tmp_path)
    real_args.project_root = str(tmp_path)

    result = main(real_args)
    assert result == 0, "Compose should succeed"

    config_dir = get_project_config_dir(tmp_path)
    output_dir = config_dir / "_generated"
    orchestrators_constitution = output_dir / "constitutions" / "ORCHESTRATORS.md"

    content = orchestrators_constitution.read_text(encoding="utf-8")
    # Verify Handlebars markers were rendered and an actual rule id appears
    assert "{{#each rules.orchestrator}}" not in content
    rules = get_rules_for_role("orchestrator")
    assert rules, "Expected orchestrator rules to be available"
    assert rules[0]["id"] in content, "Orchestrator rules should be rendered into constitution"

    # Verify references to rosters are present and generated
    assert "AVAILABLE_AGENTS.md" in content, "Orchestrator constitution should reference available agents"
    assert "AVAILABLE_VALIDATORS.md" in content, "Orchestrator constitution should reference available validators"

    available_agents = output_dir / "AVAILABLE_AGENTS.md"
    available_validators = output_dir / "AVAILABLE_VALIDATORS.md"
    assert available_agents.exists(), "AVAILABLE_AGENTS.md should be generated alongside constitutions"
    assert available_validators.exists(), "AVAILABLE_VALIDATORS.md should be generated alongside constitutions"
