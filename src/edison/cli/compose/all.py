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
        help="Only compose orchestrator manifest",
    )
    parser.add_argument(
        "--constitutions",
        action="store_true",
        help="Only compose constitutions (and supporting rosters)",
    )
    parser.add_argument(
        "--guidelines",
        action="store_true",
        help="Only compose guidelines",
    )
    parser.add_argument(
        "--platforms",
        type=str,
        help="Target platforms (comma-separated: claude,cursor,zen)",
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
    from edison.core.composition.constitution import generate_all_constitutions
    from edison.core.composition.rosters import (
        generate_available_agents,
        generate_available_validators,
    )
    from edison.core.composition.state_machine import generate_state_machine_doc
    from edison.core.config import ConfigManager
    from edison.core.paths import resolve_project_root
    from edison.core.paths.project import get_project_config_dir

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()
        config_dir = get_project_config_dir(repo_root)
        engine = CompositionEngine(repo_root=repo_root)

        results = {}

        # Determine what to compose
        compose_all = not any([
            args.agents,
            args.validators,
            args.orchestrator,
            args.guidelines,
            args.constitutions,
        ])

        if args.dry_run:
            if args.json:
                print(json.dumps({"status": "dry-run", "repo_root": str(repo_root)}))
            else:
                print(f"[dry-run] Would compose artifacts in {repo_root}")
            return 0

        # Generate rosters + constitutions (constitutions depend on rosters)
        if compose_all or args.constitutions:
            cfg_mgr = ConfigManager(repo_root)
            output_path = config_dir / "_generated"

            # Generate rosters first so constitutions can reference them
            generate_available_agents(output_path / "AVAILABLE_AGENTS.md", repo_root=repo_root)
            generate_available_validators(output_path / "AVAILABLE_VALIDATORS.md", repo_root=repo_root)
            generate_state_machine_doc(output_path / "STATE_MACHINE.md", repo_root=repo_root)

            # Generate constitutions for all roles
            generate_all_constitutions(cfg_mgr, output_path)
            constitutions_dir = output_path / "constitutions"
            if constitutions_dir.exists():
                constitution_files = list(constitutions_dir.glob("*.md"))
                results["constitutions"] = [str(f) for f in constitution_files]
            results["rosters"] = [
                str(output_path / "AVAILABLE_AGENTS.md"),
                str(output_path / "AVAILABLE_VALIDATORS.md"),
            ]
            results["state_machine"] = str(output_path / "STATE_MACHINE.md")

        if compose_all or args.guidelines:
            guideline_files = engine.compose_guidelines()
            results["guidelines"] = [str(f) for f in guideline_files]

        if compose_all or args.agents:
            agent_files = engine.compose_agents()
            results["agents"] = [str(f) for f in agent_files]

        if compose_all or args.validators:
            validator_results = engine.compose_validators()
            results["validators"] = {
                vid: str(result.cache_path)
                for vid, result in validator_results.items()
            }
            # Also write validators to .agents/_generated/validators/
            generated_validators_dir = config_dir / "_generated" / "validators"
            generated_validators_dir.mkdir(parents=True, exist_ok=True)
            for vid, result in validator_results.items():
                output_file = generated_validators_dir / f"{vid}.md"
                output_file.write_text(result.text, encoding="utf-8")

        if compose_all or args.orchestrator:
            output_dir = config_dir / "_generated"
            output_dir.mkdir(parents=True, exist_ok=True)
            orchestrator_result = engine.compose_orchestrator_manifest(output_dir)
            results["orchestrator"] = {
                k: str(v) for k, v in orchestrator_result.items()
            }

        # Sync to clients
        if args.claude:
            from edison.core.adapters import ClaudeSync
            adapter = ClaudeSync(repo_root=repo_root)
            adapter.validate_claude_structure()
            changed = adapter.sync_agents_to_claude()
            results["claude_sync"] = [str(f) for f in changed]

        if args.cursor:
            from edison.core.adapters import CursorSync
            adapter = CursorSync(repo_root=repo_root)
            changed = adapter.sync()
            results["cursor_sync"] = [str(f) for f in changed]

        if args.zen:
            from edison.core.adapters import ZenSync
            adapter = ZenSync(repo_root=repo_root)
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

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
