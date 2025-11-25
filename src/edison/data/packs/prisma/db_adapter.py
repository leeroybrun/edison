from __future__ import annotations

"""
Prisma-backed session database adapter for Edison.

This module lives under the Prisma pack so that Edison core remains
framework- and tool-agnostic. Core code calls into this adapter via a
generic hook, passing all configuration it needs.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional


def _parse_base_db_url(base_db_url: str) -> Optional[tuple[str, str, str, str]]:
    """
    Parse a PostgreSQL DATABASE_URL into components.

    Returns (user, password, host, database) or None on parse failure.
    """
    m = re.match(r"postgresql://([^:]+):([^@]+)@([^/]+)/(.+)", base_db_url)
    if not m:
        return None
    return m.group(1), m.group(2), m.group(3), m.group(4)


def create_session_database(
    session_id: str,
    *,
    db_prefix: str,
    base_db_url: str,
    repo_dir: Path,
    worktree_config: Dict[str, Any],
) -> Optional[str]:
    """
    Create an isolated PostgreSQL database for a session and run Prisma migrations.

    Returns the session-specific DATABASE_URL, or None on failure.
    """
    parsed = _parse_base_db_url(base_db_url)
    if not parsed:
        return None
    user, password, host, base_db = parsed

    db_name = f"{db_prefix}_{session_id.replace('-', '_')}"

    try:
        subprocess.run(
            ["psql", "-h", host.split(":")[0], "-U", user, "-d", base_db, "-c", f"CREATE DATABASE {db_name};"],
            env={**os.environ, "PGPASSWORD": password},
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    session_db_url = f"postgresql://{user}:{password}@{host}/{db_name}"

    # Run migrations in the new DB (best-effort, errors are non-fatal here)
    try:
        subprocess.run(
            ["npx", "prisma", "migrate", "deploy"],
            env={**os.environ, "DATABASE_URL": session_db_url},
            cwd=repo_dir / "packages" / "db",
            check=True,
            capture_output=True,
            timeout=120,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        # Leave database in place even if migrations fail; caller decides what to do.
        pass

    return session_db_url


def drop_session_database(
    session_id: str,
    *,
    db_prefix: str,
    base_db_url: str,
    repo_dir: Path,
    worktree_config: Dict[str, Any],
) -> None:
    """
    Drop a session-specific PostgreSQL database created by create_session_database.
    """
    parsed = _parse_base_db_url(base_db_url)
    if not parsed:
        return
    user, password, host, base_db = parsed

    db_name = f"{db_prefix}_{session_id.replace('-', '_')}"

    try:
        subprocess.run(
            [
                "psql",
                "-h",
                host.split(":")[0],
                "-U",
                user,
                "-d",
                base_db,
                "-c",
                f"DROP DATABASE IF EXISTS {db_name} WITH (FORCE);",
            ],
            env={**os.environ, "PGPASSWORD": password},
            check=False,
            capture_output=True,
            text=True,
        )
    except Exception:
        # Best-effort cleanup only.
        return

