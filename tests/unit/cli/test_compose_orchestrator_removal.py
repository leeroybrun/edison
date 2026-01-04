"""Test that orchestrator manifest code is completely removed from CLI.

This test verifies that:
1. The --orchestrator flag no longer exists
2. The compose_all check doesn't reference orchestrator
3. Constitutions are generated instead of orchestrator manifest
"""
from argparse import ArgumentParser, Namespace
from pathlib import Path

import pytest
import yaml

from edison.cli.compose.all import main, register_args
from edison.core.utils.paths.project import get_project_config_dir
from tests.conftest import REPO_ROOT


def _setup_minimal_edison_structure(repo_root: Path) -> None:
    """Create minimal Edison structure needed for composition tests."""
    # Create core Edison structure
    core_dir = repo_root / ".edison" / "core"
    validators_dir = core_dir / "validators" / "global"
    validators_dir.mkdir(parents=True, exist_ok=True)

    # Create minimal validator spec
    validator_spec = validators_dir / "test.md"
    validator_spec.write_text(
        "# Core Edison Principles\n"
        "Test validator content.\n",
        encoding="utf-8",
    )

    # Create mandatory guideline files
    guidelines_dir = core_dir / "guidelines"
    guidelines_dir.mkdir(parents=True, exist_ok=True)

    # Create minimal guideline files with required anchors from rules registry
    guideline_contents = {
        "SESSION_WORKFLOW": (
            "# SESSION_WORKFLOW\n\n"
            "<!-- ANCHOR: context-budget -->\n"
            "Context budget guidelines.\n"
            "<!-- END ANCHOR: context-budget -->\n"
        ),
        "DELEGATION": (
            "# DELEGATION\n\n"
            "<!-- ANCHOR: priority-chain -->\n"
            "Test delegation content.\n"
            "<!-- END ANCHOR: priority-chain -->\n"
        ),
        "TDD": "# TDD\n\nTest guideline content.\n",
        "VALIDATION": (
            "# VALIDATION\n\n"
            "<!-- ANCHOR: validation-first -->\n"
            "Validation first guidelines.\n"
            "<!-- END ANCHOR: validation-first -->\n"
        ),
    }
    for guideline_name, content in guideline_contents.items():
        guideline_file = guidelines_dir / f"{guideline_name}.md"
        guideline_file.write_text(content, encoding="utf-8")

    # Create core config
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

    # Minimal state machine config
    state_machine_cfg = {
        "statemachine": {
            "task": {
                "states": {
                    "todo": {
                        "initial": True,
                        "allowed_transitions": [{"to": "wip"}],
                    },
                    "wip": {
                        "allowed_transitions": [{"to": "done"}],
                    },
                    "done": {
                        "final": True,
                        "allowed_transitions": [],
                    },
                }
            },
            "qa": {
                "states": {
                    "waiting": {
                        "initial": True,
                        "allowed_transitions": [{"to": "wip"}],
                    },
                    "wip": {
                        "allowed_transitions": [{"to": "done"}],
                    },
                    "done": {
                        "final": True,
                        "allowed_transitions": [],
                    },
                }
            },
            "session": {
                "states": {
                    "active": {
                        "initial": True,
                        "allowed_transitions": [{"to": "closing"}],
                    },
                    "closing": {
                        "allowed_transitions": [{"to": "validated"}],
                    },
                    "validated": {
                        "final": True,
                        "allowed_transitions": [],
                    },
                }
            },
        }
    }
    (core_config_dir / "state-machine.yaml").write_text(
        yaml.dump(state_machine_cfg),
        encoding="utf-8",
    )

    # Create constitution.yaml with new schema: constitutions.<role>.mandatoryReads/optionalReads
    constitution_config = core_config_dir / "constitution.yaml"
    constitution_data = {
        "version": "1.0.0",
        "constitutions": {
            "orchestrator": {
                "mandatoryReads": [
                    {"path": "guidelines/SESSION_WORKFLOW.md", "purpose": "Session workflow"},
                ],
                "optionalReads": [],
            },
            "agents": {
                "mandatoryReads": [
                    {"path": "guidelines/TDD.md", "purpose": "Test-driven development"},
                ],
                "optionalReads": [],
            },
            "validators": {
                "mandatoryReads": [
                    {"path": "guidelines/VALIDATION.md", "purpose": "Validation guidelines"},
                ],
                "optionalReads": [],
            },
        },
    }
    constitution_config.write_text(yaml.dump(constitution_data), encoding="utf-8")

    # Create project config
    config_dir = repo_root / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_file = config_dir / "config.yml"
    config_data = {
        "validation": {
            "roster": {
                "global": [{"id": "test-val"}],
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
    """Create real args namespace with all compose command flags."""
    args = Namespace()
    args.project_root = None
    args.validators = False
    args.constitutions = False
    args.guidelines = False
    args.agents = False
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
    args.pal = False
    args.platforms = None
    return args


def test_orchestrator_flag_does_not_exist():
    """FAILING TEST: The --orchestrator flag should NOT exist in CLI args."""
    parser = ArgumentParser()
    register_args(parser)

    # Parse help to get all registered arguments
    args_dict = {action.dest: action for action in parser._actions}

    # Verify orchestrator is NOT in the registered arguments
    assert "orchestrator" not in args_dict, \
        "The --orchestrator flag should be removed from CLI"


def test_compose_all_without_orchestrator_flag(tmp_path, real_args):
    """Test that compose --all works without orchestrator flag and generates constitutions."""
    _setup_minimal_edison_structure(tmp_path)
    real_args.project_root = str(tmp_path)

    # Run compose --all (which should NOT try to compose orchestrator)
    result = main(real_args)

    assert result == 0, "Compose should succeed without orchestrator code"

    # Verify constitutions were generated (replacement for orchestrator manifest)
    config_dir = get_project_config_dir(tmp_path)
    constitutions_dir = config_dir / "_generated" / "constitutions"
    orchestrators_constitution = constitutions_dir / "ORCHESTRATOR.md"

    assert constitutions_dir.exists(), f"Constitutions directory should exist at {constitutions_dir}"
    assert orchestrators_constitution.exists(), \
        "ORCHESTRATOR.md constitution should exist as replacement for orchestrator manifest"

    # Verify orchestrator-manifest.json is NOT generated (deprecated)
    manifest_file = config_dir / "_generated" / "orchestrator-manifest.json"
    assert not manifest_file.exists(), \
        "orchestrator-manifest.json should NOT be generated (replaced by constitutions)"


def test_compose_all_check_excludes_orchestrator():
    """Compose CLI should not mention the legacy orchestrator flag or special casing."""
    # Read the CLI source
    cli_path = REPO_ROOT / "src" / "edison" / "cli" / "compose" / "all.py"
    content = cli_path.read_text(encoding="utf-8")

    # The compose CLI is fully config-driven; it must not refer to a removed orchestrator flag.
    assert "--orchestrator" not in content
    assert "args.orchestrator" not in content
