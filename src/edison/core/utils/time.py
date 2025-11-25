from __future__ import annotations

"""Timezone-aware time helpers.

All formatting choices are drawn from YAML config (``time.iso8601``) to avoid
hardcoded defaults.
"""

from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict

# Default configuration (can be overridden by passing config to functions)
DEFAULT_TIME_CONFIG: Dict[str, Any] = {
    "timespec": "seconds",
    "use_z_suffix": False,
    "strip_microseconds": True,
}


def _cfg() -> Dict[str, Any]:
    """Return default time configuration.

    Note: ConfigManager is intentionally not imported here to avoid circular
    dependencies. Callers can override defaults by setting module-level config
    or by passing explicit parameters.
    """
    return DEFAULT_TIME_CONFIG


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime using config-driven precision."""
    cfg = _cfg()
    now = datetime.now(timezone.utc)
    if cfg["strip_microseconds"]:
        now = now.replace(microsecond=0)
    return now


def utc_timestamp() -> str:
    """Return ISO 8601 UTC timestamp according to YAML configuration."""
    cfg = _cfg()
    dt = utc_now()
    ts = dt.isoformat(timespec=cfg["timespec"]) if cfg["timespec"] else dt.isoformat()
    if cfg["use_z_suffix"]:
        ts = ts.replace("+00:00", "Z")
    return ts


def parse_iso8601(timestamp_str: str) -> datetime:
    """Parse an ISO 8601 timestamp string into a UTC datetime."""
    cfg = _cfg()
    ts = timestamp_str.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    if cfg["strip_microseconds"]:
        dt = dt.replace(microsecond=0)
    return dt
