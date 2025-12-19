import json
from pathlib import Path

import pytest

from edison.core.state import RichStateMachine, StateTransitionError
from edison.core.state.actions import ActionRegistry
from edison.core.state.conditions import ConditionRegistry
from edison.core.state.guards import GuardRegistry

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.fixtures import create_repo_with_git
from tests.helpers.io_utils import write_yaml


def test_state_machine_guard_emits_audit_event(tmp_path: Path, monkeypatch) -> None:
    repo = create_repo_with_git(tmp_path, name="repo")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))

    cfg_dir = repo / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(
        cfg_dir / "logging.yaml",
        {
            "logging": {
                "enabled": True,
                "audit": {
                    "enabled": True,
                    "sinks": {
                        "jsonl": {
                            "enabled": True,
                            "paths": {"project": ".project/logs/edison/audit-project.jsonl"},
                        }
                    },
                },
            }
        },
    )
    reset_edison_caches()

    guards = GuardRegistry()
    guards.register("deny", lambda ctx: False)
    sm = RichStateMachine(
        "task",
        {
            "states": {
                "a": {"allowed_transitions": [{"to": "b", "guard": "deny"}]},
                "b": {"allowed_transitions": []},
            }
        },
        guards,
        ConditionRegistry(),
        ActionRegistry(),
    )

    with pytest.raises(StateTransitionError):
        sm.validate("a", "b", context={})

    log_path = repo / ".project" / "logs" / "edison" / "audit-project.jsonl"
    events = [json.loads(ln) for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert any(e.get("event") == "guard.blocked" and e.get("guard") == "deny" for e in events)

