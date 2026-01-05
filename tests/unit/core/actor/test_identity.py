"""Tests for actor identity resolution.

RED phase: These tests define the expected behavior for ActorIdentity resolver.
"""

from __future__ import annotations

from pathlib import Path

import pytest


class TestActorKindNormalization:
    """Test normalization of actor kinds from env vars."""

    def test_agent_kind_normalized(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Agent kind should be normalized from env var."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "agent")
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.kind == "agent"

    def test_agents_alias_normalized_to_agent(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Legacy 'agents' alias should normalize to 'agent'."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "agents")
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.kind == "agent"

    def test_orchestrator_kind_normalized(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Orchestrator kind should be normalized from env var."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "orchestrator")
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.kind == "orchestrator"

    def test_validator_kind_normalized(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Validator kind should be normalized from env var."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "validator")
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.kind == "validator"

    def test_validators_alias_normalized_to_validator(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Legacy 'validators' alias should normalize to 'validator'."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "validators")
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.kind == "validator"

    def test_case_insensitive_normalization(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Kind normalization should be case-insensitive."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "AGENT")
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.kind == "agent"

    def test_unknown_kind_returns_unknown(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Unknown actor kinds should return 'unknown'."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "invalid_kind")
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.kind == "unknown"

    def test_missing_env_returns_unknown(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Missing EDISON_ACTOR_KIND env var should return 'unknown'."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.delenv("EDISON_ACTOR_KIND", raising=False)
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.kind == "unknown"


class TestActorIdResolution:
    """Test actor ID resolution from env vars."""

    def test_actor_id_from_env(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Actor ID should be read from EDISON_ACTOR_ID env var."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "agent")
        monkeypatch.setenv("EDISON_ACTOR_ID", "my-custom-agent")
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.actor_id == "my-custom-agent"

    def test_missing_actor_id_returns_none(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Missing EDISON_ACTOR_ID env var should return None."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "agent")
        monkeypatch.delenv("EDISON_ACTOR_ID", raising=False)
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.actor_id is None


class TestConstitutionPath:
    """Test constitution path resolution."""

    def test_agent_constitution_path(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Agent kind should resolve to AGENTS.md constitution."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "agent")
        result = resolve_actor_identity(project_root=isolated_project_env, session_id=None)
        assert result.constitution_path is not None
        assert result.constitution_path.name == "AGENTS.md"
        assert result.constitution_path.parent.name == "constitutions"

    def test_orchestrator_constitution_path(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Orchestrator kind should resolve to ORCHESTRATOR.md constitution."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "orchestrator")
        result = resolve_actor_identity(project_root=isolated_project_env, session_id=None)
        assert result.constitution_path is not None
        assert result.constitution_path.name == "ORCHESTRATOR.md"

    def test_validator_constitution_path(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Validator kind should resolve to VALIDATORS.md constitution."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "validator")
        result = resolve_actor_identity(project_root=isolated_project_env, session_id=None)
        assert result.constitution_path is not None
        assert result.constitution_path.name == "VALIDATORS.md"

    def test_unknown_kind_has_no_constitution_path(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Unknown kind should have no constitution path."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.delenv("EDISON_ACTOR_KIND", raising=False)
        result = resolve_actor_identity(project_root=isolated_project_env, session_id=None)
        assert result.constitution_path is None


class TestReadCommand:
    """Test read command generation."""

    def test_agent_read_command(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Agent kind should generate correct read command."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "agent")
        result = resolve_actor_identity(project_root=isolated_project_env, session_id=None)
        assert result.read_command == "edison read AGENTS --type constitutions"

    def test_orchestrator_read_command(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Orchestrator kind should generate correct read command."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "orchestrator")
        result = resolve_actor_identity(project_root=isolated_project_env, session_id=None)
        assert result.read_command == "edison read ORCHESTRATOR --type constitutions"

    def test_validator_read_command(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Validator kind should generate correct read command."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "validator")
        result = resolve_actor_identity(project_root=isolated_project_env, session_id=None)
        assert result.read_command == "edison read VALIDATORS --type constitutions"

    def test_unknown_kind_has_no_read_command(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Unknown kind should have no read command."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.delenv("EDISON_ACTOR_KIND", raising=False)
        result = resolve_actor_identity(project_root=isolated_project_env, session_id=None)
        assert result.read_command is None


class TestActorIdentityDataclass:
    """Test ActorIdentity dataclass properties."""

    def test_actor_identity_is_frozen(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """ActorIdentity should be immutable."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "agent")
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)

        with pytest.raises(AttributeError):
            result.kind = "orchestrator"  # type: ignore[misc]

    def test_actor_identity_source_field(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """ActorIdentity should track resolution source."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.setenv("EDISON_ACTOR_KIND", "agent")
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.source == "env"

    def test_actor_identity_unknown_source_fallback(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        """Missing env vars should set source to 'fallback'."""
        from edison.core.actor.identity import resolve_actor_identity

        monkeypatch.delenv("EDISON_ACTOR_KIND", raising=False)
        result = resolve_actor_identity(project_root=tmp_path, session_id=None)
        assert result.source == "fallback"
