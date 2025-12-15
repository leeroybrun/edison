from __future__ import annotations

import os

from pathlib import Path


def test_tracking_start_creates_implementation_report(isolated_project_env: Path) -> None:
    from edison.core.qa.evidence import tracking
    from edison.core.qa.evidence import EvidenceService

    info = tracking.start_implementation("T-TRACK-1", project_root=isolated_project_env, model="codex")
    assert info["taskId"] == "T-TRACK-1"
    assert info["type"] == "implementation"
    assert info["round"] == 1

    ev = EvidenceService("T-TRACK-1", project_root=isolated_project_env)
    data = ev.read_implementation_report(round_num=1)
    assert data["taskId"] == "T-TRACK-1"
    assert data["round"] == 1
    assert data["completionStatus"] == "partial"
    assert int(data["tracking"]["processId"]) == os.getpid()


def test_tracking_complete_marks_implementation_complete(isolated_project_env: Path) -> None:
    from edison.core.qa.evidence import tracking
    from edison.core.qa.evidence import EvidenceService

    tracking.start_implementation("T-TRACK-2", project_root=isolated_project_env, model="codex")
    tracking.complete("T-TRACK-2", project_root=isolated_project_env)

    ev = EvidenceService("T-TRACK-2", project_root=isolated_project_env)
    data = ev.read_implementation_report(round_num=1)
    assert data["completionStatus"] == "complete"
    assert data["tracking"]["completedAt"]


def test_tracking_start_validation_creates_validator_report(isolated_project_env: Path) -> None:
    from edison.core.qa.evidence import tracking
    from edison.core.qa.evidence import EvidenceService

    tracking.start_implementation("T-TRACK-3", project_root=isolated_project_env, model="codex")
    info = tracking.start_validation(
        "T-TRACK-3",
        project_root=isolated_project_env,
        validator_id="security",
        model="codex",
        round_num=1,
    )
    assert info["type"] == "validation"
    assert info["validatorId"] == "security"

    ev = EvidenceService("T-TRACK-3", project_root=isolated_project_env)
    report = ev.read_validator_report("security", round_num=1)
    assert report["taskId"] == "T-TRACK-3"
    assert report["round"] == 1
    assert report["validatorId"] == "security"
    assert report["verdict"] == "pending"
    assert int(report["tracking"]["processId"]) == os.getpid()
