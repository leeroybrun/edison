from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import pytest

from edison.core.session import manager as session_manager
from edison.core.session import store as session_store
from edison.core.session.context import SessionContext
from edison.core.utils.subprocess import run_with_timeout


ZEN_SERVER_ROOT = Path.home() / "Documents" / "Development" / "zen-mcp-server"


SCRIPT_TEMPLATE = """
import json
import os
from pathlib import Path

cwd = os.getcwd()
Path("clink-cwd.txt").write_text(cwd)
print(json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": cwd}}))
print(json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1, "output_tokens": 1}}))
"""


async def _run_clink(prompt: str, cli_dir: Path, cli_name: str = "codex"):
    from clink.agents import create_agent  # type: ignore
    from clink.models import ResolvedCLIClient, ResolvedCLIRole  # type: ignore

    prompt_path = (cli_dir / "prompt.txt").resolve()
    script_path = (cli_dir / "cli_probe.py").resolve()

    role = ResolvedCLIRole(
        name="default",
        prompt_path=prompt_path,
        role_args=[],
        description=None,
    )
    client = ResolvedCLIClient(
        name=cli_name,
        executable=["python3", str(script_path)],
        working_dir=None,
        internal_args=["exec"],
        config_args=[],
        env={},
        timeout_seconds=120,
        parser="codex_jsonl",
        runner=cli_name,
        roles={"default": role},
        output_to_file=None,
    )

    agent = create_agent(client)
    return await agent.run(role=role, prompt=prompt, system_prompt=None, files=[], images=[])


@pytest.mark.integration
def test_clink_runs_in_session_worktree(monkeypatch, isolated_project_env: Path):
    repo_root = isolated_project_env

    # Initial commit so worktrees can be created reliably
    (repo_root / "README.md").write_text("base\n", encoding="utf-8")
    run_with_timeout(["git", "add", "README.md"], cwd=repo_root, check=True)
    run_with_timeout(["git", "commit", "-m", "init"], cwd=repo_root, check=True)
    run_with_timeout(["git", "branch", "-M", "main"], cwd=repo_root, check=True)

    # Create a real worktree on a session branch
    session_id = "zen-wt"
    branch = f"session/{session_id}"
    worktree_path = repo_root / ".worktrees" / session_id
    run_with_timeout(
        ["git", "worktree", "add", str(worktree_path), "-b", branch],
        cwd=repo_root,
        check=True,
    )
    assert worktree_path.exists()

    # Materialize session record and attach the worktree metadata
    session_manager.create_session(session_id, owner="tester", create_wt=False)
    session = session_store.load_session(session_id)
    session.setdefault("git", {})["worktreePath"] = str(worktree_path)
    session["git"]["branchName"] = branch
    session_store.save_session(session_id, session)

    # Stub CLI client that writes the cwd into clink-cwd.txt
    cli_dir = repo_root / ".zen-test-clients"
    cli_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = cli_dir / "prompt.txt"
    prompt_path.write_text("prompt\n", encoding="utf-8")
    script_path = cli_dir / "cli_probe.py"
    script_path.write_text(SCRIPT_TEMPLATE, encoding="utf-8")

    config_path = cli_dir / "codex.json"
    config_path.write_text(
        json.dumps(
            {
                "name": "codex",
                "command": f"python3 {script_path}",
                "roles": {
                    "default": {
                        "prompt_path": str(prompt_path),
                        "role_args": [],
                    }
                },
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # Simulate pre-fix global state: server root and default ZEN_WORKING_DIR
    monkeypatch.setenv("CLI_CLIENTS_CONFIG_PATH", str(cli_dir))
    monkeypatch.setenv("ZEN_MCP_SERVER_DIR", str(ZEN_SERVER_ROOT))
    monkeypatch.setenv("ZEN_WORKING_DIR", str(repo_root))

    # Build per-session environment for Zen
    env = SessionContext.build_zen_environment(session_id, base_env=os.environ.copy())
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    # Execute clink from the repo root (server context) and ensure outputs land in worktree
    os.chdir(repo_root)
    asyncio.run(_run_clink("write cwd to file", cli_dir))

    worktree_file = worktree_path / "clink-cwd.txt"
    root_file = repo_root / "clink-cwd.txt"

    assert worktree_file.exists(), "clink output should be written inside session worktree"
    assert not root_file.exists(), "root repo must remain untouched by clink run"
    assert worktree_file.read_text().strip() == str(worktree_path)
