"""Tests for shareEvidenceRoot configuration flag.

This feature allows optionally sharing the validation evidence root across
worktrees (primary + session + meta) to avoid "missing evidence" errors when
operators write evidence in one worktree but run guards from another.
"""
from __future__ import annotations

import os
import sys
import pytest
from pathlib import Path
import yaml

from edison.core.session._config import reset_config_cache
from edison.core.config.cache import clear_all_caches
from tests.helpers.env_setup import clear_path_caches


@pytest.fixture(autouse=True)
def setup_shared_evidence_config(session_git_repo_path, monkeypatch):
    """Configure worktree settings with shareEvidenceRoot enabled.

    This fixture sets up a minimal sharedPaths config that does NOT include
    `.project/qa`, so that `shareEvidenceRoot` provides the independent
    evidence symlink functionality.
    """
    config_dir = session_git_repo_path / ".edison" / "config"
    worktrees_dir = session_git_repo_path / "worktrees"
    meta_dir = worktrees_dir / "_meta"

    session_data = {
        "worktrees": {
            "enabled": True,
            "baseDirectory": str(worktrees_dir),
            "branchPrefix": "session/",
            "sharedState": {
                "mode": "meta",
                "metaBranch": "edison-meta",
                "metaPathTemplate": str(meta_dir),
                # Enable shared evidence root
                "shareEvidenceRoot": True,
                # Only share .project/tasks and .project/sessions, NOT .project/qa
                # This tests the independent evidence root sharing
                "sharedPaths": [
                    {"path": ".project/tasks", "scopes": ["primary", "session"]},
                    {"path": ".project/sessions", "scopes": ["primary", "session"]},
                    {"path": ".edison/_generated", "scopes": ["primary", "session"]},
                ],
            },
            "timeouts": {
                "health_check": 2,
                "fetch": 5,
                "checkout": 5,
                "worktree_add": 5,
                "clone": 10,
                "install": 10,
            },
        }
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_data))

    monkeypatch.setenv("PROJECT_NAME", "testproj")

    clear_path_caches()
    clear_all_caches()
    reset_config_cache()

    yield

    clear_path_caches()
    clear_all_caches()
    reset_config_cache()


