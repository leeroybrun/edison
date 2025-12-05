"""Tests for QA round management via QARepository.

P2-QA-001: Refactor qa/round.py to use QAManager/QARepository
"""
import pytest
from helpers.io_utils import write_yaml
from helpers.fixtures import create_qa_file
import importlib
from pathlib import Path
from edison.core.qa.workflow.repository import QARepository
from edison.core.entity import EntityMetadata
from edison.core.qa.models import QARecord
from tests.helpers.env_setup import setup_project_root
from tests.helpers.fixtures import create_repo_with_git
from tests.helpers.cache_utils import reset_edison_caches


@pytest.fixture
def repo_env(tmp_path, monkeypatch):
    """Setup a repository environment with configuration."""
    from tests.helpers.fixtures import create_repo_with_git
    repo = create_repo_with_git(tmp_path)
    config_dir = repo / ".edison" / "config"

    # defaults.yaml with QA states
    write_yaml(
        config_dir / "defaults.yaml",
        {
            "statemachine": {
                "qa": {
                    "states": {
                        "waiting": {"initial": True, "allowed_transitions": [{"to": "todo", "guard": "always_allow"}]},
                        "todo": {"allowed_transitions": [{"to": "wip", "guard": "always_allow"}]},
                        "wip": {"allowed_transitions": [{"to": "done", "guard": "always_allow"}, {"to": "todo", "guard": "always_allow"}]},
                        "done": {"allowed_transitions": [{"to": "validated", "guard": "always_allow"}]},
                        "validated": {"final": True, "allowed_transitions": []},
                    }
                }
            }
        },
    )

    # tasks.yaml with paths
    write_yaml(
        config_dir / "tasks.yaml",
        {
            "tasks": {
                "paths": {
                    "root": ".project/tasks",
                    "qaRoot": ".project/qa",
                    "metaRoot": ".project/tasks/meta",
                    "template": ".project/tasks/TEMPLATE.md",
                },
            }
        },
    )

    # workflow.yaml
    write_yaml(
        config_dir / "workflow.yaml",
        {
            "version": "1.0",
            "statemachine": {
                "qa": {
                    "states": {
                        "waiting": {"initial": True, "allowed_transitions": [{"to": "todo", "guard": "always_allow"}]},
                        "todo": {"allowed_transitions": [{"to": "wip", "guard": "always_allow"}]},
                        "wip": {"allowed_transitions": [{"to": "done", "guard": "always_allow"}, {"to": "todo", "guard": "always_allow"}]},
                        "done": {"allowed_transitions": [{"to": "validated", "guard": "always_allow"}]},
                        "validated": {"final": True, "allowed_transitions": []},
                    }
                }
            }
        }
    )

    setup_project_root(monkeypatch, repo)
    reset_edison_caches()

    import edison.core.config.domains.task as task_config
    importlib.reload(task_config)
    import edison.core.config.domains.workflow as wf
    importlib.reload(wf)

    return repo


class TestQARoundManagement:
    """Test QARepository round management methods."""

    def test_append_round_increments_round_number(self, repo_env):
        """Test append_round increments the round number."""
        qa_id = "T-1-qa"
        task_id = "T-1"

        # Create QA in wip state with round 1
        create_qa_file(repo_env, qa_id, task_id, state="wip")

        repo = QARepository(project_root=repo_env)
        qa = repo.get(qa_id)
        assert qa.round == 1

        # Append a new round
        updated_qa = repo.append_round(qa_id, status="rejected")

        # Assert - round incremented
        assert updated_qa.round == 2

        # Verify persisted
        reloaded = repo.get(qa_id)
        assert reloaded.round == 2

    def test_append_round_with_status(self, repo_env):
        """Test append_round records the status."""
        qa_id = "T-2-qa"
        task_id = "T-2"

        create_qa_file(repo_env, qa_id, task_id, state="wip")

        repo = QARepository(project_root=repo_env)

        # Append round with status
        updated_qa = repo.append_round(qa_id, status="approved")

        # Assert round history contains status
        assert len(updated_qa.round_history) > 0
        latest = updated_qa.round_history[-1]
        assert latest["status"] == "approved"

    def test_append_round_with_notes(self, repo_env):
        """Test append_round can include notes."""
        qa_id = "T-3-qa"
        task_id = "T-3"

        create_qa_file(repo_env, qa_id, task_id, state="wip")

        repo = QARepository(project_root=repo_env)

        # Append round with notes
        updated_qa = repo.append_round(
            qa_id, 
            status="rejected",
            notes="validators: context7, code-reviewer"
        )

        # Assert notes recorded
        latest = updated_qa.round_history[-1]
        assert "validators" in latest.get("notes", "")

    def test_append_round_multiple_times(self, repo_env):
        """Test appending multiple rounds."""
        qa_id = "T-4-qa"
        task_id = "T-4"

        create_qa_file(repo_env, qa_id, task_id, state="wip")

        repo = QARepository(project_root=repo_env)

        # Append round 2
        qa = repo.append_round(qa_id, status="rejected", notes="First rejection")
        assert qa.round == 2

        # Append round 3
        qa = repo.append_round(qa_id, status="rejected", notes="Second rejection")
        assert qa.round == 3

        # Append round 4
        qa = repo.append_round(qa_id, status="approved")
        assert qa.round == 4

        # Verify history
        assert len(qa.round_history) == 3  # 3 appended rounds

    def test_append_round_raises_for_nonexistent_qa(self, repo_env):
        """Test append_round raises error for non-existent QA."""
        repo = QARepository(project_root=repo_env)

        with pytest.raises(Exception, match="not found"):
            repo.append_round("NONEXISTENT-qa", status="rejected")

    def test_get_current_round(self, repo_env):
        """Test getting current round number."""
        qa_id = "T-5-qa"
        task_id = "T-5"

        create_qa_file(repo_env, qa_id, task_id, state="wip")

        repo = QARepository(project_root=repo_env)

        # Initial round
        current = repo.get_current_round(qa_id)
        assert current == 1

        # After appending
        repo.append_round(qa_id, status="rejected")
        current = repo.get_current_round(qa_id)
        assert current == 2

    def test_list_rounds(self, repo_env):
        """Test listing all rounds for a QA."""
        qa_id = "T-6-qa"
        task_id = "T-6"

        create_qa_file(repo_env, qa_id, task_id, state="wip")

        repo = QARepository(project_root=repo_env)

        # Add some rounds
        repo.append_round(qa_id, status="rejected", notes="Round 2")
        repo.append_round(qa_id, status="approved", notes="Round 3")

        # List rounds
        rounds = repo.list_rounds(qa_id)

        assert len(rounds) >= 2  # At least the appended rounds

