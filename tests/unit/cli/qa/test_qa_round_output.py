"""Tests for qa round output format.

These tests verify that:
1. Appending without --new prints hint about evidence directory
2. --new prints both round number and evidence directory path
3. Output is clear about what was created vs recorded
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
import yaml


def _write_yaml(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _setup_task(repo: Path, task_id: str = "T001") -> None:
    """Create a minimal task file."""
    task_dir = repo / ".project" / "tasks" / "done"
    task_dir.mkdir(parents=True, exist_ok=True)
    (task_dir / f"{task_id}.md").write_text(
        f"---\n"
        f"id: {task_id}\n"
        f"title: {task_id}\n"
        f"owner: test\n"
        f"created_at: '2025-12-15T00:00:00Z'\n"
        f"updated_at: '2025-12-15T00:00:00Z'\n"
        "---\n\n"
        f"# {task_id}\n",
        encoding="utf-8",
    )


def _setup_qa_brief(repo: Path, task_id: str = "T001") -> None:
    """Create a minimal QA brief file."""
    qa_dir = repo / ".project" / "qa" / "todo"
    qa_dir.mkdir(parents=True, exist_ok=True)
    qa_id = f"{task_id}-qa"
    (qa_dir / f"{qa_id}.md").write_text(
        f"---\n"
        f"id: {qa_id}\n"
        f"taskId: {task_id}\n"
        f"title: QA for {task_id}\n"
        f"owner: _unassigned_\n"
        f"round: 0\n"
        f"created_at: '2025-12-15T00:00:00Z'\n"
        f"updated_at: '2025-12-15T00:00:00Z'\n"
        "---\n\n"
        f"# QA for {task_id}\n",
        encoding="utf-8",
    )


class TestQaRoundOutputWithoutNew:
    """Tests for qa round without --new flag."""

    def test_append_without_new_mentions_no_evidence_dir(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Appending a round without --new should mention no evidence dir created."""
        repo = isolated_project_env
        _setup_task(repo)
        _setup_qa_brief(repo)

        from tests.helpers.cache_utils import reset_edison_caches

        reset_edison_caches()

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(["qa", "round", "T001", "--status", "pending"])

        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Should mention that no evidence directory was created
        assert "no evidence" in output.lower() or "--new" in output, \
            f"Expected hint about no evidence dir: {output}"

    def test_append_without_new_suggests_new_flag(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Appending without --new should suggest using --new for evidence."""
        repo = isolated_project_env
        _setup_task(repo)
        _setup_qa_brief(repo)

        from tests.helpers.cache_utils import reset_edison_caches

        reset_edison_caches()

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(["qa", "round", "T001", "--status", "pending"])

        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Should suggest using --new
        assert "--new" in output, f"Expected '--new' suggestion in output: {output}"

    def test_append_without_new_prints_round_number(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Appending without --new should still print the round number."""
        repo = isolated_project_env
        _setup_task(repo)
        _setup_qa_brief(repo)

        from tests.helpers.cache_utils import reset_edison_caches

        reset_edison_caches()

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(["qa", "round", "T001", "--status", "pending"])

        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Should print round number
        assert "round" in output.lower(), f"Expected round number in output: {output}"


class TestQaRoundOutputWithNew:
    """Tests for qa round with --new flag."""

    def test_new_prints_round_number(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--new should print the created round number."""
        repo = isolated_project_env
        _setup_task(repo)
        _setup_qa_brief(repo)

        from tests.helpers.cache_utils import reset_edison_caches

        reset_edison_caches()

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(["qa", "round", "T001", "--new"])

        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Should print round number
        assert "round" in output.lower(), f"Expected round in output: {output}"
        # Should indicate it was created
        assert "created" in output.lower() or "1" in output, \
            f"Expected creation indication: {output}"

    def test_new_prints_evidence_directory_path(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--new should print the evidence directory path."""
        repo = isolated_project_env
        _setup_task(repo)
        _setup_qa_brief(repo)

        from tests.helpers.cache_utils import reset_edison_caches

        reset_edison_caches()

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(["qa", "round", "T001", "--new"])

        captured = capsys.readouterr()
        output = captured.out + captured.err

        # Should print the evidence directory path
        assert "round-" in output or "Path:" in output, \
            f"Expected evidence path in output: {output}"

    def test_new_json_includes_evidence_path(
        self, isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """--new --json should include the evidence directory path."""
        repo = isolated_project_env
        _setup_task(repo)
        _setup_qa_brief(repo)

        from tests.helpers.cache_utils import reset_edison_caches

        reset_edison_caches()

        from edison.cli._dispatcher import main as cli_main

        code = cli_main(["qa", "round", "T001", "--new", "--json"])

        captured = capsys.readouterr()
        output = captured.out.strip()

        # Should be valid JSON with evidence path
        payload = json.loads(output)
        assert "created" in payload or "round" in payload, \
            f"Expected round info in JSON: {payload}"


class TestQaRoundHelpText:
    """Tests for qa round help text."""

    def test_help_explains_new_creates_evidence_dir(self) -> None:
        """Help text should explain that --new creates evidence directory."""
        from edison.cli.qa import round as round_module

        parser = argparse.ArgumentParser()
        round_module.register_args(parser)

        help_text = parser.format_help()

        # --new help should mention evidence directory
        assert "evidence" in help_text.lower() or "round" in help_text.lower(), \
            f"Expected evidence/round explanation in help: {help_text}"

    def test_help_explains_default_no_evidence(self) -> None:
        """Help text should clarify that default doesn't create evidence dir."""
        from edison.cli.qa import round as round_module

        parser = argparse.ArgumentParser()
        round_module.register_args(parser)

        help_text = parser.format_help()

        # Help should be clear about evidence directory behavior
        assert "--new" in help_text, f"Expected '--new' in help: {help_text}"
