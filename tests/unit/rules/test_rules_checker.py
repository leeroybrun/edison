from __future__ import annotations

from typing import Any, Dict

from edison.core.rules import RulesEngine
from edison.core.rules.checker import get_rules_for_context_formatted


def test_rules_checker_transition_path_returns_rules() -> None:
    cfg: Dict[str, Any] = {
        "rules": {
            "transitions": {
                "task": {
                    "wip->done": ["RULE.DELEGATION.PRIORITY_CHAIN"],
                }
            }
        }
    }
    engine = RulesEngine(cfg)

    out = get_rules_for_context_formatted(engine=engine, transition="wip->done")
    assert out["count"] == 1
    assert out["rules"][0]["id"] == "RULE.DELEGATION.PRIORITY_CHAIN"




