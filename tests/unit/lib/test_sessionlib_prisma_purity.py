from __future__ import annotations

import inspect

from edison.core.session import database as session_database


def test_session_database_has_no_prisma_cli_calls() -> None:
    """
    Edison core library must not shell out directly to prisma.

    Database orchestration (migrations, schema operations) should be
    delegated to packs under `.edison/packs/prisma/` via a generic
    interface. This test enforces that the core session.database module
    no longer hard-codes `npx prisma ...` invocations.
    """
    source = inspect.getsource(session_database.create_session_database)

    # RED expectation: current implementation still references prisma CLI.
    assert "prisma" not in source, (
        "session.database.create_session_database must delegate database migrations "
        "to a pack-level adapter instead of invoking prisma CLI directly"
    )
