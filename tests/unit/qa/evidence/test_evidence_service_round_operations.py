"""Tests for EvidenceService round-specific operations - NO MOCKS."""
from __future__ import annotations

from pathlib import Path

from edison.core.qa.evidence.service import EvidenceService


def test_evidence_service_round_operations_with_specific_round(isolated_project_env):
    """EvidenceService can operate on specific rounds."""
    svc = EvidenceService(task_id="T-500", project_root=isolated_project_env)

    # Create two rounds
    r1 = svc.create_next_round()
    r2 = svc.create_next_round()

    # Write to round 1
    svc.write_bundle({"round": 1}, round_num=1)

    # Write to round 2
    svc.write_bundle({"round": 2}, round_num=2)

    # Read from specific rounds
    data1 = svc.read_bundle(round_num=1)
    data2 = svc.read_bundle(round_num=2)

    assert data1 == {"round": 1}
    assert data2 == {"round": 2}


def test_evidence_service_get_current_round_dir_none(isolated_project_env):
    """get_current_round_dir() returns None when no rounds exist."""
    svc = EvidenceService(task_id="T-RD-001", project_root=isolated_project_env)

    assert svc.get_current_round_dir() is None


def test_evidence_service_get_current_round_dir_single_round(isolated_project_env):
    """get_current_round_dir() returns the only round directory."""
    svc = EvidenceService(task_id="T-RD-002", project_root=isolated_project_env)

    # Create round
    r1 = svc.create_next_round()

    current_dir = svc.get_current_round_dir()
    assert current_dir is not None
    assert current_dir == r1
    assert current_dir.name == "round-1"


def test_evidence_service_get_current_round_dir_multiple_rounds(isolated_project_env):
    """get_current_round_dir() returns latest round directory."""
    svc = EvidenceService(task_id="T-RD-003", project_root=isolated_project_env)

    # Create multiple rounds
    r1 = svc.create_next_round()
    r2 = svc.create_next_round()
    r3 = svc.create_next_round()

    current_dir = svc.get_current_round_dir()
    assert current_dir is not None
    assert current_dir == r3
    assert current_dir.name == "round-3"


def test_evidence_service_get_current_round_dir_returns_path_object(isolated_project_env):
    """get_current_round_dir() returns a Path object."""
    svc = EvidenceService(task_id="T-RD-004", project_root=isolated_project_env)

    # Create round
    svc.create_next_round()

    current_dir = svc.get_current_round_dir()
    assert current_dir is not None
    assert isinstance(current_dir, Path)
    assert current_dir.is_dir()
