from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edison.core.utils.config import safe_dict as _safe_dict


@dataclass(frozen=True)
class ContinuationView:
    defaults: dict[str, Any]
    override: dict[str, Any] | None
    effective: dict[str, Any]


def _coerce_int(value: Any, *, field: str, origin: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Invalid continuation {origin} value for {field}: {value!r}") from e


def compute_continuation_view(*, continuation_cfg: dict[str, Any], meta_continuation: dict[str, Any] | None) -> ContinuationView:
    """Compute continuation view from config and session overrides.

    All default values come from continuation.yaml config - no hardcoded fallbacks.
    Config provides: enabled, defaultMode, budgets.{maxIterations,cooldownSeconds,stopOnBlocked}
    """
    cfg = _safe_dict(continuation_cfg)
    budgets = _safe_dict(cfg.get("budgets"))

    for key in ("enabled", "defaultMode"):
        if key not in cfg or cfg.get(key) is None:
            raise ValueError(f"Missing required continuation config key: {key}")

    for key in ("maxIterations", "cooldownSeconds", "stopOnBlocked"):
        if key not in budgets or budgets.get(key) is None:
            raise ValueError(f"Missing required continuation budget key: {key}")

    defaults = {
        "enabled": bool(cfg["enabled"]),
        "mode": str(cfg["defaultMode"]),
        "budgets": {
            "maxIterations": _coerce_int(budgets["maxIterations"], field="maxIterations", origin="config"),
            "cooldownSeconds": _coerce_int(
                budgets["cooldownSeconds"], field="cooldownSeconds", origin="config"
            ),
            "stopOnBlocked": bool(budgets["stopOnBlocked"]),
        },
    }

    ov = _safe_dict(meta_continuation) if meta_continuation is not None else {}
    override = dict(ov) if ov else None

    enabled_override = ov.get("enabled") if "enabled" in ov else None
    mode_override = ov.get("mode") if "mode" in ov else None
    max_iterations_override = ov.get("maxIterations") if "maxIterations" in ov else None
    cooldown_seconds_override = ov.get("cooldownSeconds") if "cooldownSeconds" in ov else None
    stop_on_blocked_override = ov.get("stopOnBlocked") if "stopOnBlocked" in ov else None

    effective = {
        "enabled": bool(enabled_override) if enabled_override is not None else defaults["enabled"],
        "mode": str(mode_override) if mode_override is not None else defaults["mode"],
        "budgets": {
            "maxIterations": _coerce_int(
                max_iterations_override, field="maxIterations", origin="override"
            )
            if max_iterations_override is not None
            else defaults["budgets"]["maxIterations"],
            "cooldownSeconds": _coerce_int(
                cooldown_seconds_override, field="cooldownSeconds", origin="override"
            )
            if cooldown_seconds_override is not None
            else defaults["budgets"]["cooldownSeconds"],
            "stopOnBlocked": bool(stop_on_blocked_override)
            if stop_on_blocked_override is not None
            else defaults["budgets"]["stopOnBlocked"],
        },
    }
    if not effective["enabled"]:
        effective["mode"] = "off"

    return ContinuationView(defaults=defaults, override=override, effective=effective)


__all__ = ["ContinuationView", "compute_continuation_view"]
