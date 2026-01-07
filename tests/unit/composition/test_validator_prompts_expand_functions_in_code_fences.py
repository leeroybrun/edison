from __future__ import annotations

from pathlib import Path

def test_validator_prompts_expand_functions_inside_code_fences(
    isolated_project_env: Path,
    monkeypatch,
) -> None:
    """Validator prompts use code fences for runnable command blocks.

    These blocks intentionally contain template functions (e.g. `ci_command`,
    and must be rendered into concrete commands so CLI validators don't see
    unresolved `{{fn:...}}` markers at runtime.
    """
    monkeypatch.chdir(isolated_project_env)

    project_dir = isolated_project_env / ".edison"
    (project_dir / "config").mkdir(parents=True, exist_ok=True)
    (project_dir / "config" / "ci.yaml").write_text(
        "ci:\n"
        "  commands:\n"
        "    dependency-audit: \"echo DEP_AUDIT\"\n",
        encoding="utf-8",
    )

    from edison.core.composition.registries.validator_prompts import ValidatorPromptRegistry

    rendered = ValidatorPromptRegistry(project_root=isolated_project_env).compose(
        "critical/security",
        packs=["python"],
    )
    assert rendered is not None

    # Functions should be expanded even when used inside code fences.
    assert "{{fn:ci_command" not in rendered
    assert "echo DEP_AUDIT" in rendered
