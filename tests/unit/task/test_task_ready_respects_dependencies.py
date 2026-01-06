import json
from argparse import Namespace

from edison.cli.task import ready as task_ready


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


def test_task_ready_excludes_tasks_with_unmet_depends_on(project_root, monkeypatch, capsys):
    monkeypatch.chdir(project_root)

    todo_dir = project_root / ".project" / "tasks" / "todo"
    todo_dir.mkdir(parents=True, exist_ok=True)

    dep_id = "001-test-dep"
    main_id = "002-test-main"

    _write_task(todo_dir / f"{dep_id}.md", task_id=dep_id, title="Dependency")
    _write_task(
        todo_dir / f"{main_id}.md",
        task_id=main_id,
        title="Depends on dep",
        extra_frontmatter=(
            "relationships:\n"
            "  - type: depends_on\n"
            f"    target: {dep_id}\n"
        ),
    )

    args = Namespace(record_id=None, session=None, json=True, repo_root=str(project_root))
    rc = task_ready.main(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["tasks"][0]["id"] == dep_id


def test_task_ready_includes_tasks_when_dependencies_are_done(project_root, monkeypatch, capsys):
    monkeypatch.chdir(project_root)

    todo_dir = project_root / ".project" / "tasks" / "todo"
    done_dir = project_root / ".project" / "tasks" / "done"
    todo_dir.mkdir(parents=True, exist_ok=True)
    done_dir.mkdir(parents=True, exist_ok=True)

    dep_id = "001-test-dep"
    main_id = "002-test-main"

    _write_task(done_dir / f"{dep_id}.md", task_id=dep_id, title="Dependency (done)")
    _write_task(
        todo_dir / f"{main_id}.md",
        task_id=main_id,
        title="Ready once dep is done",
        extra_frontmatter=(
            "relationships:\n"
            "  - type: depends_on\n"
            f"    target: {dep_id}\n"
        ),
    )

    args = Namespace(record_id=None, session=None, json=True, repo_root=str(project_root))
    rc = task_ready.main(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["tasks"][0]["id"] == main_id
