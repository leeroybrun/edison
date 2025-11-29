from __future__ import annotations

"""Timezone-aware time helpers.

All formatting choices are drawn from YAML config (``time.iso8601``) to avoid
hardcoded defaults.
"""

from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Dict


def _cfg() -> Dict[str, Any]:
    """Return time configuration from YAML without fallbacks.

    Raises:
        RuntimeError: If config cannot be loaded or time.iso8601 section is missing
    """
    try:
        from ..config import ConfigManager
        from .paths import PathResolver

        repo_root = PathResolver.resolve_project_root()
        cfg_manager = ConfigManager(repo_root)
        full_config = cfg_manager.load_config(validate=False)

        if "time" not in full_config:
            raise RuntimeError(
                "time configuration section is missing. "
                "Add 'time' section to your YAML config."
            )

        if "iso8601" not in full_config["time"]:
            raise RuntimeError(
                "time.iso8601 configuration section is missing. "
                "Add 'time.iso8601' section to your YAML config."
            )

        config = full_config["time"]["iso8601"]

        # Validate required fields
        required_fields = ["timespec", "use_z_suffix", "strip_microseconds"]
        missing_fields = [f for f in required_fields if f not in config]
        if missing_fields:
            raise RuntimeError(
                f"time.iso8601 configuration missing required fields: {missing_fields}"
            )

        return config
    except Exception as e:
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(
            f"Failed to load time configuration: {e}"
        ) from e


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
