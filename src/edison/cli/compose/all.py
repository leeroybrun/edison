"""
Edison compose all command.

SUMMARY: Compose all artifacts (agents, validators, orchestrator, guidelines)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Compose all artifacts (agents, validators, orchestrator, guidelines)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--agents",
        action="store_true",
        help="Only compose agents",
    )
    parser.add_argument(
        "--validators",
        action="store_true",
        help="Only compose validators",
    )
    parser.add_argument(
        "--orchestrator",
        action="store_true",
        help="Only compose orchestrator manifest and guide",
    )
    parser.add_argument(
        "--guidelines",
        action="store_true",
        help="Only compose guidelines",
    )
    parser.add_argument(
        "--claude",
        action="store_true",
        help="Sync to Claude Code after composing",
    )
    parser.add_argument(
        "--cursor",
        action="store_true",
        help="Sync to Cursor after composing",
    )
    parser.add_argument(
        "--zen",
        action="store_true",
        help="Sync to Zen MCP after composing",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    parser.add_argument(
        "--repo-root",
        type=str,
        help="Override repository root path",
    )


def main(args: argparse.Namespace) -> int:
    """Compose artifacts - delegates to composition engine."""
    from edison.core.composition import CompositionEngine
    from edison.core.paths import resolve_project_root

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()
        engine = CompositionEngine(repo_root)

        results = {}

        # Determine what to compose
        compose_all = not any([args.agents, args.validators, args.orchestrator, args.guidelines])

        if args.dry_run:
            if args.json:
                print(json.dumps({"status": "dry-run", "repo_root": str(repo_root)}))
            else:
                print(f"[dry-run] Would compose artifacts in {repo_root}")
            return 0

        if compose_all or args.guidelines:
            guideline_files = engine.compose_guidelines()
            results["guidelines"] = [str(f) for f in guideline_files]

        if compose_all or args.agents:
            agent_files = engine.compose_agents()
            results["agents"] = [str(f) for f in agent_files]

        if compose_all or args.validators:
            validator_files = engine.compose_validators()
            results["validators"] = [str(f) for f in validator_files]

        if compose_all or args.orchestrator:
            manifest_path, guide_path = engine.compose_orchestrator_manifest()
            results["orchestrator"] = {
                "manifest": str(manifest_path),
                "guide": str(guide_path),
            }

        # Sync to clients
        if args.claude:
            from edison.core.claude_adapter import ClaudeCodeAdapter
            adapter = ClaudeCodeAdapter(repo_root=repo_root)
            adapter.validate_claude_structure()
            changed = adapter.sync_agents_to_claude()
            results["claude_sync"] = [str(f) for f in changed]

        if args.cursor:
            from edison.core.cursor_adapter import CursorAdapter
            adapter = CursorAdapter(repo_root=repo_root)
            changed = adapter.sync()
            results["cursor_sync"] = [str(f) for f in changed]

        if args.zen:
            from edison.core.zen_adapter import ZenAdapter
            adapter = ZenAdapter(repo_root=repo_root)
            changed = adapter.sync_all_prompts()
            results["zen_sync"] = [str(f) for f in changed]

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for key, files in results.items():
                if isinstance(files, list):
                    print(f"{key}: {len(files)} files")
                elif isinstance(files, dict):
                    print(f"{key}: {files}")

        return 0

    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
