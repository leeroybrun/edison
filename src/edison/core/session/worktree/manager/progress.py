"""Worktree creation progress helpers (CLI-facing, stderr only).

Worktree creation can take tens of seconds in large repos (especially when
setting up meta/shared-state). When invoked via the Edison CLI we want to emit
minimal, safe progress updates without polluting stdout/JSON output.

Enable with:
  EDISON_SESSION_CREATE_PROGRESS=1
"""

from __future__ import annotations

import os
import sys
from time import perf_counter


class WorktreeProgress:
    def __init__(self) -> None:
        self.enabled = os.environ.get("EDISON_SESSION_CREATE_PROGRESS") == "1"
        self._t0 = perf_counter()

    def emit(self, msg: str) -> None:
        if not self.enabled:
            return
        print(f"[edison] {msg}", file=sys.stderr)

    def elapsed(self) -> float:
        return float(perf_counter() - self._t0)


__all__ = ["WorktreeProgress"]

