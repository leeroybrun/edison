from __future__ import annotations

from pathlib import Path

from edison.core.qa import promoter


def test_collect_task_files_excludes_qa_files(isolated_project_env: Path) -> None:
    repo = isolated_project_env

    task_id = "T001"
    task_path = repo / ".project" / "tasks" / "done" / f"{task_id}.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    task_path.write_text("---\nid: T001\ntitle: T001\n---\n", encoding="utf-8")

    qa_path = repo / ".project" / "qa" / "done" / f"{task_id}-qa.md"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text("---\nid: T001-qa\ntask_id: T001\n---\n", encoding="utf-8")

    files = promoter.collect_task_files([task_id])
    assert task_path in files
    assert qa_path not in files

