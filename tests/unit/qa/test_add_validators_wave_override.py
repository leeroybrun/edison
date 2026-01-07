from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers import (
    create_repo_with_git,
    create_project_structure,
    create_task_file,
    setup_project_root,
)
from tests.helpers.cache_utils import reset_edison_caches


def _seed_impl_report(project_root: Path, task_id: str, files: list[str]) -> None:
    from edison.core.qa.evidence import EvidenceService

    ev = EvidenceService(task_id, project_root=project_root)
    ev.ensure_round(1)
    ev.write_implementation_report(
        {"summary": "test", "filesChanged": files},
        round_num=1,
    )


def _disable_cli_engines(project_root: Path) -> None:
    cfg_dir = project_root / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "orchestration.yml").write_text(
        "orchestration:\n"
        "  allowCliEngines: false\n",
        encoding="utf-8",
    )


@pytest.mark.qa
def test_add_validators_wave_prefix_executes_in_requested_wave(tmp_path: Path, monkeypatch) -> None:
    """`--add-validators <wave>:<id>` must run the validator in that wave even if its config wave differs."""
    repo = create_repo_with_git(tmp_path)
    create_project_structure(repo)
    _disable_cli_engines(repo)
    setup_project_root(monkeypatch, repo)
    reset_edison_caches()

    create_task_file(repo, "T001", state="wip", title="Wave Override")
    # Use docs changes so the inferred preset would normally avoid critical validators.
    _seed_impl_report(repo, "T001", ["docs/README.md"])

    from edison.core.qa.engines import ValidationExecutor

    executor = ValidationExecutor(project_root=repo, max_workers=1)

    # Control: comprehensive wave should be empty by default for docs-only changes.
    control = executor.execute(
        task_id="T001",
        session_id="test",
        wave="comprehensive",
        parallel=False,
    )
    assert control.waves and control.waves[0].wave == "comprehensive"
    assert all(v.validator_id != "security" for v in control.waves[0].validators)

    # Now explicitly request the critical validator "security" to run in the comprehensive wave.
    result = executor.execute(
        task_id="T001",
        session_id="test",
        wave="comprehensive",
        parallel=False,
        extra_validators=[{"id": "security", "wave": "comprehensive"}],
    )

    assert result.waves and result.waves[0].wave == "comprehensive"
    assert any(v.validator_id == "security" for v in result.waves[0].validators)
