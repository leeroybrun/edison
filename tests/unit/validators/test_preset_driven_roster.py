from __future__ import annotations

from edison.core.qa.evidence import EvidenceService
from edison.core.registries.validators import ValidatorRegistry
from tests.helpers.env_setup import setup_project_root


def _seed_impl_report(project_root, task_id: str, files: list[str]) -> None:
    (project_root / ".project").mkdir(parents=True, exist_ok=True)
    ev = EvidenceService(task_id, project_root=project_root)
    ev.ensure_round(1)
    ev.write_implementation_report(
        {"summary": "test", "filesChanged": files},
        round_num=1,
    )


def _roster_ids(roster: dict) -> set[str]:
    ids: set[str] = set()
    for key in ("alwaysRequired", "triggeredBlocking", "triggeredOptional", "extraAdded"):
        for item in roster.get(key, []) or []:
            if isinstance(item, dict) and item.get("id"):
                ids.add(str(item["id"]))
    return ids


def test_docs_preset_excludes_critical_validators(tmp_path, monkeypatch) -> None:
    setup_project_root(monkeypatch, tmp_path)
    task_id = "T-docs-1"
    _seed_impl_report(tmp_path, task_id, ["docs/README.md"])

    roster = ValidatorRegistry(project_root=tmp_path).build_execution_roster(task_id)
    ids = _roster_ids(roster)

    # Global validators always run.
    assert "global-codex" in ids
    assert "global-claude" in ids

    # Docs-only changes should not schedule critical validators like security/performance by default.
    assert "security" not in ids
    assert "performance" not in ids


def test_source_preset_includes_critical_validators(tmp_path, monkeypatch) -> None:
    setup_project_root(monkeypatch, tmp_path)
    task_id = "T-src-1"
    _seed_impl_report(tmp_path, task_id, ["src/app.py"])

    roster = ValidatorRegistry(project_root=tmp_path).build_execution_roster(task_id)
    ids = _roster_ids(roster)

    assert "global-codex" in ids
    assert "global-claude" in ids

    # Source changes should select the standard preset and include security/performance.
    assert "security" in ids
    assert "performance" in ids

