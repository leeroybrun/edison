import json
from argparse import Namespace

from edison.cli.task import ready as task_ready
from edison.core.session._config import get_config


def test_task_ready_lists_global_todo_tasks_even_with_session_id_file(project_root, monkeypatch, capsys):
    """`edison task ready` should list claimable todo tasks even inside a worktree/session.

    The repository can have a `.project/.session-id` file (worktree auto-resolution), but
    listing ready tasks should not silently filter out global (unclaimed) tasks unless the
    user explicitly passes `--session`.
    """
    monkeypatch.chdir(project_root)

    # Simulate being inside a session/worktree: auto-resolvers can discover a session id.
    (project_root / ".project" / ".session-id").write_text("sess-1\n", encoding="utf-8")

    # Create a minimal session record so auto-resolution considers the session id "real".
    cfg = get_config(repo_root=project_root)
    lookup_order = cfg.get_session_lookup_order()
    assert lookup_order, "test harness requires configured session lookup states"
    state = str(lookup_order[0])
    dir_name = cfg.get_session_states().get(state, state)
    session_json = (project_root / cfg.get_session_root_path() / dir_name / "sess-1" / "session.json")
    session_json.parent.mkdir(parents=True, exist_ok=True)
    session_json.write_text("{}", encoding="utf-8")

    todo_dir = project_root / ".project" / "tasks" / "todo"
    todo_dir.mkdir(parents=True, exist_ok=True)

    task_path = todo_dir / "001-test-T001.md"
    task_path.write_text(
        "---\n"
        "id: 001-test-T001\n"
        "title: Example ready task\n"
        "owner: test\n"
        "---\n"
        "\n"
        "# Example ready task\n",
        encoding="utf-8",
    )

    args = Namespace(record_id=None, session=None, json=True, repo_root=str(project_root))
    rc = task_ready.main(args)
    assert rc == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["count"] == 1
    assert payload["tasks"][0]["id"] == "001-test-T001"
