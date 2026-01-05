"""
Tests for `edison rules inject` CLI command.

SUMMARY: Verify the rules inject CLI returns applicable rules with rendered content

The `edison rules inject` command provides a unified interface for clients
(Claude hooks, OpenCode plugin) to get applicable rules and injection text.

Expected output shape (JSON mode):
{
    "sessionId": "...",
    "taskId": "...",
    "contexts": ["..."],
    "rules": [{"id": "...", "title": "...", "content": "...", "priority": "..."}],
    "injection": "## Edison Rules ..."
}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def edison_project(isolated_project_env: Path) -> Path:
    """Fixture providing an Edison project directory for rules inject tests."""
    return isolated_project_env


class TestRulesInjectCLI:
    """Tests for edison rules inject CLI."""

    def test_inject_module_exists(self) -> None:
        """Verify rules/inject.py exists and is importable."""
        from edison.cli.rules import inject  # noqa: F401

    def test_register_args_accepts_session_id(self) -> None:
        """CLI should accept --session-id flag."""
        from edison.cli.rules.inject import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--session-id", "my-session"])
        assert args.session_id == "my-session"

    def test_register_args_accepts_task_id(self) -> None:
        """CLI should accept --task-id flag."""
        from edison.cli.rules.inject import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--task-id", "123"])
        assert args.task_id == "123"

    def test_register_args_accepts_context(self) -> None:
        """CLI should accept --context flag (multiple values)."""
        from edison.cli.rules.inject import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--context", "delegation", "--context", "validation"])
        assert args.context == ["delegation", "validation"]

    def test_register_args_accepts_transition(self) -> None:
        """CLI should accept --transition flag."""
        from edison.cli.rules.inject import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--transition", "wip->done"])
        assert args.transition == "wip->done"

    def test_register_args_accepts_format(self) -> None:
        """CLI should accept --format flag with markdown/json options."""
        from edison.cli.rules.inject import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--format", "markdown"])
        assert args.format == "markdown"

    def test_register_args_defaults(self) -> None:
        """CLI should have sensible defaults."""
        from edison.cli.rules.inject import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([])
        assert args.format == "markdown"
        assert args.context is None
        assert args.transition is None
        assert args.state is None

    def test_register_args_accepts_state(self) -> None:
        """CLI should accept --state flag for auto state-to-transition mapping."""
        from edison.cli.rules.inject import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(["--state", "wip"])
        assert args.state == "wip"


class TestStateToTransitionMapping:
    """Tests for centralized state-to-transition mapping."""

    def test_state_to_transition_wip(self) -> None:
        """wip state should map to wip->done transition."""
        from edison.cli.rules.inject import _state_to_transition

        assert _state_to_transition("wip") == "wip->done"

    def test_state_to_transition_done(self) -> None:
        """done state should map to done->validated transition."""
        from edison.cli.rules.inject import _state_to_transition

        assert _state_to_transition("done") == "done->validated"

    def test_state_to_transition_unknown(self) -> None:
        """Unknown state should return None."""
        from edison.cli.rules.inject import _state_to_transition

        assert _state_to_transition("unknown") is None
        assert _state_to_transition("todo") is None
        assert _state_to_transition("validated") is None

    def test_state_flag_auto_maps_to_transition(
        self, edison_project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--state flag should auto-map to transition and return rules."""
        from edison.cli.rules.inject import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--json",
            "--state", "wip",  # Should auto-map to wip->done
            "--repo-root", str(edison_project),
        ])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)
        # Same rules as wip->done transition
        rule_ids = [r["id"] for r in data["rules"]]
        assert "RULE.GUARDS.FAIL_CLOSED" in rule_ids or len(rule_ids) > 0


