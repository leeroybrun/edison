from __future__ import annotations

from pathlib import Path

from edison.core.config import ConfigManager


def test_continuation_defaults_present_in_config(isolated_project_env: Path) -> None:
    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    continuation = cfg.get("continuation") or {}

    assert continuation.get("enabled") is True
    assert continuation.get("defaultMode") == "soft"

    budgets = continuation.get("budgets") or {}
    assert budgets.get("maxIterations") == 3
    assert budgets.get("cooldownSeconds") == 15
    assert budgets.get("stopOnBlocked") is True


def test_context_window_defaults_present_in_config(isolated_project_env: Path) -> None:
    cfg = ConfigManager(isolated_project_env).load_config(validate=False)
    cw = cfg.get("context_window") or {}

    assert cw.get("enabled") is True

    reminders = (cw.get("reminders") or {})
    assert reminders.get("enabled") is True

    trunc = (cw.get("truncation") or {})
    assert trunc.get("enabled") is False
    assert trunc.get("maxChars") == 20000

