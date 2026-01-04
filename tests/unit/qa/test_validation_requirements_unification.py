from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.paths import get_repo_root


@pytest.mark.qa
def test_validator_registry_roster_accepts_preset_override_and_applies_blocking_validators(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preset blocking_validators must control blockingness for preset-selected validators."""
    from edison.core.context.files import FileContext
    from edison.core.context.files import FileContextService
    from edison.core.registries.validators import ValidatorRegistry

    def _fake_get_for_task(self: FileContextService, task_id: str, session_id: str | None):
        _ = (task_id, session_id)
        # Stable set of files; deep preset is explicit so inference shouldn't matter.
        return FileContext(all_files=["src/app.py"], source="test")

    monkeypatch.setattr(FileContextService, "get_for_task", _fake_get_for_task, raising=True)

    repo_root = get_repo_root()
    registry = ValidatorRegistry(project_root=repo_root)

    # Deep preset is defined in `.edison/config/validation.yaml` and should be usable explicitly.
    roster = registry.build_execution_roster(
        task_id="T-DEEP",
        session_id=None,
        wave=None,
        extra_validators=None,
        preset_name="deep",
    )

    assert roster.get("preset") == "deep"

    always_required = roster.get("alwaysRequired") or []
    by_id = {v["id"]: v for v in always_required}

    assert by_id["security"]["blocking"] is True
    # Deep preset includes performance but does NOT list it as blocking.
    assert by_id["performance"]["blocking"] is False


@pytest.mark.qa
def test_session_close_uses_configured_preset() -> None:
    """Session-close requirements must be driven by validation.sessionClose.preset."""
    from edison.core.qa.policy.session_close import get_session_close_policy

    policy = get_session_close_policy(project_root=Path(get_repo_root()))
    assert policy.preset.name == "deep"
    assert "command-test-full.txt" in (policy.required_evidence or [])

