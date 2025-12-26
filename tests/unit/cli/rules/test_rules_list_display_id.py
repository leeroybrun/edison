from __future__ import annotations

from edison.cli.rules.list import _display_rule_id


def test_display_rule_id_does_not_duplicate_prefix() -> None:
    assert _display_rule_id("RULE.DELEGATION.PRIORITY_CHAIN") == "RULE.DELEGATION.PRIORITY_CHAIN"
    assert _display_rule_id("rule.validation.first") == "RULE.VALIDATION.FIRST"









