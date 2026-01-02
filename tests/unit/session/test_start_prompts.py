from __future__ import annotations

from pathlib import Path

import pytest


def test_list_and_read_start_prompts_prefers_project_generated(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True, exist_ok=True)

    gen_dir = project_root / ".edison" / "_generated" / "start"
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "START_FOO.md").write_text("# START_FOO\nfrom project\n", encoding="utf-8")

    from edison.core.session.start_prompts import list_start_prompts, read_start_prompt, find_start_prompt_path

    assert "FOO" in list_start_prompts(project_root)
    assert find_start_prompt_path(project_root, "FOO") == gen_dir / "START_FOO.md"
    assert read_start_prompt(project_root, "FOO").startswith("# START_FOO")


def test_read_start_prompt_errors_with_available_list(tmp_path: Path) -> None:
    project_root = tmp_path / "proj"
    project_root.mkdir(parents=True, exist_ok=True)

    gen_dir = project_root / ".edison" / "_generated" / "start"
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "START_BAR.md").write_text("# START_BAR\n", encoding="utf-8")

    from edison.core.session.start_prompts import read_start_prompt

    with pytest.raises(FileNotFoundError) as exc:
        read_start_prompt(project_root, "NOPE")

    assert "BAR" in str(exc.value)


def test_read_start_prompt_processes_includes_and_functions_when_not_generated(
    isolated_project_env: Path,
) -> None:
    """When .edison/_generated/start is missing, read_start_prompt() should still render templates."""
    from edison.core.session.start_prompts import read_start_prompt

    content = read_start_prompt(isolated_project_env, "NEW_SESSION")

    assert content.startswith("# START_NEW_SESSION")
    # Includes from the bundled START template should be expanded.
    assert "{{include:" not in content
    assert "{{include-section:" not in content
    # Functions inside included guidelines must be resolved (e.g. paths helpers).
    assert "{{fn:" not in content
    assert "Worktree Confinement (CRITICAL)" in content
    assert ".project/" in content
