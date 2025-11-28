"""Tests for QAManager facade."""
from __future__ import annotations

import pytest
from pathlib import Path
from typing import Any, Dict

from edison.core.qa.manager import QAManager
from edison.core.utils.paths import PathResolver


@pytest.fixture
def qa_manager(tmp_path: Path, monkeypatch) -> QAManager:
    """Fixture providing a QAManager with isolated project root."""
    # Set environment for PathResolver
    monkeypatch.setenv("project_ROOT", str(tmp_path))
    # Create .project directory structure
    (tmp_path / ".project" / "qa" / "validation-evidence").mkdir(parents=True, exist_ok=True)
    return QAManager(project_root=tmp_path)


@pytest.fixture
def task_id() -> str:
    """Standard test task ID."""
    return "task-100"


class TestQAManagerInit:
    """Test QAManager initialization."""

    def test_init_with_project_root(self, tmp_path: Path):
        """QAManager should accept explicit project_root."""
        mgr = QAManager(project_root=tmp_path)
        assert mgr.project_root == tmp_path

    def test_init_without_project_root(self, tmp_path: Path, monkeypatch):
        """QAManager should resolve project_root from PathResolver when not provided."""
        # When no project_root provided, PathResolver is used
        # We can't easily override PathResolver without monkeypatching,
        # so just verify it's set to something valid
        mgr = QAManager()
        assert mgr.project_root is not None
        assert isinstance(mgr.project_root, Path)


class TestQAManagerCreateRound:
    """Test create_round operation."""

    def test_create_first_round(self, qa_manager: QAManager, task_id: str):
        """Should create round-1 directory for new task."""
        round_dir = qa_manager.create_round(task_id)

        assert round_dir.exists()
        assert round_dir.is_dir()
        assert round_dir.name == "round-1"
        assert task_id in str(round_dir)

    def test_create_second_round(self, qa_manager: QAManager, task_id: str):
        """Should create round-2 when round-1 exists."""
        # Create round-1
        round_1 = qa_manager.create_round(task_id)
        assert round_1.name == "round-1"

        # Create round-2
        round_2 = qa_manager.create_round(task_id)
        assert round_2.exists()
        assert round_2.name == "round-2"

    def test_create_round_returns_path(self, qa_manager: QAManager, task_id: str):
        """Should return Path to created round directory."""
        round_dir = qa_manager.create_round(task_id)
        assert isinstance(round_dir, Path)


class TestQAManagerGetLatestRound:
    """Test get_latest_round operation."""

    def test_get_latest_round_when_none_exist(self, qa_manager: QAManager, task_id: str):
        """Should return None when no rounds exist."""
        latest = qa_manager.get_latest_round(task_id)
        assert latest is None

    def test_get_latest_round_with_single_round(self, qa_manager: QAManager, task_id: str):
        """Should return round-1 when only one round exists."""
        qa_manager.create_round(task_id)
        latest = qa_manager.get_latest_round(task_id)

        assert latest is not None
        assert latest == 1

    def test_get_latest_round_with_multiple_rounds(self, qa_manager: QAManager, task_id: str):
        """Should return highest round number when multiple rounds exist."""
        qa_manager.create_round(task_id)  # round-1
        qa_manager.create_round(task_id)  # round-2
        qa_manager.create_round(task_id)  # round-3

        latest = qa_manager.get_latest_round(task_id)
        assert latest == 3


class TestQAManagerGetRoundDir:
    """Test get_round_dir operation."""

    def test_get_round_dir_for_existing_round(self, qa_manager: QAManager, task_id: str):
        """Should return path to specific round directory."""
        qa_manager.create_round(task_id)
        qa_manager.create_round(task_id)

        round_1_dir = qa_manager.get_round_dir(task_id, round_num=1)
        assert round_1_dir.exists()
        assert round_1_dir.name == "round-1"

    def test_get_round_dir_for_nonexistent_round(self, qa_manager: QAManager, task_id: str):
        """Should return None for non-existent round."""
        round_dir = qa_manager.get_round_dir(task_id, round_num=99)
        assert round_dir is None

    def test_get_round_dir_latest_when_no_round_specified(self, qa_manager: QAManager, task_id: str):
        """Should return latest round when round_num is None."""
        qa_manager.create_round(task_id)  # round-1
        qa_manager.create_round(task_id)  # round-2

        latest_dir = qa_manager.get_round_dir(task_id)
        assert latest_dir is not None
        assert latest_dir.name == "round-2"


class TestQAManagerListRounds:
    """Test list_rounds operation."""

    def test_list_rounds_when_none_exist(self, qa_manager: QAManager, task_id: str):
        """Should return empty list when no rounds exist."""
        rounds = qa_manager.list_rounds(task_id)
        assert rounds == []

    def test_list_rounds_with_multiple_rounds(self, qa_manager: QAManager, task_id: str):
        """Should return all round directories sorted."""
        qa_manager.create_round(task_id)  # round-1
        qa_manager.create_round(task_id)  # round-2
        qa_manager.create_round(task_id)  # round-3

        rounds = qa_manager.list_rounds(task_id)
        assert len(rounds) == 3
        assert all(isinstance(r, Path) for r in rounds)
        assert rounds[0].name == "round-1"
        assert rounds[1].name == "round-2"
        assert rounds[2].name == "round-3"


