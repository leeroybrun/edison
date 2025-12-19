import json
from pathlib import Path

from edison.cli._dispatcher import main as edison_main

from tests.helpers.io_utils import write_yaml


def test_audit_event_command_writes_audit_jsonl(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(
        cfg_dir / "logging.yaml",
        {
            "logging": {
                "enabled": True,
                "audit": {
                    "enabled": True,
                    "sinks": {"jsonl": {"enabled": True, "paths": {"project": ".project/logs/edison/audit-project.jsonl"}}},
                },
                "stdio": {"capture": {"enabled": False}},
            }
        },
    )

    rc = edison_main(["audit", "event", "hook.test", "--field", "k=v", "--repo-root", str(repo)])
    assert rc == 0

    log_path = repo / ".project" / "logs" / "edison" / "audit-project.jsonl"
    assert log_path.exists()

    events = [json.loads(ln) for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert any(e.get("event") == "hook.test" and e.get("k") == "v" for e in events)

