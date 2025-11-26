from __future__ import annotations

from typing import List

import yaml

from edison.data import get_data_path


ALLOWED_ROLES = {"orchestrator", "agent", "validator"}


def _load_rules() -> List[dict]:
    """Load bundled core rules registry YAML."""
    path = get_data_path("rules", "registry.yml")
    assert path.exists(), "Bundled rules registry is missing"

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), "Rules registry must be a mapping at top level"

    rules = data.get("rules")
    assert isinstance(rules, list), "'rules' must be a list"

    return rules


def test_all_rules_define_applies_to() -> None:
    """Every rule must declare applies_to for role-based filtering."""
    rules = _load_rules()

    missing = [
        rule.get("id", f"index:{idx}")
        for idx, rule in enumerate(rules)
        if "applies_to" not in rule
    ]

    assert not missing, f"Rules missing applies_to: {missing}"


def test_applies_to_lists_use_valid_roles_and_are_non_empty() -> None:
    """applies_to must be a non-empty list containing only allowed roles."""
    rules = _load_rules()
    invalid: list[str] = []

    for rule in rules:
        rid = rule.get("id", "<missing-id>")
        applies = rule.get("applies_to")

        if not isinstance(applies, list):
            invalid.append(f"{rid}: expected list, got {type(applies).__name__}")
            continue

        if not applies:
            invalid.append(f"{rid}: empty applies_to")

        bad_roles = [role for role in applies if role not in ALLOWED_ROLES]
        if bad_roles:
            invalid.append(f"{rid}: invalid roles {bad_roles}")

    assert not invalid, "Invalid applies_to definitions: " + "; ".join(invalid)
