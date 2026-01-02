"""Worktree environment helpers."""

from __future__ import annotations

import re as _re
from pathlib import Path


def update_worktree_env(worktree_path: Path, database_url: str) -> None:
    """Update .env file in worktree with session database URL."""
    env_path = worktree_path / ".env"
    if env_path.exists():
        env_content = env_path.read_text()
    else:
        example_path = worktree_path / ".env.example"
        env_content = example_path.read_text() if example_path.exists() else ""

    if _re.search(r"^DATABASE_URL=", env_content, _re.MULTILINE):
        env_content = _re.sub(
            r"^DATABASE_URL=.*$",
            f'DATABASE_URL="{database_url}"',
            env_content,
            flags=_re.MULTILINE,
        )
    else:
        env_content += f'\nDATABASE_URL="{database_url}"\n'
    env_path.write_text(env_content)


__all__ = ["update_worktree_env"]
