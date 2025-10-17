from __future__ import annotations

import asyncio

from app.jobs.handlers import handle_aggregate_scores
from app.jobs.registry import registry


def test_registry_returns_registered_handler() -> None:
    handler = registry.get("aggregate_scores")
    assert handler is handle_aggregate_scores

    import asyncio

    asyncio.run(handler({}))


def test_registry_missing_handler() -> None:
    try:
        registry.get("unknown-job")
    except KeyError as exc:
        assert "unknown-job" in str(exc)
    else:  # pragma: no cover - defensive
        raise AssertionError("Expected KeyError")
