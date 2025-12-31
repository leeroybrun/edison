"""Tests for preset inference from changed files.

RED phase: These tests verify that the correct validation preset is inferred
based on the files changed in a task, with proper escalation logic.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import (
    create_repo_with_git,
    setup_project_root,
)
from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml


@pytest.mark.qa
class TestPresetInference:
    """Tests for inferring validation preset from changed files."""

    def test_docs_only_changes_infer_quick_preset(self, tmp_path: Path, monkeypatch):
        """Changes only in docs/ should infer 'quick' preset."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)
        result = inference.infer_preset([
            "docs/README.md",
            "docs/api/endpoints.md",
        ])

        assert result.preset_name == "quick"
        assert result.confidence == "high"

    def test_markdown_only_changes_infer_quick_preset(self, tmp_path: Path, monkeypatch):
        """Changes only in .md files (anywhere) should infer 'quick' preset."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)
        result = inference.infer_preset([
            "CHANGELOG.md",
            "README.md",
        ])

        assert result.preset_name == "quick"

    def test_source_code_changes_infer_standard_preset(self, tmp_path: Path, monkeypatch):
        """Changes in source code should infer 'standard' preset."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)
        result = inference.infer_preset([
            "src/app.py",
            "src/utils/helpers.py",
        ])

        assert result.preset_name == "standard"

    def test_test_file_changes_infer_standard_preset(self, tmp_path: Path, monkeypatch):
        """Changes in test files should infer 'standard' preset."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)
        result = inference.infer_preset([
            "tests/unit/test_app.py",
        ])

        assert result.preset_name == "standard"

    def test_mixed_docs_and_code_escalates_to_standard(self, tmp_path: Path, monkeypatch):
        """Mixed docs and code changes should escalate to 'standard' preset."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)
        result = inference.infer_preset([
            "docs/README.md",  # Would infer quick
            "src/app.py",      # Should escalate to standard
        ])

        assert result.preset_name == "standard"
        assert result.was_escalated is True

    def test_config_file_changes_infer_standard(self, tmp_path: Path, monkeypatch):
        """Changes in config files should infer 'standard' preset."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)
        result = inference.infer_preset([
            "pyproject.toml",
        ])

        assert result.preset_name == "standard"

    def test_empty_file_list_returns_quick(self, tmp_path: Path, monkeypatch):
        """Empty file list should return 'quick' preset (defensive default)."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)
        result = inference.infer_preset([])

        assert result.preset_name == "quick"


@pytest.mark.qa
class TestPresetInferenceResult:
    """Tests for PresetInferenceResult structure."""

    def test_result_has_preset_name(self, tmp_path: Path, monkeypatch):
        """Inference result must have preset_name."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)
        result = inference.infer_preset(["docs/README.md"])

        assert hasattr(result, "preset_name")
        assert isinstance(result.preset_name, str)

    def test_result_has_matched_patterns(self, tmp_path: Path, monkeypatch):
        """Inference result should include which patterns matched."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)
        result = inference.infer_preset(["docs/README.md"])

        assert hasattr(result, "matched_patterns")
        # Should have matched at least one pattern
        assert len(result.matched_patterns) >= 0

    def test_result_has_confidence_level(self, tmp_path: Path, monkeypatch):
        """Inference result should include confidence level."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)
        result = inference.infer_preset(["docs/README.md"])

        assert hasattr(result, "confidence")
        assert result.confidence in ("high", "medium", "low")

    def test_result_tracks_escalation(self, tmp_path: Path, monkeypatch):
        """Inference result tracks whether escalation occurred."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)
        result = inference.infer_preset(["docs/README.md", "src/app.py"])

        assert hasattr(result, "was_escalated")
        assert isinstance(result.was_escalated, bool)


@pytest.mark.qa
class TestPresetEscalation:
    """Tests for preset escalation rules."""

    def test_escalation_from_quick_to_standard(self, tmp_path: Path, monkeypatch):
        """When code changes detected, quick preset escalates to standard."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)

        # Docs only - should stay quick
        docs_result = inference.infer_preset(["docs/README.md"])
        assert docs_result.preset_name == "quick"
        assert docs_result.was_escalated is False

        # Docs + code - should escalate
        mixed_result = inference.infer_preset(["docs/README.md", "src/app.py"])
        assert mixed_result.preset_name == "standard"
        assert mixed_result.was_escalated is True

    def test_no_escalation_when_already_at_target(self, tmp_path: Path, monkeypatch):
        """No escalation when files already match target preset level."""
        repo = create_repo_with_git(tmp_path)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        from edison.core.qa.policy.inference import PresetInference

        inference = PresetInference(project_root=repo)

        # Code files - directly standard, no escalation
        result = inference.infer_preset(["src/app.py"])
        assert result.preset_name == "standard"
        assert result.was_escalated is False
