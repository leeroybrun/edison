"""Tests for safe defaults in session.next continuation payload computation."""

from __future__ import annotations


def test_compute_continuation_handles_missing_budget_values() -> None:
    """compute_next continuation payload should not crash when budgets are missing/None."""
    from edison.core.session.next.compute import _compute_continuation

    result = _compute_continuation(
        session={
            "meta": {
                "continuation": {
                    "maxIterations": None,
                    "cooldownSeconds": None,
                    "stopOnBlocked": None,
                }
            }
        },
        session_id="S001",
        continuation_cfg={
            "enabled": True,
            "defaultMode": "auto",
            "budgets": {
                "maxIterations": None,
                "cooldownSeconds": None,
                "stopOnBlocked": None,
            },
            "templates": {"continuationPrompt": "Continue {sessionId}"},
        },
        context_window_cfg={},
        completion={"isComplete": False},
        actions=[],
        blockers=[],
    )

    budgets = result.get("budgets") or {}
    assert budgets.get("maxIterations") == 0
    assert budgets.get("cooldownSeconds") == 0
    assert budgets.get("stopOnBlocked") is False


def test_safe_int_tolerates_none_default() -> None:
    """_safe_int should not crash if an explicit None default is passed."""
    from edison.core.session.next.compute import _safe_int

    assert _safe_int(None, None) == 0
    assert _safe_int("5", None) == 5


def test_safe_int_tolerates_non_int_default() -> None:
    """_safe_int should not crash if the provided default is not int-coercible."""
    from edison.core.session.next.compute import _safe_int

    assert _safe_int(None, "nope") == 0
    assert _safe_int("5", "nope") == 5
    assert _safe_int("x", "nope") == 0


def test_compute_continuation_filters_none_from_next_blocking_cmd() -> None:
    """Continuation prompt should not include literal 'None' from cmd templates."""
    from edison.core.session.next.compute import _compute_continuation

    result = _compute_continuation(
        session={"meta": {"continuation": {}}},
        session_id="S001",
        continuation_cfg={
            "enabled": True,
            "defaultMode": "auto",
            "budgets": {"maxIterations": 1, "cooldownSeconds": 0, "stopOnBlocked": False},
            "templates": {"continuationPrompt": "Continue {sessionId}"},
        },
        context_window_cfg={},
        completion={"isComplete": False},
        actions=[
            {
                "blocking": True,
                "cmd": ["edison", "task", "status", None, "--status", "done"],
            }
        ],
        blockers=[],
    )

    prompt = str(result.get("prompt") or "")
    assert "Next blocking action" in prompt
    assert "None" not in prompt
