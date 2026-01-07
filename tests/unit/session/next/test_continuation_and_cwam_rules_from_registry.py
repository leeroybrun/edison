from __future__ import annotations

from edison.core.session.next.rules import get_rules_for_context


def test_context_window_rules_include_cwam_reassurance() -> None:
    rules = get_rules_for_context("context_window")
    rule_ids = [r.get("id") for r in rules]
    assert "RULE.CONTEXT.CWAM_REASSURANCE" in rule_ids


def test_continuation_rules_include_no_idle_rule() -> None:
    rules = get_rules_for_context("continuation")
    rule_ids = [r.get("id") for r in rules]
    assert "RULE.CONTINUATION.NO_IDLE_UNTIL_COMPLETE" in rule_ids

