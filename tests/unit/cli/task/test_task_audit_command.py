from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest


def _write_task(path: Path, *, task_id: str, title: str, body: str, extra_fm: str = "") -> None:
    content = (
        "---\n"
        f"id: {task_id}\n"
        f"title: {json.dumps(title)}\n"
        "created_at: \"2025-12-28T00:00:00Z\"\n"
        "updated_at: \"2025-12-28T00:00:00Z\"\n"
        "tags: [edison-core]\n"
        f"{extra_fm}"
        "---\n\n"
        f"# {title}\n\n"
        f"{body.strip()}\n"
    )
    path.write_text(content, encoding="utf-8")


@pytest.mark.task
def test_task_audit_reports_overlap_and_implicit_references(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = isolated_project_env
    tasks_dir = root / ".project" / "tasks" / "todo"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    _write_task(
        tasks_dir / "001-alpha.md",
        task_id="001-alpha",
        title="Duplicate Title",
        body="""
Mentions task `002-beta` but does not link it.

## Files to Create/Modify

```
src/app.py
```
""",
    )
    _write_task(
        tasks_dir / "002-beta.md",
        task_id="002-beta",
        title="Duplicate Title",
        body="""
## Files to Create/Modify

```
src/other.py
```
""",
    )
    _write_task(
        tasks_dir / "003-gamma.md",
        task_id="003-gamma",
        title="Unrelated",
        body="""
## Files to Create/Modify

```
src/app.py
```
""",
    )

    from edison.cli.task.audit import main as audit_main

    args = argparse.Namespace(
        repo_root=root,
        json=True,
        tasks_root=str(root / ".project" / "tasks"),
        include_session_tasks=False,
        threshold=0.8,
        top_k=3,
    )
    rc = audit_main(args)
    assert rc == 0

    out = capsys.readouterr().out
    payload = json.loads(out)

    assert payload["taskCount"] == 3
    issues = payload.get("issues", [])
    assert any(i.get("code") == "implicit_reference" for i in issues)
    assert any(i.get("code") == "file_overlap" for i in issues)

    duplicates = payload.get("duplicates", [])
    assert any(
        {d.get("a"), d.get("b")} == {"001-alpha", "002-beta"} and d.get("score", 0) >= 0.8
        for d in duplicates
    )


@pytest.mark.task
def test_task_audit_suppresses_overlap_when_tasks_are_ordered(
    isolated_project_env: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = isolated_project_env
    tasks_dir = root / ".project" / "tasks" / "todo"
    tasks_dir.mkdir(parents=True, exist_ok=True)

    _write_task(
        tasks_dir / "001-alpha.md",
        task_id="001-alpha",
        title="Alpha",
        body="""
## Files to Create/Modify

```
src/app.py
```
""",
    )
    _write_task(
        tasks_dir / "002-beta.md",
        task_id="002-beta",
        title="Beta",
        extra_fm="depends_on:\n  - 001-alpha\n",
        body="""
## Files to Create/Modify

```
src/app.py
```
""",
    )

    from edison.cli.task.audit import main as audit_main

    args = argparse.Namespace(
        repo_root=root,
        json=True,
        tasks_root=str(root / ".project" / "tasks"),
        include_session_tasks=False,
        threshold=0.8,
        top_k=3,
    )
    rc = audit_main(args)
    assert rc == 0

    out = capsys.readouterr().out
    payload = json.loads(out)
    issues = payload.get("issues", [])
    assert not any(i.get("code") == "file_overlap" for i in issues)
