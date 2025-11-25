from __future__ import annotations

from pathlib import Path


def _expected_evidence_dir(project_root: Path, task_id: str) -> Path:
    return project_root / ".project" / "qa" / "validation-evidence" / task_id


def test_get_evidence_dir_path_construction(isolated_project_env: Path) -> None:
    """get_evidence_dir should resolve the canonical evidence directory."""
    from edison.core.qa import evidence as qa_evidence 
    task_id = "task-123"
    ev_dir = qa_evidence.get_evidence_dir(task_id)

    assert ev_dir == _expected_evidence_dir(isolated_project_env, task_id)
    # Function should not create directories eagerly.
    assert not ev_dir.exists()


def test_get_latest_round_with_multiple_rounds(isolated_project_env: Path) -> None:
    """get_latest_round should return the highest numeric round."""
    from edison.core.qa import evidence as qa_evidence 
    task_id = "task-456"
    ev_dir = _expected_evidence_dir(isolated_project_env, task_id)

    # Create several round directories, including a non-numeric suffix to
    # ensure it is ignored for ordering.
    (ev_dir / "round-1").mkdir(parents=True, exist_ok=True)
    (ev_dir / "round-3").mkdir(parents=True, exist_ok=True)
    (ev_dir / "round-2").mkdir(parents=True, exist_ok=True)
    (ev_dir / "round-alpha").mkdir(parents=True, exist_ok=True)

    latest = qa_evidence.get_latest_round(task_id)
    assert latest == 3


def test_get_latest_round_when_no_rounds(isolated_project_env: Path) -> None:
    """When no rounds exist, get_latest_round should return None."""
    from edison.core.qa import evidence as qa_evidence 
    task_id = "task-empty"
    latest = qa_evidence.get_latest_round(task_id)
    assert latest is None


def test_get_implementation_report_path(isolated_project_env: Path) -> None:
    """get_implementation_report_path should point into the correct round dir."""
    from edison.core.qa import evidence as qa_evidence 
    task_id = "task-789"
    round_num = 2
    ev_dir = _expected_evidence_dir(isolated_project_env, task_id)
    (ev_dir / f"round-{round_num}").mkdir(parents=True, exist_ok=True)

    report_path = qa_evidence.get_implementation_report_path(task_id, round_num)
    assert report_path == ev_dir / f"round-{round_num}" / "implementation-report.json"

