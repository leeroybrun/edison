#!/usr/bin/env python3
"""
Thin CLI shim to run Claude agent schema validation.

This provides a CLI entrypoint for Claude agent validation, using the
ClaudeSync adapter (formerly ClaudeCodeAdapter). It validates all generated
agents (`.agents/_generated/agents/*.md`). If validation succeeds, it
prints `Schema validation passed` and exits 0; otherwise it surfaces the
error and exits 1.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[4]

    # Import ClaudeSync from the new structure
    from edison.core.adapters import ClaudeSync

    adapter = ClaudeSync(repo_root=repo_root)
    try:
        adapter.sync_agents_to_claude()
    except Exception as exc:  # pragma: no cover - CLI surfacing
        print(f"Schema validation failed: {exc}")
        return 1

    print("Schema validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