class TestRulesInjectOutput:
    """Tests for rules inject output format."""

    def test_json_output_has_required_fields(
        self, edison_project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """JSON output should contain sessionId, taskId, contexts, rules, injection."""
        from edison.cli.rules.inject import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--json",
            "--repo-root", str(edison_project),
        ])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)

        # Required top-level fields
        assert "sessionId" in data
        assert "taskId" in data
        assert "contexts" in data
        assert "rules" in data
        assert "injection" in data

    def test_rules_list_has_correct_shape(
        self, edison_project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Each rule in output should have id, title, content, priority."""
        from edison.cli.rules.inject import main, register_args

        # Use bundled transitions which have real rules (wip->done has RULE.GUARDS.FAIL_CLOSED)
        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--json",
            "--transition", "wip->done",
            "--repo-root", str(edison_project),
        ])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)

        assert isinstance(data["rules"], list)
        # Bundled wip->done has rules defined
        assert len(data["rules"]) > 0, "wip->done transition should have rules in bundled config"
        # At least verify structure when rules exist
        for rule in data["rules"]:
            assert "id" in rule
            assert "title" in rule
            assert "content" in rule
            assert "priority" in rule

    def test_injection_is_markdown_string(
        self, edison_project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Injection field should be a markdown string."""
        from edison.cli.rules.inject import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--json",
            "--repo-root", str(edison_project),
        ])

        main(args)
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert isinstance(data["injection"], str)

    def test_markdown_output_is_injection_text(
        self, edison_project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Non-JSON output should be just the injection markdown text."""
        from edison.cli.rules.inject import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--format", "markdown",
            "--repo-root", str(edison_project),
        ])

        main(args)
        captured = capsys.readouterr()

        # Non-JSON output should be just text (not JSON)
        with pytest.raises(json.JSONDecodeError):
            json.loads(captured.out)


class TestRulesInjectContextFiltering:
    """Tests for context-aware rule filtering."""

    def test_transition_filter_returns_transition_rules(
        self, edison_project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Specifying --transition should return rules for that transition."""
        from edison.cli.rules.inject import main, register_args

        # Use bundled wip->done transition which has RULE.GUARDS.FAIL_CLOSED
        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--json",
            "--transition", "wip->done",
            "--repo-root", str(edison_project),
        ])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)
        rule_ids = [r["id"] for r in data["rules"]]
        # Bundled wip->done has RULE.GUARDS.FAIL_CLOSED
        assert "RULE.GUARDS.FAIL_CLOSED" in rule_ids or len(rule_ids) > 0

    def test_context_filter_returns_matching_rules(
        self, edison_project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Specifying --context should filter rules by context."""
        from edison.cli.rules.inject import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--json",
            "--context", "delegation",
            "--repo-root", str(edison_project),
        ])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)
        # Contexts should include the requested context
        assert "delegation" in data["contexts"]


class TestRulesInjectInjectionRendering:
    """Tests for injection text rendering."""

    def test_injection_contains_rule_content(
        self, edison_project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Injection text should contain rendered rule content."""
        from edison.cli.rules.inject import main, register_args

        # Use bundled wip->done transition which has rules
        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--json",
            "--transition", "wip->done",
            "--repo-root", str(edison_project),
        ])

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0
        data = json.loads(captured.out)
        # If we have rules, injection should have content
        if data["rules"]:
            assert len(data["injection"]) > 0

    def test_empty_rules_returns_empty_injection(
        self, edison_project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """When no rules match, injection should be empty or minimal."""
        from edison.cli.rules.inject import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--json",
            "--transition", "nonexistent->state",
            "--repo-root", str(edison_project),
        ])

        main(args)
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert data["rules"] == []
        # Empty rules = empty injection
        assert data["injection"] == "" or data["injection"].strip() == ""


class TestRulesInjectSessionContext:
    """Tests for session/task context integration."""

    def test_session_id_included_in_output(
        self, edison_project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """sessionId should reflect the provided --session-id."""
        from edison.cli.rules.inject import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--json",
            "--session-id", "test-session-123",
            "--repo-root", str(edison_project),
        ])

        main(args)
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert data["sessionId"] == "test-session-123"

    def test_task_id_included_in_output(
        self, edison_project: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """taskId should reflect the provided --task-id."""
        from edison.cli.rules.inject import main, register_args

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args([
            "--json",
            "--task-id", "task-456",
            "--repo-root", str(edison_project),
        ])

        main(args)
        captured = capsys.readouterr()

        data = json.loads(captured.out)
        assert data["taskId"] == "task-456"


class TestRulesInjectRepoRootBehavior:
    """Tests for --repo-root behavior when environment/cwd are unrelated."""

    def test_transition_rules_respect_repo_root_even_when_cwd_is_elsewhere(
        self,
        edison_project: Path,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Transition lookup should use provided --repo-root, not cwd-derived project root."""
        from edison.cli.rules.inject import main, register_args

        # Simulate a client that runs outside the repo and does NOT set AGENTS_PROJECT_ROOT.
        monkeypatch.delenv("AGENTS_PROJECT_ROOT", raising=False)
        outside = tmp_path / "outside"
        outside.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(outside)

        # Ensure any cached project root is cleared for this test.
        try:
            import edison.core.utils.paths.resolver as paths  # type: ignore

            paths._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]
        except Exception:
            pass

        parser = argparse.ArgumentParser()
        register_args(parser)
        args = parser.parse_args(
            [
                "--json",
                "--transition",
                "wip->done",
                "--repo-root",
                str(edison_project),
            ]
        )

        exit_code = main(args)
        captured = capsys.readouterr()

        assert exit_code == 0, captured.err
        data = json.loads(captured.out)
        assert len(data["rules"]) > 0, "wip->done should yield workflow rules under --repo-root"
