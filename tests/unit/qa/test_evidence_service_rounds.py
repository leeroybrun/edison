"""Tests for EvidenceService round management - NO MOCKS."""
from __future__ import annotations

import pytest
from pathlib import Path

from edison.core.qa.evidence.service import EvidenceService
from edison.core.qa.evidence.exceptions import EvidenceError


@pytest.fixture(autouse=True)
def clear_path_caches():
    """Clear path singleton cache before each test."""
    from edison.core.utils.paths import management
    management._paths_instance = None
    yield
    management._paths_instance = None


@pytest.fixture
def project_root(tmp_path):
    """Create a real project structure with .edison config."""
    root = tmp_path / "project"
    root.mkdir()

    # Create .edison config
    edison_dir = root / ".edison"
    edison_dir.mkdir()
    config_file = edison_dir / "config.yml"
    config_file.write_text("management_dir: .project\n")

    return root


def test_evidence_service_create_round_initial(project_root):
    """EvidenceService can create initial evidence round."""
    svc = EvidenceService(task_id="T-123", project_root=project_root)

    # Create first round
    round_path = svc.ensure_round()

    assert round_path.exists()
    assert round_path.name == "round-1"
    assert round_path.parent == svc.get_evidence_root()


def test_evidence_service_get_current_round_none(project_root):
    """EvidenceService returns None when no rounds exist."""
    svc = EvidenceService(task_id="T-123", project_root=project_root)

    assert svc.get_current_round() is None


def test_evidence_service_get_current_round(project_root):
    """EvidenceService returns current round number."""
    svc = EvidenceService(task_id="T-123", project_root=project_root)

    # Create round
    svc.ensure_round()

    assert svc.get_current_round() == 1

    # Create another round
    svc.create_next_round()

    assert svc.get_current_round() == 2


def test_evidence_service_create_next_round(project_root):
    """EvidenceService creates sequential rounds."""
    svc = EvidenceService(task_id="T-456", project_root=project_root)

    # Create first round
    r1 = svc.create_next_round()
    assert r1.name == "round-1"
    assert r1.exists()

    # Create second round
    r2 = svc.create_next_round()
    assert r2.name == "round-2"
    assert r2.exists()

    # Create third round
    r3 = svc.create_next_round()
    assert r3.name == "round-3"
    assert r3.exists()


def test_evidence_service_list_rounds(project_root):
    """EvidenceService lists all rounds."""
    svc = EvidenceService(task_id="T-789", project_root=project_root)

    # No rounds initially
    assert svc.list_rounds() == []

    # Create rounds
    svc.ensure_round()
    svc.create_next_round()
    svc.create_next_round()

    rounds = svc.list_rounds()
    assert len(rounds) == 3
    assert rounds[0].name == "round-1"
    assert rounds[1].name == "round-2"
    assert rounds[2].name == "round-3"


def test_evidence_service_ensure_round_latest(project_root):
    """EvidenceService.ensure_round() returns latest round."""
    svc = EvidenceService(task_id="T-600", project_root=project_root)

    # Create rounds
    r1 = svc.create_next_round()
    r2 = svc.create_next_round()

    # ensure_round with no arg should return latest
    latest = svc.ensure_round()
    assert latest == r2
    assert latest.name == "round-2"


def test_evidence_service_ensure_round_specific_existing(project_root):
    """EvidenceService.ensure_round(N) returns existing round N."""
    svc = EvidenceService(task_id="T-700", project_root=project_root)

    # Create rounds
    r1 = svc.create_next_round()
    r2 = svc.create_next_round()

    # Ensure specific round that exists
    round_1 = svc.ensure_round(round_num=1)
    assert round_1 == r1
    assert round_1.name == "round-1"


def test_evidence_service_ensure_round_specific_next(project_root):
    """EvidenceService.ensure_round(N) creates round N if it's next."""
    svc = EvidenceService(task_id="T-800", project_root=project_root)

    # Create round 1
    svc.create_next_round()

    # ensure_round(2) should create round 2 since it's next
    r2 = svc.ensure_round(round_num=2)
    assert r2.exists()
    assert r2.name == "round-2"


def test_evidence_service_ensure_round_invalid_number(project_root):
    """EvidenceService.ensure_round(N) raises if N is not valid."""
    svc = EvidenceService(task_id="T-900", project_root=project_root)

    # Create round 1
    svc.create_next_round()

    # Try to ensure round 5 (skipping 2, 3, 4)
    with pytest.raises(EvidenceError) as exc_info:
        svc.ensure_round(round_num=5)

    assert "Cannot create round 5" in str(exc_info.value)
    assert "Next available is 2" in str(exc_info.value)
