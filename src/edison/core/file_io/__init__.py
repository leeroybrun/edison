"""
IO utilities package for Edison core.

Hosts higher-level helpers built on top of :mod:`lib.io_utils` to
provide a cleaner abstraction surface.
"""
from __future__ import annotations

from . import utils as _utils  # noqa: F401

__all__ = ["utils"]

utils = _utils

