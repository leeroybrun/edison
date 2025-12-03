"""Context-aware RulesEngine tests (Phase 1B).

These tests exercise the richer RulesEngine API for:
- Loading rules metadata from the in-memory config
- Context-based rule filtering (by type/state/operation)
- Priority-aware ordering of returned rules

They intentionally avoid mocks and rely only on pure Python
data structures so they can run in minimal environments.
"""
from __future__ import annotations

from typing import Dict, Any, List

import pytest

from edison.core.rules import RulesEngine, Rule 
def _engine_with_context_rules(rules_config: Dict[str, Any] | None = None) -> RulesEngine:
    """Helper to construct a RulesEngine with a minimal context-aware config."""
    base_config: Dict[str, Any] = {
        "rules": {
            "enforcement": True,
            "byState": {
                "todo": [
                    {
                        "id": "task-definition-complete",
                        "description": "Task must be well defined before work starts",
                        "enforced": True,
                        "blocking": False,
                        "config": {
                            "contexts": [
                                {
                                    "type": "transition",
                                    "states": ["todo"],
                                    "operations": ["tasks/status"],
                                    "priority": 50,
                                }
                            ]
                        },
                    }
                ],
                "wip": [
                    {
                        "id": "tdd-red-first",
                        "description": "Must have failing test before implementation",
                        "enforced": True,
                        "blocking": False,
                        "config": {
                            "contexts": [
                                {
                                    "type": "guidance",
                                    "states": ["wip"],
                                    "operations": ["session/next"],
                                    "priority": 80,
                                }
                            ]
                        },
                    }
                ],
            },
            "project": [
                {
                    "id": "better-auth-integration",
                    "description": "Authentication must use better-auth patterns",
                    "enforced": True,
                    "blocking": False,
                    "config": {
                        "contexts": [
                            {
                                "type": "guidance",
                                "operations": ["session/next", "delegation/plan"],
                                "priority": 90,
                            }
                        ]
                    },
                }
            ],
        }
    }

    if rules_config is not None:
        # Allow tests to override or extend the base rules config.
        base_config["rules"].update(rules_config)  # type: ignore[arg-type]

    return RulesEngine(base_config)


def _get_ids(rules: List[Rule]) -> List[str]:
    return [r.id for r in rules]


def test_get_rules_for_context_filters_by_type_and_state() -> None:
    """Transition context for todo should surface only todo transition rules."""
    engine = _engine_with_context_rules()

    rules = engine.get_rules_for_context(
        context_type="transition",
        task_state="todo",
        changed_files=None,
        operation="tasks/status",
    )

    assert _get_ids(rules) == ["task-definition-complete"]


def test_get_rules_for_context_ignores_mismatched_context_type() -> None:
    """Validation/guidance requests must not return transition-only rules."""
    engine = _engine_with_context_rules()

    rules = engine.get_rules_for_context(
        context_type="validation",
        task_state="todo",
        changed_files=None,
        operation="tasks/status",
    )

    # No validation-scoped rules configured in the helper config.
    assert rules == []


def test_get_rules_for_context_sorts_by_priority() -> None:
    """RulesEngine should return rules sorted by priority (ascending)."""
    overrides = {
        "project": [
            {
                "id": "high-priority-guidance",
                "description": "High priority guidance rule",
                "enforced": True,
                "blocking": False,
                "config": {
                    "contexts": [
                        {
                            "type": "guidance",
                            "operations": ["session/next"],
                            "priority": 10,
                        }
                    ]
                },
            }
        ]
    }
    engine = _engine_with_context_rules(rules_config=overrides)

    rules = engine.get_rules_for_context(
        context_type="guidance",
        task_state="wip",
        changed_files=None,
        operation="session/next",
    )

    # Expect highest-priority rule first, followed by existing guidance rules.
    assert _get_ids(rules)[0] == "high-priority-guidance"
    assert "tdd-red-first" in _get_ids(rules)

