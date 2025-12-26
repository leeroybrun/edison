import json
from argparse import Namespace


def _write_task(path, *, task_id: str, title: str, extra_frontmatter: str = "") -> None:
    path.write_text(
        "---\n"
        f"id: {task_id}\n"
        f"title: {title}\n"
        "owner: test\n"
        f"{extra_frontmatter}"
        "---\n"
        "\n"
        f"# {title}\n",
        encoding="utf-8",
    )


def test_task_blocked_lists_todo_tasks_blocked_by_depends_on(project_root, monkeypatch, capsys):
    monkeypatch.chdir(project_root)

    todo_dir = project_root / ".project" / "tasks" / "todo"
    todo_dir.mkdir(parents=True, exist_ok=True)

    dep_id = "001-test-dep"
    main_id = "002-test-main"

    _write_task(todo_dir / f"{dep_id}.md", task_id=dep_id, title="Dependency")
    _write_task(
        todo_dir / f"{main_id}.md",
        task_id=main_id,
        title="Blocked task",
        extra_frontmatter=f"depends_on: [{dep_id}]\n",
    )

    from edison.cli.task import blocked as task_blocked

    args = Namespace(record_id=None, session=None, json=True, repo_root=str(project_root))
    rc = task_blocked.main(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["tasks"][0]["id"] == main_id
    assert payload["tasks"][0]["blockedBy"][0]["dependencyId"] == dep_id
