"""Tests for actor-aware session context.

RED phase: These tests define the expected behavior for role-aware session context,
where actor identity is included in both JSON and Markdown output.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.session import ensure_session


class TestSessionContextPayloadActorIdentity:
    """Test actor identity fields in session context payload."""

    @pytest.mark.session
    def test_payload_includes_actor_identity_when_env_set(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Payload should include actor identity fields when EDISON_ACTOR_KIND is set."""
        session_id = "sess-actor-001"
        ensure_session(session_id, state="active")

        monkeypatch.setenv("EDISON_ACTOR_KIND", "agent")
        monkeypatch.setenv("EDISON_ACTOR_ID", "test-agent-profile")

        from edison.core.session.context_payload import build_session_context_payload

        payload = build_session_context_payload(
            project_root=isolated_project_env,
            session_id=session_id,
        )
        data = payload.to_dict()

        assert "actorKind" in data
        assert data["actorKind"] == "agent"
        assert "actorId" in data
        assert data["actorId"] == "test-agent-profile"
        assert "actorConstitution" in data
        assert "AGENTS.md" in data["actorConstitution"]
        assert "actorReadCmd" in data
        assert data["actorReadCmd"] == "edison read AGENTS --type constitutions"

    @pytest.mark.session
    def test_payload_includes_actor_resolution_source(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Payload should include how actor identity was resolved."""
        session_id = "sess-actor-002"
        ensure_session(session_id, state="active")

        monkeypatch.setenv("EDISON_ACTOR_KIND", "orchestrator")

        from edison.core.session.context_payload import build_session_context_payload

        payload = build_session_context_payload(
            project_root=isolated_project_env,
            session_id=session_id,
        )
        data = payload.to_dict()

        assert "actorResolution" in data
        assert data["actorResolution"] == "env"

    @pytest.mark.session
    def test_payload_accepts_plural_orchestrators_alias(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Plural actor kinds should normalize to the canonical actor kind."""
        session_id = "sess-actor-004"
        ensure_session(session_id, state="active")

        monkeypatch.setenv("EDISON_ACTOR_KIND", "orchestrators")

        from edison.core.session.context_payload import build_session_context_payload

        payload = build_session_context_payload(
            project_root=isolated_project_env,
            session_id=session_id,
        )
        data = payload.to_dict()

        assert data.get("actorKind") == "orchestrator"
        assert data.get("actorReadCmd") == "edison read ORCHESTRATOR --type constitutions"

    @pytest.mark.session
    def test_payload_actor_kind_unknown_when_env_not_set(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Payload should have unknown actor kind when env var not set."""
        session_id = "sess-actor-003"
        ensure_session(session_id, state="active")

        monkeypatch.delenv("EDISON_ACTOR_KIND", raising=False)

        from edison.core.session.context_payload import build_session_context_payload

        payload = build_session_context_payload(
            project_root=isolated_project_env,
            session_id=session_id,
        )
        data = payload.to_dict()

        assert "actorKind" in data
        assert data["actorKind"] == "unknown"
        assert "actorResolution" in data
        assert data["actorResolution"] == "fallback"


class TestSessionContextMarkdownActorField:
    """Test actor field rendering in Markdown output."""

    @pytest.mark.session
    def test_markdown_includes_actor_stanza_when_configured(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Markdown should include Actor section when actor field is configured."""
        session_id = "sess-actor-md-001"
        ensure_session(session_id, state="active")

        monkeypatch.setenv("EDISON_ACTOR_KIND", "validator")

        from edison.core.session.context_payload import (
            build_session_context_payload,
            format_session_context_markdown,
        )

        payload = build_session_context_payload(
            project_root=isolated_project_env,
            session_id=session_id,
        )
        markdown = format_session_context_markdown(payload)

        # Should include actor kind
        assert "Actor:" in markdown or "actor" in markdown.lower()
        # Should include read command
        assert "edison read VALIDATORS --type constitutions" in markdown

    @pytest.mark.session
    def test_markdown_actor_shows_kind_and_id_when_both_present(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Markdown should show both actor kind and id when available."""
        session_id = "sess-actor-md-002"
        ensure_session(session_id, state="active")

        monkeypatch.setenv("EDISON_ACTOR_KIND", "agent")
        monkeypatch.setenv("EDISON_ACTOR_ID", "specialized-agent")

        from edison.core.session.context_payload import (
            build_session_context_payload,
            format_session_context_markdown,
        )

        payload = build_session_context_payload(
            project_root=isolated_project_env,
            session_id=session_id,
        )
        markdown = format_session_context_markdown(payload)

        # Should show kind
        assert "agent" in markdown.lower()
        # Should show id
        assert "specialized-agent" in markdown

    @pytest.mark.session
    def test_markdown_actor_shows_unknown_gracefully(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Markdown should handle unknown actor kind gracefully."""
        session_id = "sess-actor-md-003"
        ensure_session(session_id, state="active")

        monkeypatch.delenv("EDISON_ACTOR_KIND", raising=False)

        from edison.core.session.context_payload import (
            build_session_context_payload,
            format_session_context_markdown,
        )

        payload = build_session_context_payload(
            project_root=isolated_project_env,
            session_id=session_id,
        )
        markdown = format_session_context_markdown(payload)

        # Should still render (unknown is valid)
        # The exact format depends on implementation
        assert "## Edison Context" in markdown
        assert "actor" in markdown.lower()
        assert "unknown" in markdown.lower()


class TestSessionContextForNextActorField:
    """Test actor field rendering in session next output."""

    @pytest.mark.session
    def test_next_output_includes_actor_when_configured(
        self, monkeypatch: pytest.MonkeyPatch, isolated_project_env: Path
    ) -> None:
        """Session next output should include actor info when configured."""
        session_id = "sess-actor-next-001"
        ensure_session(session_id, state="active")

        monkeypatch.setenv("EDISON_ACTOR_KIND", "orchestrator")

        from edison.core.session.context_payload import (
            build_session_context_payload,
            format_session_context_for_next,
        )

        payload = build_session_context_payload(
            project_root=isolated_project_env,
            session_id=session_id,
        )
        ctx = payload.to_dict()
        lines = format_session_context_for_next(ctx)
        output = "\n".join(lines)

        # Should include actor read command
        assert "edison read ORCHESTRATOR --type constitutions" in output
