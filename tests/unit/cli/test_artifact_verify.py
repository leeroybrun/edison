from __future__ import annotations

import argparse
from pathlib import Path

import pytest


def test_artifact_verify_returns_nonzero_when_required_sections_missing(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = isolated_project_env / "some.md"
    path.write_text(
        "\n".join(
            [
                "# Test",
                "",
                "<!-- REQUIRED FILL: AcceptanceCriteria -->",
                "## Acceptance Criteria",
                "",
                "- [ ] <<FILL: acceptance criterion>>",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    from edison.cli.artifact.verify import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args([str(path), "--repo-root", str(isolated_project_env)])

    rc = main(args)
    assert rc == 1
    out = capsys.readouterr().out
    assert "Missing required sections" in out


def test_artifact_verify_returns_zero_when_no_required_markers_present(
    isolated_project_env: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = isolated_project_env / "some.md"
    path.write_text("# Test\n\nNo required markers.\n", encoding="utf-8")

    from edison.cli.artifact.verify import main, register_args

    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args([str(path), "--repo-root", str(isolated_project_env)])

    rc = main(args)
    assert rc == 0
    out = capsys.readouterr().out
    assert "OK" in out

