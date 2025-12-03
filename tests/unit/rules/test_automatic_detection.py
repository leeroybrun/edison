"""Automatic rule detection tests (Phase 1B).

These tests exercise RulesEngine.get_rules_for_context using file pattern
matching and operation scoping. They pass explicit changed_files paths
to avoid relying on git history while still validating the matching logic.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, List

from edison.core.rules import RulesEngine, Rule 
def _engine_with_detection_rules() -> RulesEngine:
    cfg: Dict[str, Any] = {
        "rules": {
            "enforcement": True,
            "project": [
                {
                    "id": "database-migrations",
                    "description": "Database changes must follow migration rules",
                    "enforced": True,
                    "blocking": True,
                    "config": {
                        "contexts": [
                            {
                                "type": "validation",
                                "filePatterns": ["**/*.prisma", "prisma/**/*"],
                                "operations": ["session/next"],
                                "priority": 10,
                            }
                        ]
                    },
                },
                {
                    "id": "api-contracts",
                    "description": "API changes must respect contract rules",
                    "enforced": True,
                    "blocking": True,
                    "config": {
                        "contexts": [
                            {
                                "type": "validation",
                                "filePatterns": ["app/api/**/*", "**/route.ts"],
                                "operations": ["session/next"],
                                "priority": 20,
                            }
                        ]
                    },
                },
                {
                    "id": "delegation-priority",
                    "description": "Delegation must follow priority chain",
                    "enforced": True,
                    "blocking": False,
                    "config": {
                        "contexts": [
                            {
                                "type": "delegation",
                                "filePatterns": ["**/*.ts", "**/*.tsx"],
                                "operations": ["delegation/plan"],
                                "priority": 5,
                            }
                        ]
                    },
                },
            ]
        }
    }
    return RulesEngine(cfg)


def _get_ids(rules: List[Rule]) -> List[str]:
    return [r.id for r in rules]


def test_file_patterns_trigger_validation_rules_for_changed_files() -> None:
    """Changed files matching patterns should trigger validation rules."""
    engine = _engine_with_detection_rules()
    changed_files = [
        Path("prisma/schema.prisma"),
        Path("app/api/users/route.ts"),
    ]

    rules = engine.get_rules_for_context(
        context_type="validation",
        task_state="wip",
        changed_files=changed_files,
        operation="session/next",
    )

    ids = _get_ids(rules)
    assert "database-migrations" in ids
    assert "api-contracts" in ids
    # Database rule has higher priority (10 < 20) and should be first.
    assert ids[0] == "database-migrations"


def test_operation_type_filters_delegation_rules() -> None:
    """Delegation context should return only delegation-scoped rules."""
    engine = _engine_with_detection_rules()
    changed_files = [Path("app/example-app/page.tsx")]

    rules = engine.get_rules_for_context(
        context_type="delegation",
        task_state=None,
        changed_files=changed_files,
        operation="delegation/plan",
    )

    ids = _get_ids(rules)
    assert ids == ["delegation-priority"]

