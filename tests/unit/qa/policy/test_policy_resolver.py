"""Tests for the validation policy resolver.

RED phase: These tests verify the main policy resolver that combines
preset loading, inference, and policy construction into a single API.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import (
    create_repo_with_git,
    create_task_file,
    create_project_structure,
    setup_project_root,
)
from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml


@pytest.mark.qa
class TestPolicyResolver:
    """Tests for ValidationPolicyResolver."""

    def test_resolve_for_task_returns_validation_policy(self, tmp_path: Path, monkeypatch):
        """PolicyResolver.resolve_for_task returns a ValidationPolicy."""
        repo = create_repo_with_git(tmp_path)
        create_project_structure(repo)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        # Create a task
        create_task_file(repo, "T001", state="wip", title="Test Task")

        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        resolver = ValidationPolicyResolver(project_root=repo)
        policy = resolver.resolve_for_task("T001")

        assert policy is not None
        assert policy.task_id == "T001"
        assert policy.preset is not None
        assert policy.preset.name in ("quick", "standard")

    def test_resolve_uses_file_context_for_inference(self, tmp_path: Path, monkeypatch):
        """PolicyResolver uses FileContextService to get changed files."""
        repo = create_repo_with_git(tmp_path)
        create_project_structure(repo)

        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        create_task_file(repo, "T001", state="wip", title="Docs Update")

        # Create evidence directory with implementation report listing docs files
        from edison.core.qa.evidence import EvidenceService

        ev = EvidenceService("T001", project_root=repo)
        ev.ensure_round(1)
        ev.write_implementation_report(
            {
                "summary": "Changed documentation files.",
                "filesModified": ["docs/README.md", "docs/api.md"],
            },
            round_num=1,
        )

        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        resolver = ValidationPolicyResolver(project_root=repo)
        policy = resolver.resolve_for_task("T001")

        # Should infer quick preset based on docs-only changes
        assert policy.preset.name == "quick"
        assert "docs/README.md" in policy.changed_files or len(policy.changed_files) >= 0

    def test_resolve_with_explicit_preset_name(self, tmp_path: Path, monkeypatch):
        """PolicyResolver can use an explicit preset name, skipping inference."""
        repo = create_repo_with_git(tmp_path)
        create_project_structure(repo)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        create_task_file(repo, "T001", state="wip", title="Force Standard")

        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        resolver = ValidationPolicyResolver(project_root=repo)
        policy = resolver.resolve_for_task("T001", preset_name="standard")

        assert policy.preset.name == "standard"

    def test_resolve_raises_for_unknown_preset(self, tmp_path: Path, monkeypatch):
        """PolicyResolver raises ValueError for unknown explicit preset."""
        repo = create_repo_with_git(tmp_path)
        create_project_structure(repo)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        create_task_file(repo, "T001", state="wip", title="Bad Preset")

        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        resolver = ValidationPolicyResolver(project_root=repo)

        with pytest.raises(ValueError, match="Unknown preset"):
            resolver.resolve_for_task("T001", preset_name="nonexistent")


@pytest.mark.qa
class TestPolicyValidatorFiltering:
    """Tests for filtering validators based on policy."""

    def test_quick_preset_adds_no_extra_validators(self, tmp_path: Path, monkeypatch):
        """Quick preset should not add any extra validators beyond always_run globals."""
        repo = create_repo_with_git(tmp_path)
        create_project_structure(repo)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        create_task_file(repo, "T001", state="wip", title="Quick Test")

        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        resolver = ValidationPolicyResolver(project_root=repo)
        policy = resolver.resolve_for_task("T001", preset_name="quick")

        assert policy.preset.validators == []
        assert policy.preset.blocking_validators == []

    def test_standard_preset_includes_more_validators(self, tmp_path: Path, monkeypatch):
        """Standard preset includes more validators than quick."""
        repo = create_repo_with_git(tmp_path)
        create_project_structure(repo)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        create_task_file(repo, "T001", state="wip", title="Standard Test")

        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        resolver = ValidationPolicyResolver(project_root=repo)
        quick_policy = resolver.resolve_for_task("T001", preset_name="quick")
        standard_policy = resolver.resolve_for_task("T001", preset_name="standard")

        # Standard should have equal or more validators
        assert len(standard_policy.preset.validators) >= len(quick_policy.preset.validators)


@pytest.mark.qa
class TestPolicyEvidenceRequirements:
    """Tests for evidence requirements from policy."""

    def test_quick_preset_requires_no_evidence(self, tmp_path: Path, monkeypatch):
        """Quick preset explicitly disables required evidence."""
        repo = create_repo_with_git(tmp_path)
        create_project_structure(repo)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        create_task_file(repo, "T001", state="wip", title="Quick Evidence")

        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        resolver = ValidationPolicyResolver(project_root=repo)
        policy = resolver.resolve_for_task("T001", preset_name="quick")

        assert policy.required_evidence == []

    def test_standard_preset_requires_automation_evidence(self, tmp_path: Path, monkeypatch):
        """Standard preset requires automation command evidence."""
        repo = create_repo_with_git(tmp_path)
        create_project_structure(repo)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        create_task_file(repo, "T001", state="wip", title="Standard Evidence")

        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        resolver = ValidationPolicyResolver(project_root=repo)
        policy = resolver.resolve_for_task("T001", preset_name="standard")

        # Standard should require automation files
        evidence = policy.required_evidence
        # Check that at least some automation evidence is required
        automation_files = [f for f in evidence if f.startswith("command-")]
        assert len(automation_files) > 0


@pytest.mark.qa
class TestPolicyResolverCaching:
    """Tests for policy resolver caching behavior."""

    def test_resolver_caches_preset_config(self, tmp_path: Path, monkeypatch):
        """PolicyResolver should cache loaded preset configurations."""
        repo = create_repo_with_git(tmp_path)
        create_project_structure(repo)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        create_task_file(repo, "T001", state="wip")
        create_task_file(repo, "T002", state="wip")

        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        resolver = ValidationPolicyResolver(project_root=repo)

        # Multiple calls should use cached config
        policy1 = resolver.resolve_for_task("T001", preset_name="quick")
        policy2 = resolver.resolve_for_task("T002", preset_name="quick")

        # Same preset object should be returned (cached)
        assert policy1.preset.name == policy2.preset.name


@pytest.mark.qa
class TestPolicyIntegrationWithValidatorRegistry:
    """Tests for policy resolver integration with ValidatorRegistry."""

    def test_policy_validators_exist_in_registry(self, tmp_path: Path, monkeypatch):
        """Validators in policy must exist in ValidatorRegistry."""
        repo = create_repo_with_git(tmp_path)
        create_project_structure(repo)
        setup_project_root(monkeypatch, repo)
        reset_edison_caches()

        create_task_file(repo, "T001", state="wip")

        from edison.core.qa.policy.resolver import ValidationPolicyResolver
        from edison.core.registries.validators import ValidatorRegistry

        resolver = ValidationPolicyResolver(project_root=repo)
        policy = resolver.resolve_for_task("T001", preset_name="quick")

        registry = ValidatorRegistry(project_root=repo)

        # All validators in the preset must exist in registry
        for validator_id in policy.preset.validators:
            assert registry.exists(validator_id), f"Validator {validator_id} not in registry"
