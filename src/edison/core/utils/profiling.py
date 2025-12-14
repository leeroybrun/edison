"""Lightweight hierarchical profiler for Edison.

Goals:
- Zero overhead when disabled (no-op span context manager).
- Works across the whole codebase without invasive plumbing (ContextVar-based).
- Produces both human-readable summaries and machine-readable JSON.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from time import perf_counter
from typing import Any, Dict, Iterator, List, Optional


_ACTIVE_PROFILER: ContextVar["Profiler | None"] = ContextVar("_ACTIVE_PROFILER", default=None)


@dataclass(frozen=True)
class SpanRecord:
    name: str
    start_s: float
    end_s: float
    duration_ms: float
    depth: int
    meta: Dict[str, Any]


class Profiler:
    """Collects spans in a hierarchical fashion."""

    def __init__(self) -> None:
        self._spans: List[SpanRecord] = []
        self._depth: int = 0

    @property
    def spans(self) -> List[SpanRecord]:
        return list(self._spans)

    @contextmanager
    def span(self, name: str, **meta: Any) -> Iterator[None]:
        start = perf_counter()
        depth = self._depth
        self._depth += 1
        try:
            yield
        finally:
            self._depth -= 1
            end = perf_counter()
            self._spans.append(
                SpanRecord(
                    name=name,
                    start_s=start,
                    end_s=end,
                    duration_ms=(end - start) * 1000.0,
                    depth=depth,
                    meta=dict(meta),
                )
            )

    def summary_ms(self) -> Dict[str, float]:
        totals: Dict[str, float] = {}
        for s in self._spans:
            totals[s.name] = totals.get(s.name, 0.0) + s.duration_ms
        return totals

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spans": [asdict(s) for s in self._spans],
            "summary_ms": self.summary_ms(),
        }


@contextmanager
def enable_profiler(profiler: Profiler) -> Iterator[None]:
    token = _ACTIVE_PROFILER.set(profiler)
    try:
        yield
    finally:
        _ACTIVE_PROFILER.reset(token)


@contextmanager
def span(name: str, **meta: Any) -> Iterator[None]:
    profiler = _ACTIVE_PROFILER.get()
    if profiler is None:
        yield
        return
    with profiler.span(name, **meta):
        yield


def get_active_profiler() -> Optional[Profiler]:
    return _ACTIVE_PROFILER.get()


__all__ = ["Profiler", "SpanRecord", "enable_profiler", "span", "get_active_profiler"]


