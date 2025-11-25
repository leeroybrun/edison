from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path


def _core_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / "lib" / "sessionlib.py").exists():
            return parent
    raise AssertionError("cannot locate Edison core lib root")


def _ensure_core_on_path() -> None:
    core_root = _core_root()
    if str(core_root) not in sys.path:


def test_sessionlib_has_no_prisma_cli_calls() -> None:
    """
    Edison core library must not shell out directly to prisma.

    Database orchestration (migrations, schema operations) should be
    delegated to packs under `.edison/packs/prisma/` via a generic
    interface. This test enforces that the core sessionlib implementation
    no longer hard-codes `npx prisma ...` invocations.
    """
    _ensure_core_on_path()
    sessionlib = importlib.import_module("lib.sessionlib")  # type: ignore[assignment]

    source = inspect.getsource(sessionlib.create_session_database)  # type: ignore[attr-defined]

    # RED expectation: current implementation still references prisma CLI.
    assert "prisma" not in source, (
        "sessionlib.create_session_database must delegate database migrations "
        "to a pack-level adapter instead of invoking prisma CLI directly"
    )

