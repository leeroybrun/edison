from __future__ import annotations

from pathlib import Path

import yaml

from edison.core.setup import configure_project
from edison.core.setup.questionnaire import SetupQuestionnaire


def test_setup_questionnaire_skips_conditional_questions_when_worktrees_disabled(tmp_path: Path) -> None:
    q = SetupQuestionnaire(repo_root=tmp_path, assume_yes=True)
    answers = q.run(mode="basic", provided_answers={"enable_worktrees": False}, assume_yes=True)
    assert "worktrees_shared_state_mode" not in answers


def test_setup_questionnaire_includes_shared_state_mode_when_worktrees_enabled(tmp_path: Path) -> None:
    q = SetupQuestionnaire(repo_root=tmp_path, assume_yes=True)
    answers = q.run(mode="basic", provided_answers={"enable_worktrees": True}, assume_yes=True)
    assert answers["worktrees_shared_state_mode"] in {"meta", "primary", "external"}


def test_configure_project_renders_shared_state_mode_in_worktrees_config(tmp_path: Path) -> None:
    result = configure_project(
        repo_root=tmp_path,
        interactive=False,
        mode="basic",
        provided_answers={
            "enable_worktrees": True,
            "worktrees_shared_state_mode": "external",
            "worktrees_external_path": "/tmp/edison-shared",
        },
        write_files=False,
    )
    assert result["success"] is True

    configs = result["configs"]
    assert "worktrees.yml" in configs
    data = yaml.safe_load(configs["worktrees.yml"]) or {}
    wt = data.get("worktrees") or {}
    assert wt.get("enabled") is True
    ss = wt.get("sharedState") or {}
    assert ss.get("mode") == "external"
    assert ss.get("externalPath") == "/tmp/edison-shared"

