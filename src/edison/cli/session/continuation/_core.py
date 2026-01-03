from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _safe_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


@dataclass(frozen=True)
class ContinuationView:
    defaults: dict[str, Any]
    override: dict[str, Any] | None
    effective: dict[str, Any]


def compute_continuation_view(*, continuation_cfg: dict[str, Any], meta_continuation: dict[str, Any] | None) -> ContinuationView:
    cfg = _safe_dict(continuation_cfg)
    budgets = _safe_dict(cfg.get("budgets"))

    defaults = {
        "enabled": bool(cfg.get("enabled", True)),
        "mode": str(cfg.get("defaultMode") or "soft"),
        "budgets": {
            "maxIterations": int(budgets.get("maxIterations") or 3),
            "cooldownSeconds": int(budgets.get("cooldownSeconds") or 15),
            "stopOnBlocked": bool(budgets.get("stopOnBlocked", True)),
        },
    }

    ov = _safe_dict(meta_continuation) if meta_continuation is not None else {}
    override = dict(ov) if ov else None

    effective = {
        "enabled": bool(ov.get("enabled")) if "enabled" in ov else defaults["enabled"],
        "mode": str(ov.get("mode") or defaults["mode"]),
        "budgets": {
            "maxIterations": int(ov.get("maxIterations")) if "maxIterations" in ov else defaults["budgets"]["maxIterations"],
            "cooldownSeconds": int(ov.get("cooldownSeconds")) if "cooldownSeconds" in ov else defaults["budgets"]["cooldownSeconds"],
            "stopOnBlocked": bool(ov.get("stopOnBlocked")) if "stopOnBlocked" in ov else defaults["budgets"]["stopOnBlocked"],
        },
    }
    if not effective["enabled"]:
        effective["mode"] = "off"

    return ContinuationView(defaults=defaults, override=override, effective=effective)


__all__ = ["ContinuationView", "compute_continuation_view"]