class TestQAManagerWriteReport:
    """Test write_report operation."""

    def test_write_bundle_summary(self, qa_manager: QAManager, task_id: str):
        """Should write bundle-approved.json to latest round."""
        qa_manager.create_round(task_id)

        bundle_data = {
            "approved": True,
            "taskId": task_id,
            "validators": ["global-claude"]
        }

        qa_manager.write_report(task_id, "bundle", bundle_data)

        # Verify file was written
        latest_dir = qa_manager.get_round_dir(task_id)
        bundle_file = latest_dir / "bundle-approved.json"
        assert bundle_file.exists()

    def test_write_implementation_report(self, qa_manager: QAManager, task_id: str):
        """Should write implementation-report.json to latest round."""
        qa_manager.create_round(task_id)

        impl_data = {
            "taskId": task_id,
            "implementer": "test-agent",
            "status": "completed"
        }

        qa_manager.write_report(task_id, "implementation", impl_data)

        # Verify file was written
        latest_dir = qa_manager.get_round_dir(task_id)
        impl_file = latest_dir / "implementation-report.json"
        assert impl_file.exists()

    def test_write_validator_report(self, qa_manager: QAManager, task_id: str):
        """Should write validator-{name}-report.json to latest round."""
        qa_manager.create_round(task_id)

        validator_data = {
            "validatorName": "global-claude",
            "verdict": "approved",
            "score": 9.5
        }

        qa_manager.write_report(task_id, "validator", validator_data, validator_name="global-claude")

        # Verify file was written
        latest_dir = qa_manager.get_round_dir(task_id)
        validator_file = latest_dir / "validator-global-claude-report.json"
        assert validator_file.exists()

    def test_write_report_to_specific_round(self, qa_manager: QAManager, task_id: str):
        """Should write report to specific round when round_num provided."""
        qa_manager.create_round(task_id)  # round-1
        qa_manager.create_round(task_id)  # round-2

        data = {"test": "data"}
        qa_manager.write_report(task_id, "implementation", data, round_num=1)

        # Verify file was written to round-1
        round_1_dir = qa_manager.get_round_dir(task_id, round_num=1)
        impl_file = round_1_dir / "implementation-report.json"
        assert impl_file.exists()


class TestQAManagerReadReport:
    """Test read_report operation."""

    def test_read_bundle_summary(self, qa_manager: QAManager, task_id: str):
        """Should read bundle-approved.json from latest round."""
        qa_manager.create_round(task_id)

        bundle_data = {
            "approved": True,
            "taskId": task_id,
            "validators": ["global-claude"]
        }
        qa_manager.write_report(task_id, "bundle", bundle_data)

        # Read it back
        result = qa_manager.read_report(task_id, "bundle")
        assert result["approved"] is True
        assert result["taskId"] == task_id

    def test_read_implementation_report(self, qa_manager: QAManager, task_id: str):
        """Should read implementation-report.json from latest round."""
        qa_manager.create_round(task_id)

        impl_data = {"taskId": task_id, "status": "completed"}
        qa_manager.write_report(task_id, "implementation", impl_data)

        result = qa_manager.read_report(task_id, "implementation")
        assert result["status"] == "completed"

    def test_read_validator_report(self, qa_manager: QAManager, task_id: str):
        """Should read validator report from latest round."""
        qa_manager.create_round(task_id)

        validator_data = {"verdict": "approved"}
        qa_manager.write_report(task_id, "validator", validator_data, validator_name="global-claude")

        result = qa_manager.read_report(task_id, "validator", validator_name="global-claude")
        assert result["verdict"] == "approved"

    def test_read_nonexistent_report_returns_empty_dict(self, qa_manager: QAManager, task_id: str):
        """Should return empty dict when report doesn't exist."""
        result = qa_manager.read_report(task_id, "bundle")
        assert result == {}

    def test_read_report_from_specific_round(self, qa_manager: QAManager, task_id: str):
        """Should read report from specific round when round_num provided."""
        qa_manager.create_round(task_id)  # round-1
        qa_manager.create_round(task_id)  # round-2

        data_r1 = {"round": 1}
        data_r2 = {"round": 2}
        qa_manager.write_report(task_id, "implementation", data_r1, round_num=1)
        qa_manager.write_report(task_id, "implementation", data_r2, round_num=2)

        result = qa_manager.read_report(task_id, "implementation", round_num=1)
        assert result["round"] == 1


class TestQAManagerListValidatorReports:
    """Test list_validator_reports operation."""

    def test_list_validator_reports_when_none_exist(self, qa_manager: QAManager, task_id: str):
        """Should return empty list when no validator reports exist."""
        qa_manager.create_round(task_id)
        reports = qa_manager.list_validator_reports(task_id)
        assert reports == []

    def test_list_validator_reports_with_multiple_validators(self, qa_manager: QAManager, task_id: str):
        """Should return all validator report paths."""
        qa_manager.create_round(task_id)

        # Write multiple validator reports
        qa_manager.write_report(task_id, "validator", {"v": 1}, validator_name="global-claude")
        qa_manager.write_report(task_id, "validator", {"v": 2}, validator_name="codex-security")

        reports = qa_manager.list_validator_reports(task_id)
        assert len(reports) == 2
        assert all(isinstance(r, Path) for r in reports)
        assert any("global-claude" in r.name for r in reports)
        assert any("codex-security" in r.name for r in reports)
