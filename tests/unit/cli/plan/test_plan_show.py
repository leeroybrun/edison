"""
Tests for edison plan show command.

Verifies that `edison plan show <plan-id-or-name>` correctly:
- Prints raw plan Markdown content in human mode
- Returns JSON with recordType, id, path, content in --json mode
- Supports --repo-root like other record CLIs
- Returns non-zero exit code when plan not found
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


def _create_plan_file(plans_dir: Path, name: str, content: str) -> Path:
    """Create a plan file in the plans directory."""
    plan_path = plans_dir / f"{name}.md"
    plan_path.write_text(content, encoding="utf-8")
    return plan_path


@pytest.fixture
def project_with_plans(isolated_project_env: Path) -> Path:
    """Create a project with sample plans."""
    root = isolated_project_env

    # Create the plans directory under .project
    plans_dir = root / ".project" / "plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    # Create sample plans
    _create_plan_file(
        plans_dir,
        "001-feature-auth",
        """---
id: 001-feature-auth
title: "Authentication Feature Plan"
status: draft
created_at: "2025-01-01T00:00:00Z"
---

# Authentication Feature Plan

## Goals
- Implement JWT-based authentication
- Add login/logout endpoints

## Non-Goals
- OAuth2 support (future work)

## Milestones
1. Design API endpoints
2. Implement token generation
3. Add middleware
""",
    )

    _create_plan_file(
        plans_dir,
        "002-refactor-db",
        """---
id: 002-refactor-db
title: "Database Refactoring Plan"
status: approved
created_at: "2025-01-01T00:00:00Z"
---

# Database Refactoring Plan

## Goals
- Migrate from SQLite to PostgreSQL
- Optimize query performance
""",
    )

    return root


@pytest.mark.plan
class TestPlanShowHumanMode:
    """Test plan show in human-readable (text) mode."""

    def test_show_plan_prints_content(
        self,
        project_with_plans: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Plan show should print the raw Markdown content."""
        from edison.cli.plan.show import main, register_args

        args = argparse.Namespace(
            plan_id="001-feature-auth",
            json=False,
            repo_root=project_with_plans,
        )
        rc = main(args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "# Authentication Feature Plan" in out
        assert "Implement JWT-based authentication" in out

    def test_show_plan_not_found_returns_error(
        self,
        project_with_plans: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Plan show should return non-zero exit code when plan not found."""
        from edison.cli.plan.show import main

        args = argparse.Namespace(
            plan_id="999-nonexistent",
            json=False,
            repo_root=project_with_plans,
        )
        rc = main(args)

        assert rc == 1
        err = capsys.readouterr().err
        assert "not found" in err.lower() or "error" in err.lower()


@pytest.mark.plan
class TestPlanShowJsonMode:
    """Test plan show in JSON mode."""

    def test_show_plan_json_output_structure(
        self,
        project_with_plans: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Plan show --json should return proper JSON structure."""
        from edison.cli.plan.show import main

        args = argparse.Namespace(
            plan_id="001-feature-auth",
            json=True,
            repo_root=project_with_plans,
        )
        rc = main(args)

        assert rc == 0
        out = capsys.readouterr().out
        payload = json.loads(out)

        # Verify JSON structure matches specification
        assert payload["recordType"] == "plan"
        assert payload["id"] == "001-feature-auth"
        assert "path" in payload
        assert payload["path"].endswith("001-feature-auth.md")
        assert "content" in payload
        assert "# Authentication Feature Plan" in payload["content"]

    def test_show_plan_json_includes_full_content(
        self,
        project_with_plans: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Plan show --json content field should contain full Markdown."""
        from edison.cli.plan.show import main

        args = argparse.Namespace(
            plan_id="002-refactor-db",
            json=True,
            repo_root=project_with_plans,
        )
        rc = main(args)

        assert rc == 0
        payload = json.loads(capsys.readouterr().out)
        assert "Migrate from SQLite to PostgreSQL" in payload["content"]

    def test_show_plan_json_error_on_not_found(
        self,
        project_with_plans: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Plan show --json should return JSON error when plan not found."""
        from edison.cli.plan.show import main

        args = argparse.Namespace(
            plan_id="999-nonexistent",
            json=True,
            repo_root=project_with_plans,
        )
        rc = main(args)

        assert rc == 1
        out = capsys.readouterr().out
        payload = json.loads(out)
        assert "error" in payload


@pytest.mark.plan
class TestPlanShowRepoRoot:
    """Test plan show with --repo-root option."""

    def test_register_args_includes_repo_root(self) -> None:
        """register_args should add --repo-root argument."""
        from edison.cli.plan.show import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)

        # Should not raise for repo-root
        args = parser.parse_args(["test-plan", "--repo-root", "/tmp/project"])
        assert args.repo_root == "/tmp/project"

    def test_register_args_includes_json_flag(self) -> None:
        """register_args should add --json flag."""
        from edison.cli.plan.show import register_args

        parser = argparse.ArgumentParser()
        register_args(parser)

        args = parser.parse_args(["test-plan", "--json"])
        assert args.json is True

    def test_show_uses_provided_repo_root(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Plan show should use the provided --repo-root path."""
        # Create a plan in a custom location
        plans_dir = tmp_path / ".project" / "plans"
        plans_dir.mkdir(parents=True)
        _create_plan_file(
            plans_dir,
            "custom-plan",
            "# Custom Plan\n\nContent here.",
        )

        from edison.cli.plan.show import main

        args = argparse.Namespace(
            plan_id="custom-plan",
            json=False,
            repo_root=tmp_path,
        )
        rc = main(args)

        assert rc == 0
        out = capsys.readouterr().out
        assert "# Custom Plan" in out


@pytest.mark.plan
class TestPlanShowModule:
    """Test plan show module attributes."""

    def test_module_has_summary(self) -> None:
        """Module should have SUMMARY constant for CLI help."""
        from edison.cli.plan import show

        assert hasattr(show, "SUMMARY")
        assert isinstance(show.SUMMARY, str)
        assert len(show.SUMMARY) > 0

    def test_module_has_main(self) -> None:
        """Module should have main function."""
        from edison.cli.plan import show

        assert hasattr(show, "main")
        assert callable(show.main)

    def test_module_has_register_args(self) -> None:
        """Module should have register_args function."""
        from edison.cli.plan import show

        assert hasattr(show, "register_args")
        assert callable(show.register_args)
