"""Tests for evidence analysis functions."""
from pathlib import Path

import pytest

from edison.core.qa.evidence.analysis import missing_evidence_blockers
from edison.core.qa.evidence.service import EvidenceService
from edison.core.config.domains.qa import QAConfig


def test_missing_evidence_blockers_uses_config(isolated_project_env: Path):
    """Test that missing_evidence_blockers loads required files from config."""
    # Setup: Create task evidence structure
    task_id = "test-task-001"

    # Create real evidence directory structure
    pm_paths_root = isolated_project_env / ".project"
    evidence_root = pm_paths_root / "qa" / "validation-evidence" / task_id
    round_1 = evidence_root / "round-1"
    round_1.mkdir(parents=True)

    # Create one file present, others missing
    (round_1 / "command-type-check.txt").write_text("type check output")

    # Create custom config with custom required files
    config_dir = isolated_project_env / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "qa.yaml"
    config_file.write_text("""
validation:
  evidence:
    requiredFiles:
      - command-type-check.txt
      - command-lint.txt
      - command-test.txt
      - command-build.txt
""")

    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    # Act - use real EvidenceService and QAConfig
    blockers = missing_evidence_blockers(task_id)

    # Assert
    assert len(blockers) == 1
    blocker = blockers[0]
    assert blocker["kind"] == "automation"
    assert blocker["recordId"] == task_id
    assert "Missing evidence files" in blocker["message"]
    assert "command-lint.txt" in blocker["message"]
    assert "command-test.txt" in blocker["message"]
    assert "command-build.txt" in blocker["message"]
    assert "command-type-check.txt" not in blocker["message"]  # This one exists


def test_missing_evidence_blockers_uses_fallback_defaults(isolated_project_env: Path):
    """Test that missing_evidence_blockers uses fallback defaults if config not available."""
    # Setup
    task_id = "test-task-002"

    # Create real evidence directory structure
    pm_paths_root = isolated_project_env / ".project"
    evidence_root = pm_paths_root / "qa" / "validation-evidence" / task_id
    round_1 = evidence_root / "round-1"
    round_1.mkdir(parents=True)

    # Create no evidence files - this will trigger the missing files blocker

    # Act - Real config will use defaults from bundled validators.yaml
    blockers = missing_evidence_blockers(task_id)

    # Assert - should use default values from bundled config
    assert len(blockers) == 1
    blocker = blockers[0]
    assert "Missing evidence files" in blocker["message"]
    # Should mention the default files
    assert "command-type-check.txt" in blocker["message"]
    assert "command-lint.txt" in blocker["message"]
    assert "command-test.txt" in blocker["message"]
    assert "command-build.txt" in blocker["message"]


def test_missing_evidence_blockers_custom_files_in_config(isolated_project_env: Path):
    """Test that custom required files from config are properly used."""
    # Setup
    task_id = "test-task-003"

    # Create real evidence directory structure
    pm_paths_root = isolated_project_env / ".project"
    evidence_root = pm_paths_root / "qa" / "validation-evidence" / task_id
    round_1 = evidence_root / "round-1"
    round_1.mkdir(parents=True)

    # Create one custom file
    (round_1 / "custom-check.txt").write_text("custom output")

    # Create custom config with different required files
    config_dir = isolated_project_env / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "qa.yaml"
    config_file.write_text("""
validation:
  evidence:
    requiredFiles:
      - custom-check.txt
      - custom-test.txt
      - custom-build.txt
""")

    # Clear config cache to ensure our custom config is loaded
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    # Act - use real QAConfig which will load our custom config
    blockers = missing_evidence_blockers(task_id)

    # Assert
    assert len(blockers) == 1
    blocker = blockers[0]
    assert "Missing evidence files" in blocker["message"]
    assert "custom-test.txt" in blocker["message"]
    assert "custom-build.txt" in blocker["message"]
    assert "custom-check.txt" not in blocker["message"]  # This exists


def test_missing_evidence_blockers_no_evidence_dir(isolated_project_env: Path):
    """Test blocker when evidence directory doesn't exist."""
    task_id = "test-task-004"

    # Don't create evidence directory - it should be missing

    # Act
    blockers = missing_evidence_blockers(task_id)

    # Assert
    assert len(blockers) == 1
    blocker = blockers[0]
    assert blocker["kind"] == "automation"
    assert blocker["recordId"] == task_id
    assert "Evidence dir missing" in blocker["message"]
    assert blocker.get("fixCmd") == ["edison", "evidence", "init", task_id]


