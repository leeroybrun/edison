from __future__ import annotations

import argparse
from pathlib import Path

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.io_utils import write_yaml


def test_task_new_can_warn_about_duplicates_before_creating(
    isolated_project_env: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(isolated_project_env)

    from edison.core.task.models import Task
    from edison.core.task.repository import TaskRepository

    repo = TaskRepository(project_root=isolated_project_env)
    repo.create(
        Task.create(
            "401-wave1-oauth-refresh",
            "Implement OAuth2 refresh token rotation",
            description="Handle refresh token expiry and rotation",
            state="todo",
        )
    )

    # MCP provider returns a snippet closely matching the existing task.
    server_script = isolated_project_env / "mcp_server.py"
    server_script.write_text(
        r"""
import json
import sys


def _read_message():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if line in (b"\n", b"\r\n"):
            break
        if b":" in line:
            k, v = line.decode("ascii", errors="ignore").split(":", 1)
            headers[k.strip().lower()] = v.strip()
    n = int(headers.get("content-length", "0") or "0")
    if n <= 0:
        return None
    body = sys.stdin.buffer.read(n)
    return json.loads(body.decode("utf-8"))


def _send(obj):
    body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body)
    sys.stdout.buffer.flush()


msg = _read_message()
if msg and msg.get("method") == "initialize":
    _send({"jsonrpc": "2.0", "id": msg.get("id"), "result": {"capabilities": {"tools": {}}}})

_ = _read_message()  # initialized

msg = _read_message()
if msg and msg.get("method") == "tools/call":
    _send(
        {
            "jsonrpc": "2.0",
            "id": msg.get("id"),
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(
                            {"results": [{"snippet": "refresh token rotation", "similarity": 0.9}]}
                        ),
                    }
                ]
            },
        }
    )
""".lstrip(),
        encoding="utf-8",
    )

    cfg_dir = isolated_project_env / ".edison" / "config"
    write_yaml(
        cfg_dir / "mcp.yaml",
        {
            "mcp": {
                "servers": {
                    "test-memory": {"command": "python3", "args": [str(server_script)], "env": {}}
                }
            }
        },
    )
    write_yaml(
        cfg_dir / "memory.yaml",
        {
            "memory": {
                "enabled": True,
                "providers": {
                    "mcp": {
                        "kind": "mcp-tools",
                        "enabled": True,
                        "serverId": "test-memory",
                        "searchTool": "search",
                        "responseFormat": "json",
                    }
                },
            }
        },
    )
    write_yaml(
        cfg_dir / "tasks.yaml",
        {
            "tasks": {
                "similarity": {
                    "semantic": {"enabled": True, "providers": ["mcp"], "maxHits": 3},
                    "preCreate": {"enabled": True, "action": "warn"},
                }
            }
        },
    )
    reset_edison_caches()

    from edison.cli.task.new import main

    rc = main(
        argparse.Namespace(
            task_id="500",
            slug="session-renewal",
            wave=None,
            task_type="feature",
            owner=None,
            session=None,
            parent=None,
            continuation_id=None,
            json=False,
            repo_root=str(isolated_project_env),
            force=False,
        )
    )
    assert rc == 0

    out = capsys.readouterr().out
    assert "Possible duplicates" in out
    assert "401-wave1-oauth-refresh" in out

