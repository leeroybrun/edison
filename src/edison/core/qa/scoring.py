"""QA scoring utilities (history + regression detection)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Tuple

from . import store


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def track_validation_score(
    session_id: str,
    validator_name: str,
    scores: Dict[str, Any],
    overall_score: float,
) -> None:
    """Append a validation score record to the session's history JSONL file."""
    entry = {
        "timestamp": _now_iso(),
        "session_id": session_id,
        "validator": validator_name,
        "scores": scores,
        "overall_score": float(overall_score),
    }
    store.append_jsonl(store.score_history_file(session_id), entry)


def get_score_history(session_id: str) -> List[Dict[str, Any]]:
    """Return score history for ``session_id`` ordered by timestamp."""
    entries = list(store.read_jsonl(store.score_history_file(session_id)))
    entries.sort(key=lambda x: x.get("timestamp", ""))  # ISO-8601 sortable
    return entries


def compute_dimension_scores(dimensions: Dict[str, int], results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute weighted per-dimension and overall scores.

    Args:
        dimensions: Mapping of dimension → weight (must sum to 100).
        results: Mapping of dimension → raw score (0–10 scale).

    Returns:
        dict with ``perDimension`` and ``overallScore`` keys.
    """
    if not dimensions:
        raise ValueError("dimensions mapping must not be empty")
    total_weight = sum(int(v) for v in dimensions.values())
    if total_weight <= 0:
        raise ValueError("dimension weights must sum to a positive value")

    per_dimension: Dict[str, float] = {}
    weighted_sum = 0.0

    for name, weight in dimensions.items():
        w = float(weight)
        raw = float(results.get(name, 0.0))
        per_dimension[name] = raw
        weighted_sum += raw * w

    overall = weighted_sum / float(total_weight)
    return {"perDimension": per_dimension, "overallScore": overall}


def _regression_details(previous: float, current: float, threshold: float) -> Tuple[bool, Dict[str, Any]]:
    delta = current - previous
    if delta < -abs(threshold):
        severity = "HIGH" if delta <= -2.0 else "MEDIUM"
        return True, {
            "previous_score": previous,
            "current_score": current,
            "delta": delta,
            "regression_severity": severity,
            "suggestion": (
                "Investigate recent changes; review score history and "
                "address failing dimensions."
            ),
        }
    return False, {"status": "no_regression", "delta": delta}


def detect_regression(session_id: str, current_score: float, threshold: float = 0.5) -> Tuple[bool, Dict[str, Any]]:
    """
    Detect whether the new score is a regression compared to the last run.

    Uses score history tracked via :func:`track_validation_score`.
    """
    hist = get_score_history(session_id)
    if not hist:
        return False, {"status": "no_regression", "delta": 0}
    previous = float(hist[-1].get("overall_score", 0.0))
    return _regression_details(previous, float(current_score), float(threshold))


def plot_score_trend(session_id: str) -> str:
    """Build a simple ASCII plot of overall score trend for a session."""
    hist = get_score_history(session_id)
    if len(hist) < 2:
        return "Insufficient data for trend analysis"
    lines = [f"\nScore Trend for {session_id}", "=" * 50]
    for h in hist:
        ts = str(h.get("timestamp", ""))
        score = float(h.get("overall_score", 0.0))
        bar = "█" * int(round(score))
        lines.append(f"{ts[:19]} | {bar} {score:.1f}/10")
    lines.append("=" * 50)
    return "\n".join(lines)


__all__ = [
    "track_validation_score",
    "get_score_history",
    "compute_dimension_scores",
    "detect_regression",
    "plot_score_trend",
]
