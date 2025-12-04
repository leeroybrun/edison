"""
Edison compose all command.

SUMMARY: Compose all artifacts using config-driven composition from composition.yaml

This command uses ComposableTypesManager and AdapterLoader for unified, config-driven
composition. All content types and adapters are defined in composition.yaml.

NO SPECIAL HANDLING - everything goes through the configuration system.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, add_dry_run_flag, get_repo_root
from edison.core.composition.registries._types_manager import ComposableTypesManager
from edison.core.config import ConfigManager
from edison.core.config.domains.composition import CompositionConfig
from edison.core.adapters.loader import AdapterLoader
from edison.core.utils.paths import get_project_config_dir

SUMMARY = "Compose all artifacts (config-driven composition from composition.yaml)"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments.
    
    Dynamically registers flags for composable types and adapters from config.
    """
    # Note: We add common flags statically but they're also read from config
    # This ensures help text is available even before config is loaded
    for flag, help_text in [
        ("--agents", "Only compose agents"),
        ("--validators", "Only compose validators"),
        ("--guidelines", "Only compose guidelines"),
        ("--constitutions", "Only compose constitutions"),
        ("--start", "Only compose start prompts"),
        ("--cursor-rules", "Only compose Cursor IDE rules (.mdc files)"),
        ("--roots", "Only compose root entry files (AGENTS.md, CLAUDE.md)"),
        ("--schemas", "Only compose JSON schemas"),
        ("--documents", "Only compose document templates"),
    ]:
        parser.add_argument(flag, action="store_true", help=help_text)
    
    # Platform adapter sync options
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
        "--coderabbit",
        action="store_true",
        help="Sync CodeRabbit configuration",
    )
    parser.add_argument(
        "--all-adapters",
        action="store_true",
        help="Run all enabled platform adapters after composing",
    )
    
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Compose artifacts - fully config-driven composition."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        config_dir = get_project_config_dir(repo_root)
        cfg_mgr = ConfigManager(repo_root)
        config = cfg_mgr.load_config(validate=False)
        active_packs = (config.get("packs", {}) or {}).get("active", []) or []

        results: Dict[str, Any] = {}
        
        # Initialize managers
        types_manager = ComposableTypesManager(project_root=repo_root)
        adapter_loader = AdapterLoader(project_root=repo_root)

        # Get all enabled composable types from config
        enabled_types = {t.name for t in types_manager.get_enabled_types()}
        
        # Determine which types were explicitly requested
        requested_types: set[str] = set()
        
        # Check config-driven flags (convert hyphen to underscore for attribute names)
        for type_cfg in types_manager.get_all_types():
            attr_name = type_cfg.cli_flag.replace("-", "_")
            if getattr(args, attr_name, False):
                requested_types.add(type_cfg.name)
        
        # If no types explicitly requested, compose all enabled types
        compose_all = len(requested_types) == 0

        if args.dry_run:
            types_to_compose = list(enabled_types) if compose_all else list(requested_types)
            if args.json:
                formatter.json_output({
                    "status": "dry-run",
                    "repo_root": str(repo_root),
                    "types_to_compose": types_to_compose,
                    "enabled_adapters": adapter_loader.get_enabled_adapter_names(),
                })
            else:
                formatter.text(f"[dry-run] Would compose artifacts in {repo_root}")
                formatter.text(f"[dry-run] Types: {', '.join(types_to_compose)}")
            return 0

        # =====================================================================
        # COMPOSE ALL CONTENT TYPES (config-driven)
        # =====================================================================
        for type_cfg in types_manager.get_enabled_types():
            if not compose_all and type_cfg.name not in requested_types:
                continue
            
            # Skip if already composed (e.g., dependencies)
            if type_cfg.name in results:
                continue
            
            written = types_manager.write_type(type_cfg.name, active_packs)
            if written:
                results[type_cfg.name] = [str(f) for f in written]

        # =====================================================================
        # PLATFORM ADAPTER SYNC (via AdapterLoader)
        # =====================================================================
        # Platform adapters handle their own hooks/settings/commands internally
        adapters_to_run: List[str] = []
        
        if args.all_adapters:
            adapters_to_run = adapter_loader.get_enabled_adapter_names()
        else:
            # Check individual adapter flags
            for adapter_name in adapter_loader.get_all_adapter_names():
                if getattr(args, adapter_name, False):
                    adapters_to_run.append(adapter_name)
        
        for adapter_name in adapters_to_run:
            adapter_result = adapter_loader.run_adapter(adapter_name)
            if adapter_result and "error" not in adapter_result:
                results[f"{adapter_name}_sync"] = {
                    k: [str(f) for f in v] if isinstance(v, list) else v
                    for k, v in adapter_result.items()
                }
            elif adapter_result and "error" in adapter_result:
                results[f"{adapter_name}_sync"] = {"error": adapter_result["error"]}

        # =====================================================================
        # OUTPUT
        # =====================================================================
        if args.json:
            formatter.json_output(results)
        else:
            for key, files in results.items():
                if isinstance(files, list):
                    formatter.text(f"{key}: {len(files)} files")
                elif isinstance(files, dict):
                    if "error" in files:
                        formatter.text(f"{key}: ERROR - {files['error']}")
                    else:
                        count = len(files) if files else 0
                        formatter.text(f"{key}: {count} items")
                else:
                    formatter.text(f"{key}: {files}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="compose_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
