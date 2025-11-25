#!/usr/bin/env python3
"""
Thin CLI shim to run Claude agent schema validation.

This mirrors the legacy `claude_adapter.py` entrypoint expected by
migration validation scripts. It loads the core `ClaudeCodeAdapter`
from `.edison/core/lib/claude_adapter.py` and validates all generated
agents (`.agents/_generated/agents/*.md`). If validation succeeds, it
prints `Schema validation passed` and exits 0; otherwise it surfaces the
error and exits 1.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _load_core_adapter(repo_root: Path):
    """Import the main Claude adapter with package context for relative imports."""
    core_pkg_root = repo_root / ".edison" / "core"
    # Import as package `lib.claude_adapter` so its relative imports resolve
    import edison.core.claude_adapter as adapter  # type: ignore

    return adapter


def main() -> int:
    repo_root = Path(__file__).resolve().parents[4]
    module = _load_core_adapter(repo_root)

    adapter = module.ClaudeCodeAdapter(repo_root=repo_root)
    try:
        adapter.sync_agents_to_claude()
    except Exception as exc:  # pragma: no cover - CLI surfacing
        print(f"Schema validation failed: {exc}")
        return 1

    print("Schema validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