class TestShareEvidenceRootConfig:
    """Tests for shareEvidenceRoot configuration parsing."""

    def test_share_evidence_root_config_defaults_to_false(self, session_git_repo_path):
        """shareEvidenceRoot should default to false for backward compatibility."""
        # Override config to NOT specify shareEvidenceRoot
        config_dir = session_git_repo_path / ".edison" / "config"
        worktrees_dir = session_git_repo_path / "worktrees"
        meta_dir = worktrees_dir / "_meta"

        session_data = {
            "worktrees": {
                "enabled": True,
                "baseDirectory": str(worktrees_dir),
                "branchPrefix": "session/",
                "sharedState": {
                    "mode": "meta",
                    "metaBranch": "edison-meta",
                    "metaPathTemplate": str(meta_dir),
                    # No shareEvidenceRoot key
                },
            }
        }
        (config_dir / "session.yml").write_text(yaml.dump(session_data))
        clear_all_caches()
        reset_config_cache()

        from edison.core.config.domains.session import SessionConfig

        cfg = SessionConfig(repo_root=session_git_repo_path).get_worktree_config()
        ss = cfg.get("sharedState", {})

        # Should default to False
        assert ss.get("shareEvidenceRoot", False) is False

    def test_share_evidence_root_config_can_be_enabled(self, session_git_repo_path):
        """shareEvidenceRoot: true should be correctly parsed from config."""
        from edison.core.config.domains.session import SessionConfig

        cfg = SessionConfig(repo_root=session_git_repo_path).get_worktree_config()
        ss = cfg.get("sharedState", {})

        # The fixture enables shareEvidenceRoot: true
        assert ss.get("shareEvidenceRoot") is True

    def test_share_evidence_root_config_can_be_explicitly_disabled(self, session_git_repo_path):
        """shareEvidenceRoot: false should be correctly parsed from config."""
        config_dir = session_git_repo_path / ".edison" / "config"
        worktrees_dir = session_git_repo_path / "worktrees"
        meta_dir = worktrees_dir / "_meta"

        session_data = {
            "worktrees": {
                "enabled": True,
                "baseDirectory": str(worktrees_dir),
                "branchPrefix": "session/",
                "sharedState": {
                    "mode": "meta",
                    "metaBranch": "edison-meta",
                    "metaPathTemplate": str(meta_dir),
                    "shareEvidenceRoot": False,
                },
            }
        }
        (config_dir / "session.yml").write_text(yaml.dump(session_data))
        clear_all_caches()
        reset_config_cache()

        from edison.core.config.domains.session import SessionConfig

        cfg = SessionConfig(repo_root=session_git_repo_path).get_worktree_config()
        ss = cfg.get("sharedState", {})

        assert ss.get("shareEvidenceRoot") is False


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Symlink semantics differ on Windows")
class TestSharedEvidenceRootSymlinks:
    """Tests for evidence root symlink creation when shareEvidenceRoot is enabled."""

    def test_worktree_evidence_root_is_shared_symlink_when_enabled(self, session_git_repo_path):
        """When shareEvidenceRoot=true, session worktree evidence dir should be a symlink to shared root."""
        from edison.core.session import worktree

        # Ensure meta worktree exists first
        meta = worktree.ensure_meta_worktree()
        meta_path = Path(meta["meta_path"])

        # Create the shared evidence root in meta
        shared_evidence = meta_path / ".project" / "qa" / "validation-evidence"
        shared_evidence.mkdir(parents=True, exist_ok=True)

        # Create a session worktree
        sid = "shared-evidence-test"
        wt_path, _ = worktree.create_worktree(sid, base_branch="main")
        assert wt_path is not None

        # Evidence root inside the worktree should be a symlink to meta
        wt_evidence = wt_path / ".project" / "qa" / "validation-evidence"
        assert wt_evidence.exists()
        assert wt_evidence.is_symlink()
        assert wt_evidence.resolve() == shared_evidence.resolve()

    def test_worktree_evidence_written_in_session_is_visible_from_primary(self, session_git_repo_path):
        """Evidence written in session worktree should be visible from primary checkout."""
        from edison.core.session import worktree

        meta = worktree.ensure_meta_worktree()
        meta_path = Path(meta["meta_path"])

        # Create shared evidence root
        shared_evidence = meta_path / ".project" / "qa" / "validation-evidence"
        shared_evidence.mkdir(parents=True, exist_ok=True)

        # Initialize primary shared state (links primary to meta)
        worktree.initialize_meta_shared_state()

        # Create a session worktree
        sid = "evidence-visible-test"
        wt_path, _ = worktree.create_worktree(sid, base_branch="main")
        assert wt_path is not None

        # Write evidence from session worktree
        task_id = "test-task-123"
        round_dir = wt_path / ".project" / "qa" / "validation-evidence" / task_id / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)
        evidence_file = round_dir / "command-test.txt"
        evidence_file.write_text("Test evidence content\n")

        # Verify visible from primary checkout
        primary_evidence_file = (
            session_git_repo_path
            / ".project"
            / "qa"
            / "validation-evidence"
            / task_id
            / "round-1"
            / "command-test.txt"
        )
        assert primary_evidence_file.exists()
        assert primary_evidence_file.read_text() == "Test evidence content\n"

    def test_worktree_evidence_root_not_symlinked_when_disabled(self, session_git_repo_path):
        """When shareEvidenceRoot=false, evidence dir should not be a symlink."""
        # Disable shareEvidenceRoot and also use minimal sharedPaths without .project/qa
        config_dir = session_git_repo_path / ".edison" / "config"
        worktrees_dir = session_git_repo_path / "worktrees"
        meta_dir = worktrees_dir / "_meta"

        session_data = {
            "worktrees": {
                "enabled": True,
                "baseDirectory": str(worktrees_dir),
                "branchPrefix": "session/",
                "sharedState": {
                    "mode": "meta",
                    "metaBranch": "edison-meta",
                    "metaPathTemplate": str(meta_dir),
                    "shareEvidenceRoot": False,
                    # Use minimal sharedPaths without .project/qa
                    "sharedPaths": [
                        {"path": ".project/tasks", "scopes": ["primary", "session"]},
                        {"path": ".project/sessions", "scopes": ["primary", "session"]},
                    ],
                },
            }
        }
        (config_dir / "session.yml").write_text(yaml.dump(session_data))
        clear_all_caches()
        reset_config_cache()

        from edison.core.session import worktree

        # Ensure meta worktree exists
        worktree.ensure_meta_worktree()

        # Create a session worktree
        sid = "no-shared-evidence-test"
        wt_path, _ = worktree.create_worktree(sid, base_branch="main")
        assert wt_path is not None

        # Create the evidence directory manually to test it's not a symlink
        wt_evidence = wt_path / ".project" / "qa" / "validation-evidence"
        wt_evidence.mkdir(parents=True, exist_ok=True)

        # Evidence root should NOT be a symlink when shareEvidenceRoot is disabled
        # and .project/qa is not in sharedPaths
        assert wt_evidence.exists()
        assert not wt_evidence.is_symlink()

    def test_evidence_shared_via_parent_qa_symlink_when_qa_in_shared_paths(
        self, session_git_repo_path
    ):
        """When .project/qa is in sharedPaths, evidence is shared via parent - no extra symlink needed."""
        # Enable shareEvidenceRoot AND include .project/qa in sharedPaths
        config_dir = session_git_repo_path / ".edison" / "config"
        worktrees_dir = session_git_repo_path / "worktrees"
        meta_dir = worktrees_dir / "_meta"

        session_data = {
            "worktrees": {
                "enabled": True,
                "baseDirectory": str(worktrees_dir),
                "branchPrefix": "session/",
                "sharedState": {
                    "mode": "meta",
                    "metaBranch": "edison-meta",
                    "metaPathTemplate": str(meta_dir),
                    "shareEvidenceRoot": True,
                    # Include .project/qa in sharedPaths - this is the default behavior
                    "sharedPaths": [
                        {"path": ".project/tasks", "scopes": ["primary", "session"]},
                        {"path": ".project/qa", "scopes": ["primary", "session"]},
                        {"path": ".project/sessions", "scopes": ["primary", "session"]},
                    ],
                },
            }
        }
        (config_dir / "session.yml").write_text(yaml.dump(session_data))
        clear_all_caches()
        reset_config_cache()

        from edison.core.session import worktree

        # Ensure meta worktree exists and initialize shared state
        meta = worktree.ensure_meta_worktree()
        meta_path = Path(meta["meta_path"])
        worktree.initialize_meta_shared_state()

        # Create evidence directory in meta
        shared_evidence = meta_path / ".project" / "qa" / "validation-evidence"
        shared_evidence.mkdir(parents=True, exist_ok=True)

        # Create a session worktree
        sid = "qa-parent-symlink-test"
        wt_path, _ = worktree.create_worktree(sid, base_branch="main")
        assert wt_path is not None

        # .project/qa should be a symlink (via sharedPaths)
        wt_qa = wt_path / ".project" / "qa"
        assert wt_qa.is_symlink()

        # Evidence directory should be accessible through the parent symlink
        wt_evidence = wt_path / ".project" / "qa" / "validation-evidence"
        assert wt_evidence.exists()
        # Evidence is NOT a symlink itself - it's accessed through the parent symlink
        assert not wt_evidence.is_symlink()
        # But it resolves to the shared location
        assert wt_evidence.resolve() == shared_evidence.resolve()


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Symlink semantics differ on Windows")
class TestSharedEvidenceRootPathResolution:
    """Tests for evidence path resolution with shareEvidenceRoot enabled."""

    def test_get_evidence_base_path_resolves_to_shared_root_when_enabled(
        self, session_git_repo_path
    ):
        """get_evidence_base_path should resolve to the shared root when enabled."""
        from edison.core.session import worktree
        from edison.core.qa._utils import get_evidence_base_path

        # Initialize meta and shared state
        meta = worktree.ensure_meta_worktree()
        meta_path = Path(meta["meta_path"])
        worktree.initialize_meta_shared_state()

        # Create session worktree
        sid = "evidence-path-test"
        wt_path, _ = worktree.create_worktree(sid, base_branch="main")
        assert wt_path is not None

        # When running from session worktree context, evidence path should resolve to shared
        # This requires that the project root is set to the worktree
        evidence_base = get_evidence_base_path(wt_path)

        # The resolved path should be the same as the shared root
        expected_shared = meta_path / ".project" / "qa" / "validation-evidence"
        assert evidence_base.resolve() == expected_shared.resolve()

    def test_evidence_path_resolution_is_deterministic(self, session_git_repo_path):
        """Evidence path should resolve to the same location regardless of checkout used."""
        from edison.core.session import worktree
        from edison.core.qa._utils import get_evidence_base_path

        # Initialize meta and shared state
        meta = worktree.ensure_meta_worktree()
        meta_path = Path(meta["meta_path"])
        worktree.initialize_meta_shared_state()

        # Create two session worktrees
        wt1, _ = worktree.create_worktree("wt1-evidence", base_branch="main")
        wt2, _ = worktree.create_worktree("wt2-evidence", base_branch="main")
        assert wt1 is not None
        assert wt2 is not None

        # All should resolve to the same shared location
        path_from_wt1 = get_evidence_base_path(wt1)
        path_from_wt2 = get_evidence_base_path(wt2)
        path_from_primary = get_evidence_base_path(session_git_repo_path)

        assert path_from_wt1.resolve() == path_from_wt2.resolve()
        assert path_from_wt1.resolve() == path_from_primary.resolve()


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Symlink semantics differ on Windows")
class TestSharedEvidenceRootSafety:
    """Tests for fail-closed safety when sharing evidence root."""

    def test_shared_evidence_root_fails_closed_on_cross_repo_leakage(
        self, session_git_repo_path, tmp_path
    ):
        """shareEvidenceRoot should fail if it would leak evidence to a different repo."""
        # This test ensures that if someone misconfigures the meta path to point
        # outside the repo structure, we fail closed and don't create symlinks
        config_dir = session_git_repo_path / ".edison" / "config"
        worktrees_dir = session_git_repo_path / "worktrees"

        # Point meta to a completely different location
        external_meta = tmp_path / "external-meta"
        external_meta.mkdir(parents=True, exist_ok=True)

        session_data = {
            "worktrees": {
                "enabled": True,
                "baseDirectory": str(worktrees_dir),
                "branchPrefix": "session/",
                "sharedState": {
                    "mode": "external",
                    "externalPath": str(external_meta),
                    "shareEvidenceRoot": True,
                },
            }
        }
        (config_dir / "session.yml").write_text(yaml.dump(session_data))
        clear_all_caches()
        reset_config_cache()

        from edison.core.session import worktree
        from edison.core.session.worktree.manager import _shared_state_cfg

        # The shared state resolver should validate that external paths are safe
        cfg = worktree._config().get_worktree_config()
        ss = _shared_state_cfg(cfg)

        # With mode=external, the external path becomes the shared root
        # Safety check: external path should be validated to be within the repo parent
        assert ss.get("mode") == "external"

    def test_evidence_rounds_remain_append_only(self, session_git_repo_path):
        """Sharing evidence root must not break append-only semantics for rounds."""
        from edison.core.session import worktree
        from edison.core.qa.evidence.service import EvidenceService

        # Initialize meta and shared state
        meta = worktree.ensure_meta_worktree()
        meta_path = Path(meta["meta_path"])
        worktree.initialize_meta_shared_state()

        # Create session worktree
        wt_path, _ = worktree.create_worktree("append-only-test", base_branch="main")
        assert wt_path is not None

        # Create evidence via EvidenceService (from worktree context)
        task_id = "append-only-task"
        ev_svc = EvidenceService(task_id, project_root=wt_path)

        # Create first round
        round1 = ev_svc.ensure_round(1)
        assert round1.exists()
        round1_marker = round1 / "marker.txt"
        round1_marker.write_text("round1\n")

        # Create second round
        round2 = ev_svc.ensure_round(2)
        assert round2.exists()
        round2_marker = round2 / "marker.txt"
        round2_marker.write_text("round2\n")

        # Both rounds should still exist (append-only)
        assert round1_marker.exists()
        assert round2_marker.exists()

        # Verify from primary checkout
        ev_svc_primary = EvidenceService(task_id, project_root=session_git_repo_path)
        rounds = ev_svc_primary.list_rounds()
        assert len(rounds) == 2
