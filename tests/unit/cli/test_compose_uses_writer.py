"""Test that compose commands use CompositionFileWriter instead of direct write_text.

Following TDD principle: Write tests FIRST to verify that composition uses the unified writer.
"""
import pytest
from pathlib import Path
from argparse import Namespace
from unittest.mock import patch, MagicMock
from edison.cli.compose.all import main
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.utils.paths.project import get_project_config_dir


def _setup_minimal_edison_structure(repo_root: Path) -> None:
    """Create minimal Edison structure needed for composition tests."""
    import yaml

    # Create core Edison structure
    core_dir = repo_root / ".edison" / "core"
    validators_dir = core_dir / "validators" / "global"
    validators_dir.mkdir(parents=True, exist_ok=True)

    # Create minimal validator spec
    validator_spec = validators_dir / "test.md"
    validator_spec.write_text(
        "# Test Validator\nTest validator content.\n",
        encoding="utf-8",
    )

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
def compose_args():
    """Create args namespace for compose command."""
    args = Namespace()
    args.repo_root = None
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
    args.documents = False
    args.dry_run = False
    args.json = False
    args.claude = False
    args.cursor = False
    args.zen = False
    args.platforms = None
    return args


def test_compose_agents_uses_composition_file_writer(tmp_path, compose_args):
    """Test that agent composition uses CompositionFileWriter.write_text."""
    _setup_minimal_edison_structure(tmp_path)
    compose_args.agents = True
    compose_args.repo_root = str(tmp_path)

    # Track all write_text calls
    original_write_text = CompositionFileWriter.write_text
    write_calls = []

    def track_write_text(self, path, content, encoding=None):
        write_calls.append((path, content, encoding))
        return original_write_text(self, path, content, encoding)

    with patch.object(CompositionFileWriter, 'write_text', track_write_text):
        result = main(compose_args)

    assert result == 0, "Compose should succeed"
    # Verify that CompositionFileWriter.write_text was called (not Path.write_text directly)
    assert len(write_calls) > 0, "CompositionFileWriter.write_text should be called for agents"


def test_compose_guidelines_uses_composition_file_writer(tmp_path, compose_args):
    """Test that guideline composition uses CompositionFileWriter.write_text."""
    _setup_minimal_edison_structure(tmp_path)

    # Create a test guideline file
    core_guidelines_dir = tmp_path / ".edison" / "core" / "guidelines"
    core_guidelines_dir.mkdir(parents=True, exist_ok=True)
    test_guideline = core_guidelines_dir / "TEST_GUIDELINE.md"
    test_guideline.write_text("# Test Guideline\nThis is a test guideline.\n", encoding="utf-8")

    compose_args.guidelines = True
    compose_args.repo_root = str(tmp_path)

    # Track all write_text calls
    original_write_text = CompositionFileWriter.write_text
    write_calls = []

    def track_write_text(self, path, content, encoding=None):
        write_calls.append((path, content, encoding))
        return original_write_text(self, path, content, encoding)

    with patch.object(CompositionFileWriter, 'write_text', track_write_text):
        result = main(compose_args)

    assert result == 0, "Compose should succeed"
    # Verify that CompositionFileWriter.write_text was called
    assert len(write_calls) > 0, "CompositionFileWriter.write_text should be called for guidelines"


def test_compose_validators_uses_composition_file_writer(tmp_path, compose_args):
    """Test that validator composition uses CompositionFileWriter.write_text."""
    _setup_minimal_edison_structure(tmp_path)
    compose_args.validators = True
    compose_args.repo_root = str(tmp_path)

    # Track all write_text calls
    original_write_text = CompositionFileWriter.write_text
    write_calls = []

    def track_write_text(self, path, content, encoding=None):
        write_calls.append((path, content, encoding))
        return original_write_text(self, path, content, encoding)

    with patch.object(CompositionFileWriter, 'write_text', track_write_text):
        result = main(compose_args)

    assert result == 0, "Compose should succeed"
    # Verify that CompositionFileWriter.write_text was called
    assert len(write_calls) > 0, "CompositionFileWriter.write_text should be called for validators"


def test_compose_start_uses_composition_file_writer(tmp_path, compose_args):
    """Test that start prompt composition uses CompositionFileWriter.write_text."""
    _setup_minimal_edison_structure(tmp_path)
    compose_args.start = True
    compose_args.repo_root = str(tmp_path)

    # Track all write_text calls
    original_write_text = CompositionFileWriter.write_text
    write_calls = []

    def track_write_text(self, path, content, encoding=None):
        write_calls.append((path, content, encoding))
        return original_write_text(self, path, content, encoding)

    with patch.object(CompositionFileWriter, 'write_text', track_write_text):
        result = main(compose_args)

    assert result == 0, "Compose should succeed"
    # Verify that CompositionFileWriter.write_text was called
    assert len(write_calls) > 0, "CompositionFileWriter.write_text should be called for start prompts"


def test_compose_clients_uses_composition_file_writer(tmp_path, compose_args):
    """Test that client file composition uses CompositionFileWriter.write_text."""
    _setup_minimal_edison_structure(tmp_path)
    # compose_all_types=True triggers client composition
    compose_args.repo_root = str(tmp_path)

    # Track all write_text calls
    original_write_text = CompositionFileWriter.write_text
    write_calls = []

    def track_write_text(self, path, content, encoding=None):
        write_calls.append((path, content, encoding))
        return original_write_text(self, path, content, encoding)

    with patch.object(CompositionFileWriter, 'write_text', track_write_text):
        result = main(compose_args)

    assert result == 0, "Compose should succeed"
    # Verify that CompositionFileWriter.write_text was called
    # (Client composition is part of compose_all_types)
    assert len(write_calls) > 0, "CompositionFileWriter.write_text should be called for clients"
