"""
IO utilities package for Edison core.

Hosts higher-level helpers built on top of :mod:`lib.io_utils` to
provide a cleaner abstraction surface.
"""
from __future__ import annotations

from . import utils as _utils  # noqa: F401

__all__ = ["utils", "utc_timestamp"]

utils = _utils


# Lazy import for utc_timestamp to avoid circular import issues
def __getattr__(name: str):
    if name == "utc_timestamp":
        from edison.core.task.io import utc_timestamp
        return utc_timestamp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

