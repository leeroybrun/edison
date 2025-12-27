from __future__ import annotations

from pathlib import Path

from helpers.io_utils import write_yaml

from edison.core.rules import compose_rules


def test_user_rules_registry_is_applied_before_project(isolated_project_env: Path) -> None:
    root = isolated_project_env

    user_registry = root / ".edison-user" / "rules" / "registry.yml"
    write_yaml(
        user_registry,
        {
            "version": "1.0.0",
            "rules": [
                {
                    "id": "user-rule",
                    "title": "User rule",
                    "blocking": False,
                    "guidance": "From user rules registry.",
                }
            ],
        },
    )

    out = compose_rules(packs=[], project_root=root)
    rules = out["rules"]
    assert "user-rule" in rules
    assert rules["user-rule"]["origins"] == ["user"]
    assert "From user rules registry." in rules["user-rule"]["body"]


def test_user_pack_rules_registry_is_included(isolated_project_env: Path) -> None:
    root = isolated_project_env

    user_pack_registry = root / ".edison-user" / "packs" / "react" / "rules" / "registry.yml"
    write_yaml(
        user_pack_registry,
        {
            "version": "1.0.0",
            "rules": [
                {
                    "id": "react-user-only",
                    "title": "React user pack rule",
                    "blocking": False,
                    "guidance": "From user pack rules registry.",
                }
            ],
        },
    )

    out = compose_rules(packs=["react"], project_root=root)
    rules = out["rules"]
    assert "react-user-only" in rules
    assert rules["react-user-only"]["origins"] == ["pack:react"]
    assert "From user pack rules registry." in rules["react-user-only"]["body"]

