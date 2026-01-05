from __future__ import annotations

from pathlib import Path

from edison.core.qa.engines.registry import EngineRegistry
from tests.helpers.io_utils import write_yaml


def test_engine_registry_blocks_validator_when_required_config_missing(
    isolated_project_env: Path,
) -> None:
    repo_root = isolated_project_env

    # Enable the pack that provides the validator and its setup requirements.
    write_yaml(
        repo_root / ".edison" / "config" / "packs.yaml",
        {"packs": {"active": ["e2e-web"]}},
    )

    reg = EngineRegistry(project_root=repo_root)
    result = reg.run_validator(
        validator_id="browser-e2e",
        task_id="T123",
        session_id="S123",
        worktree_path=repo_root,
        round_num=1,
        evidence_service=None,
    )

    assert result.verdict == "blocked"
    assert "browser-e2e" in (result.summary or "")
    assert "configure" in (result.summary or "").lower()
