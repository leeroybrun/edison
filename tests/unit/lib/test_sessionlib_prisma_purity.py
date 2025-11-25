from __future__ import annotations

import inspect
from pathlib import Path

from edison.core import sessionlib  # type: ignore


def test_sessionlib_has_no_prisma_cli_calls() -> None:
    """
    Edison core library must not shell out directly to prisma.

    Database orchestration (migrations, schema operations) should be
    delegated to packs under `.edison/packs/prisma/` via a generic
    interface. This test enforces that the core sessionlib implementation
    no longer hard-codes `npx prisma ...` invocations.
    """
    source = inspect.getsource(sessionlib.create_session_database)  # type: ignore[attr-defined]

    # RED expectation: current implementation still references prisma CLI.
    assert "prisma" not in source, (
        "sessionlib.create_session_database must delegate database migrations "
        "to a pack-level adapter instead of invoking prisma CLI directly"
    )
