"""
Edison compose all command.

SUMMARY: Compose all artifacts (validators, constitutions, guidelines)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

SUMMARY = "Compose all artifacts (validators, constitutions, guidelines)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--validators",
        action="store_true",
        help="Only compose validators",
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
    """Compose artifacts - delegates to composition registries."""
    from edison.core.composition import (
        generate_all_constitutions,
        generate_available_agents,
        generate_available_validators,
        generate_state_machine_doc,
        GuidelineRegistry,
        LayeredComposer,
    )
    from edison.core.config import ConfigManager
    from edison.core.utils.paths import resolve_project_root
    from edison.core.utils.paths import get_project_config_dir

    try:
        repo_root = Path(args.repo_root) if args.repo_root else resolve_project_root()
        config_dir = get_project_config_dir(repo_root)
        cfg_mgr = ConfigManager(repo_root)
        config = cfg_mgr.load_config(validate=False)
        active_packs = (config.get("packs", {}) or {}).get("active", []) or []

        results = {}

        # Determine what to compose
        compose_all_types = not any([
            args.validators,
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
        if compose_all_types or args.constitutions:
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

        if compose_all_types or args.guidelines:
            # Use GuidelineRegistry for concatenate + dedupe composition
            guideline_registry = GuidelineRegistry(repo_root=repo_root)
            guideline_names = guideline_registry.all_names(active_packs)
            guideline_files = []
            generated_guidelines_dir = config_dir / "_generated" / "guidelines"
            generated_guidelines_dir.mkdir(parents=True, exist_ok=True)
            
            for name in guideline_names:
                try:
                    result = guideline_registry.compose(name, active_packs)
                    output_file = generated_guidelines_dir / f"{name}.md"
                    output_file.write_text(result.text, encoding="utf-8")
                    guideline_files.append(output_file)
                except Exception:
                    pass  # Skip guidelines that fail to compose
            
            results["guidelines"] = [str(f) for f in guideline_files]

        if compose_all_types or args.validators:
            # Use LayeredComposer for section-based validator composition
            validator_composer = LayeredComposer(repo_root=repo_root, content_type="validators")
            validator_results = validator_composer.compose_all(active_packs)
            
            # Write validators to .agents/_generated/validators/
            generated_validators_dir = config_dir / "_generated" / "validators"
            generated_validators_dir.mkdir(parents=True, exist_ok=True)
            
            results["validators"] = {}
            for vid, text in validator_results.items():
                output_file = generated_validators_dir / f"{vid}.md"
                output_file.write_text(text, encoding="utf-8")
                results["validators"][vid] = str(output_file)

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