def test_missing_evidence_blockers_no_rounds(isolated_project_env: Path):
    """Test blocker when evidence directory exists but has no rounds."""
    task_id = "test-task-005"

    # Create evidence directory but no round directories
    pm_paths_root = isolated_project_env / ".project"
    evidence_root = pm_paths_root / "qa" / "validation-evidence" / task_id
    evidence_root.mkdir(parents=True)

    # Act
    blockers = missing_evidence_blockers(task_id)

    # Assert
    assert len(blockers) == 1
    blocker = blockers[0]
    assert blocker["kind"] == "automation"
    assert blocker["recordId"] == task_id
    assert "No round-* directories present" in blocker["message"]
    assert blocker.get("fixCmd") == ["edison", "evidence", "init", task_id]


def test_missing_evidence_blockers_all_files_present(isolated_project_env: Path):
    """Test no blockers when all required files are present."""
    task_id = "test-task-006"

    # Create real evidence directory structure
    pm_paths_root = isolated_project_env / ".project"
    evidence_root = pm_paths_root / "qa" / "validation-evidence" / task_id
    round_1 = evidence_root / "round-1"
    round_1.mkdir(parents=True)

    # Create ALL default required files
    (round_1 / "command-type-check.txt").write_text("type check output")
    (round_1 / "command-lint.txt").write_text("lint output")
    (round_1 / "command-test.txt").write_text("test output")
    (round_1 / "command-build.txt").write_text("build output")

    # Act
    blockers = missing_evidence_blockers(task_id)

    # Assert - no blockers
    assert len(blockers) == 0


def test_evidence_service_real_behavior(isolated_project_env: Path):
    """Test EvidenceService with real file operations."""
    task_id = "test-task-007"

    # Create real EvidenceService
    service = EvidenceService(task_id, project_root=isolated_project_env)

    # Verify evidence root path
    evidence_root = service.get_evidence_root()
    assert task_id in str(evidence_root)
    assert "validation-evidence" in str(evidence_root)

    # Create a round
    round_1 = service.ensure_round()
    assert round_1.exists()
    assert round_1.name == "round-1"

    # List rounds
    rounds = service.list_rounds()
    assert len(rounds) == 1
    assert rounds[0] == round_1

    # Create another round
    round_2 = service.create_next_round()
    assert round_2.exists()
    assert round_2.name == "round-2"

    # List rounds again
    rounds = service.list_rounds()
    assert len(rounds) == 2
    assert rounds[0].name == "round-1"
    assert rounds[1].name == "round-2"

    # Get current round
    current_num = service.get_current_round()
    assert current_num == 2

    current_dir = service.get_current_round_dir()
    assert current_dir == round_2


def test_qa_config_real_behavior(isolated_project_env: Path):
    """Test QAConfig with real configuration loading."""
    # Create custom config
    config_dir = isolated_project_env / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "qa.yaml"
    config_file.write_text("""
validation:
  evidence:
    requiredFiles:
      - custom-file-1.txt
      - custom-file-2.txt
  execution:
    mode: parallel
    concurrency: 8
""")

    # Clear config cache
    from edison.core.config.cache import clear_all_caches
    clear_all_caches()

    # Load real config
    qa_config = QAConfig(repo_root=isolated_project_env)

    # Verify custom required files are loaded
    required_files = qa_config.get_required_evidence_files()
    assert "custom-file-1.txt" in required_files
    assert "custom-file-2.txt" in required_files

    # Verify validation config is accessible
    validation_config = qa_config.get_validation_config()
    assert isinstance(validation_config, dict)
    assert "evidence" in validation_config


def test_missing_evidence_blockers_multiple_rounds(isolated_project_env: Path):
    """Test that missing_evidence_blockers checks the latest round."""
    task_id = "test-task-008"

    # Create real evidence directory structure with multiple rounds
    pm_paths_root = isolated_project_env / ".project"
    evidence_root = pm_paths_root / "qa" / "validation-evidence" / task_id
    round_1 = evidence_root / "round-1"
    round_2 = evidence_root / "round-2"
    round_1.mkdir(parents=True)
    round_2.mkdir(parents=True)

    # Round 1 has all files
    (round_1 / "command-type-check.txt").write_text("type check output")
    (round_1 / "command-lint.txt").write_text("lint output")
    (round_1 / "command-test.txt").write_text("test output")
    (round_1 / "command-build.txt").write_text("build output")

    # Round 2 has only one file - this should be checked
    (round_2 / "command-type-check.txt").write_text("type check output")

    # Act
    blockers = missing_evidence_blockers(task_id)

    # Assert - should report missing files from round-2 (latest)
    assert len(blockers) == 1
    blocker = blockers[0]
    assert "round-2" in blocker["message"]
    assert "command-lint.txt" in blocker["message"]
    assert "command-test.txt" in blocker["message"]
    assert "command-build.txt" in blocker["message"]
