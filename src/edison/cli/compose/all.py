"""
Edison compose all command.

SUMMARY: Compose all artifacts (agents, validators, constitutions, guidelines, start prompts)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, add_dry_run_flag, get_repo_root
from edison.core.composition import (
    generate_all_constitutions,
    generate_available_agents,
    generate_available_validators,
    generate_state_machine_doc,
    GuidelineRegistry,
    LayeredComposer,
)
from edison.core.config import ConfigManager
from edison.core.utils.paths import get_project_config_dir
from edison.core.adapters import ClaudeSync, CursorSync, ZenSync
from edison.data import get_data_path

SUMMARY = "Compose all artifacts (agents, validators, constitutions, guidelines, start prompts)"


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
        "--start",
        action="store_true",
        help="Only compose start prompts",
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
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Compose artifacts - delegates to composition registries."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        config_dir = get_project_config_dir(repo_root)
        cfg_mgr = ConfigManager(repo_root)
        config = cfg_mgr.load_config(validate=False)
        active_packs = (config.get("packs", {}) or {}).get("active", []) or []

        results = {}

        # Determine what to compose
        compose_all_types = not any([
            args.agents,
            args.validators,
            args.guidelines,
            args.constitutions,
            args.start,
        ])

        if args.dry_run:
            if args.json:
                formatter.json_output({"status": "dry-run", "repo_root": str(repo_root)})
            else:
                formatter.text(f"[dry-run] Would compose artifacts in {repo_root}")
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

        # Compose agents using LayeredComposer
        if compose_all_types or args.agents:
            agent_composer = LayeredComposer(repo_root=repo_root, content_type="agents")
            agent_results = agent_composer.compose_all(active_packs)
            
            # Write agents to _generated/agents/
            generated_agents_dir = config_dir / "_generated" / "agents"
            generated_agents_dir.mkdir(parents=True, exist_ok=True)
            
            results["agents"] = {}
            for agent_name, text in agent_results.items():
                output_file = generated_agents_dir / f"{agent_name}.md"
                output_file.write_text(text, encoding="utf-8")
                results["agents"][agent_name] = str(output_file)

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
                    # Preserve subfolder structure from source
                    subfolder = guideline_registry.get_subfolder(name, active_packs)
                    if subfolder:
                        output_dir = generated_guidelines_dir / subfolder
                        output_dir.mkdir(parents=True, exist_ok=True)
                    else:
                        output_dir = generated_guidelines_dir
                    output_file = output_dir / f"{name}.md"
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

        # Compose start prompts
        if compose_all_types or args.start:
            generated_start_dir = config_dir / "_generated" / "start"
            generated_start_dir.mkdir(parents=True, exist_ok=True)
            
            # Get core start files from edison.data/start/
            core_start_dir = get_data_path("start")
            project_start_dir = config_dir / "start"
            project_overlays_dir = project_start_dir / "overlays"
            
            start_files = []
            if core_start_dir.exists():
                for start_file in core_start_dir.glob("*.md"):
                    name = start_file.stem
                    content = start_file.read_text(encoding="utf-8")
                    
                    # Check for project overlay
                    project_overlay = project_overlays_dir / f"{name}.md"
                    if project_overlay.exists():
                        overlay_content = project_overlay.read_text(encoding="utf-8")
                        content = content + "\n\n" + overlay_content
                    
                    # Check for project-level new start file (completely replaces core)
                    project_new = project_start_dir / f"{name}.md"
                    if project_new.exists() and not project_overlay.exists():
                        content = project_new.read_text(encoding="utf-8")
                    
                    output_file = generated_start_dir / f"{name}.md"
                    output_file.write_text(content, encoding="utf-8")
                    start_files.append(output_file)
            
            # Also check for project-only start files (new start prompts defined at project level)
            if project_start_dir.exists():
                for start_file in project_start_dir.glob("*.md"):
                    name = start_file.stem
                    # Skip if already processed from core
                    if (generated_start_dir / f"{name}.md").exists():
                        continue
                    content = start_file.read_text(encoding="utf-8")
                    output_file = generated_start_dir / f"{name}.md"
                    output_file.write_text(content, encoding="utf-8")
                    start_files.append(output_file)
            
            results["start"] = [str(f) for f in start_files]

        # Sync to clients
        if args.claude:
            adapter = ClaudeSync(repo_root=repo_root)
            adapter.validate_claude_structure()
            changed = adapter.sync_agents_to_claude()
            results["claude_sync"] = [str(f) for f in changed]

        if args.cursor:
            adapter = CursorSync(repo_root=repo_root)
            changed = adapter.sync()
            results["cursor_sync"] = [str(f) for f in changed]

        if args.zen:
            adapter = ZenSync(repo_root=repo_root)
            changed = adapter.sync_all_prompts()
            results["zen_sync"] = [str(f) for f in changed]

        if args.json:
            formatter.json_output(results)
        else:
            for key, files in results.items():
                if isinstance(files, list):
                    formatter.text(f"{key}: {len(files)} files")
                elif isinstance(files, dict):
                    formatter.text(f"{key}: {files}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="compose_error")
        return 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
