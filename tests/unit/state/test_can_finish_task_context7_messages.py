from __future__ import annotations

from pathlib import Path

import pytest


def _write_task(root: Path, task_id: str, *, primary: list[str]) -> None:
    p = root / ".project" / "tasks" / "wip" / f"{task_id}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "\n".join(
            [
                "---",
                f"id: {task_id}",
                "title: Test",
                "---",
                "",
                "## Primary Files / Areas",
                *[f"- {x}" for x in primary],
                "",
            ]
        ),
        encoding="utf-8",
    )


@pytest.mark.task
def test_can_finish_task_context7_missing_vs_invalid_are_distinguished(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    # Configure Context7 triggers for this isolated repo.
    (root / ".edison" / "config" / "context7.yaml").write_text(
        """
context7:
  triggers:
    react: ["**/*.tsx"]
""".lstrip(),
        encoding="utf-8",
    )

    task_id = "ctx7-msg"
    _write_task(root, task_id, primary=["ui/Widget.tsx"])

    # Ensure an evidence round exists (so the error can point at a concrete dir).
    from edison.core.qa.evidence import EvidenceService

    ev = EvidenceService(task_id, project_root=root)
    round_dir = ev.ensure_round(1)

    # Write an invalid marker (missing topics).
    (round_dir / "context7-react.txt").write_text(
        "---\nlibraryId: /org/react\n---\n",
        encoding="utf-8",
    )

    from edison.core.state.builtin.guards.task import can_finish_task

    with pytest.raises(ValueError) as exc:
        can_finish_task({"task": {"id": task_id}, "project_root": root, "enforce_evidence": False})

    msg = str(exc.value)
    assert "Context7" in msg
    assert "Invalid" in msg  # invalid marker must be called out
    assert "Missing" not in msg  # should not collapse invalid into missing
    assert str(round_dir) in msg


@pytest.mark.task
def test_can_finish_task_allows_explicit_context7_bypass_with_reason(
    isolated_project_env: Path,
) -> None:
    root = isolated_project_env

    (root / ".edison" / "config" / "context7.yaml").write_text(
        """
context7:
  triggers:
    react: ["**/*.tsx"]
""".lstrip(),
        encoding="utf-8",
    )

    task_id = "ctx7-bypass"
    _write_task(root, task_id, primary=["ui/Widget.tsx"])

    from edison.core.qa.evidence import EvidenceService

    ev = EvidenceService(task_id, project_root=root)
    round_dir = ev.ensure_round(1)
    (round_dir / "implementation-report.md").write_text(
        """---
summary: "test"
filesChanged:
  - ui/Widget.tsx
---
""",
        encoding="utf-8",
    )

    from edison.core.state.builtin.guards.task import can_finish_task

    assert can_finish_task(
        {
            "task": {"id": task_id},
            "project_root": root,
            "enforce_evidence": False,
            "skip_context7": True,
            "skip_context7_reason": "verified false positive",
        }
    )
