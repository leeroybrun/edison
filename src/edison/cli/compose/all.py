"""
Edison compose all command.

SUMMARY: Compose all artifacts using config-driven composition from composition.yaml

This command uses ComposableTypesManager and AdapterLoader for unified, config-driven
composition. All content types and adapters are defined in composition.yaml.

NO SPECIAL HANDLING - everything goes through the configuration system.
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, add_dry_run_flag, get_repo_root
from edison.core.composition.registries._types_manager import ComposableTypesManager
from edison.core.config import ConfigManager
from edison.core.config.domains.composition import CompositionConfig
from edison.core.adapters.loader import AdapterLoader
from edison.core.utils.paths import get_project_config_dir
from edison.core.utils.profiling import Profiler, enable_profiler, span

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
        ("--artifacts", "Only compose artifact templates (Task/QA/Report scaffolds)"),
        ("--documents", "DEPRECATED: alias for --artifacts"),
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
        "--pal",
        action="store_true",
        help="Sync to Pal MCP after composing",
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
    parser.add_argument(
        "--no-adapters",
        action="store_true",
        help="Do not run any platform adapters (overrides the default full-compose behavior)",
    )

    # Output hygiene: prevent stale `_generated/**` files by rebuilding atomically.
    parser.add_argument(
        "--atomic-generated",
        dest="atomic_generated",
        action="store_true",
        help="Compose into a temporary `_generated` directory and swap into place on success (prevents stale files). Only valid for full compose.",
    )
    parser.add_argument(
        "--clean-generated",
        dest="clean_generated",
        action="store_true",
        help="Delete the entire `_generated` directory before composing (unsafe on failure). Only valid for full compose.",
    )

    # Profiling / diagnosis
    parser.add_argument(
        "--profile",
        action="store_true",
        help="Emit profiling information for config loading, composition, template processing, and writes.",
    )
    
    add_dry_run_flag(parser)
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Compose artifacts - fully config-driven composition."""
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        from contextlib import nullcontext

        profiling_enabled = bool(getattr(args, "profile", False))
        profiler = Profiler() if profiling_enabled else None

        with (enable_profiler(profiler) if profiler else nullcontext()):
            with span("compose.all.total"):
                # Repo root + config
                with span("compose.repo_root"):
                    repo_root = get_repo_root(args)

                with span("compose.config.load"):
                    cfg_mgr = ConfigManager(repo_root)
                    config = cfg_mgr.load_config(validate=False)
                    active_packs = (config.get("packs", {}) or {}).get("active", []) or []

                # Initialize managers
                with span("compose.init.managers"):
                    types_manager = ComposableTypesManager(project_root=repo_root)
                    adapter_loader = AdapterLoader(project_root=repo_root)

                # Enabled types + request selection
                enabled_types = {t.name for t in types_manager.get_enabled_types()}

                # Back-compat aliases for renamed content-types.
                # Keep old CLI flags working even when the underlying config key changes.
                if bool(getattr(args, "documents", False)) and not bool(getattr(args, "artifacts", False)):
                    setattr(args, "artifacts", True)

                requested_types: set[str] = set()
                for type_cfg in types_manager.get_all_types():
                    attr_name = type_cfg.cli_flag.replace("-", "_")
                    if getattr(args, attr_name, False):
                        requested_types.add(type_cfg.name)

                compose_all = len(requested_types) == 0

                atomic_generated = bool(getattr(args, "atomic_generated", False))
                clean_generated = bool(getattr(args, "clean_generated", False))

                # Default to safe behavior for full compose: avoid stale `_generated/**`.
                if compose_all and not atomic_generated and not clean_generated:
                    atomic_generated = True

                if (atomic_generated or clean_generated) and not compose_all:
                    raise ValueError(
                        "--atomic-generated/--clean-generated require a full compose (no per-type flags)."
                    )

                if args.dry_run:
                    types_to_compose = list(enabled_types) if compose_all else list(requested_types)
                    payload: Dict[str, Any] = {
                        "status": "dry-run",
                        "repo_root": str(repo_root),
                        "types_to_compose": types_to_compose,
                        "enabled_adapters": adapter_loader.get_enabled_adapter_names(),
                        "atomic_generated": atomic_generated,
                        "clean_generated": clean_generated,
                        "profile": profiling_enabled,
                    }
                    if args.json:
                        formatter.json_output(payload)
                    else:
                        formatter.text(f"[dry-run] Would compose artifacts in {repo_root}")
                        formatter.text(f"[dry-run] Types: {', '.join(types_to_compose)}")
                    return 0

                # Output hygiene: prepare `_generated`
                project_dir = get_project_config_dir(repo_root, create=True)
                generated_dir = project_dir / "_generated"
                tmp_generated_dir: Path | None = None
                # `_generated` may be a symlink in worktree setups (shared generated artifacts).
                # Atomic rebuild must operate on the real target directory, not the symlink path,
                # otherwise shutil.rmtree fails and we can accidentally replace the symlink.
                try:
                    generated_real = generated_dir.resolve() if generated_dir.is_symlink() else generated_dir
                except Exception:
                    generated_real = generated_dir

                def _map_generated_path(p: Path) -> Path:
                    if tmp_generated_dir is None:
                        return p
                    try:
                        if p.is_relative_to(generated_dir):
                            return tmp_generated_dir / p.relative_to(generated_dir)
                    except Exception:
                        p_str = str(p)
                        gen_str = str(generated_dir)
                        if p_str.startswith(gen_str + "/") or p_str == gen_str:
                            rel = Path(p_str[len(gen_str) :].lstrip("/"))
                            return tmp_generated_dir / rel
                    return p

                if atomic_generated:
                    stamp = int(time.time() * 1000)
                    tmp_generated_dir = generated_real.parent / f"_generated.__tmp__{stamp}"
                    if tmp_generated_dir.exists():
                        shutil.rmtree(tmp_generated_dir)
                    tmp_generated_dir.mkdir(parents=True, exist_ok=True)
                elif clean_generated and generated_real.exists():
                    shutil.rmtree(generated_real)

                results: Dict[str, Any] = {}

                try:
                    # Compose/write enabled types
                    for type_cfg in types_manager.get_enabled_types():
                        if not compose_all and type_cfg.name not in requested_types:
                            continue
                        if type_cfg.name in results:
                            continue
                        with span("compose.type.write", type=type_cfg.name):
                            written = types_manager.write_type(
                                type_cfg.name,
                                active_packs,
                                path_mapper=_map_generated_path if atomic_generated else None,
                            )
                        if written:
                            results[type_cfg.name] = [str(f) for f in written]

                    # Swap `_generated` atomically only after successful writes
                    if atomic_generated and tmp_generated_dir is not None:
                        with span("compose.generated.swap"):
                            if generated_real.exists():
                                shutil.rmtree(generated_real)
                            tmp_generated_dir.replace(generated_real)
                            tmp_generated_dir = None
                finally:
                    if tmp_generated_dir is not None and tmp_generated_dir.exists():
                        shutil.rmtree(tmp_generated_dir)

                # Platform adapters
                adapters_to_run: List[str] = []
                explicit_all = bool(getattr(args, "all_adapters", False))
                no_adapters = bool(getattr(args, "no_adapters", False))
                explicit_any = False
                for adapter_name in adapter_loader.get_all_adapter_names():
                    if getattr(args, adapter_name, False):
                        explicit_any = True
                        break

                if no_adapters and (explicit_all or explicit_any):
                    raise ValueError("--no-adapters cannot be combined with adapter selection flags.")

                # Full compose defaults to also running enabled adapters unless explicitly suppressed
                # by selecting specific types or requesting specific adapters.
                if no_adapters:
                    adapters_to_run = []
                elif compose_all and not explicit_all and not explicit_any:
                    adapters_to_run = adapter_loader.get_enabled_adapter_names()
                elif explicit_all:
                    adapters_to_run = adapter_loader.get_enabled_adapter_names()
                else:
                    for adapter_name in adapter_loader.get_all_adapter_names():
                        if getattr(args, adapter_name, False):
                            adapters_to_run.append(adapter_name)

                for adapter_name in adapters_to_run:
                    with span("compose.adapter.sync", adapter=adapter_name):
                        adapter_result = adapter_loader.run_adapter(adapter_name)
                    if adapter_result and "error" not in adapter_result:
                        results[f"{adapter_name}_sync"] = {
                            k: [str(f) for f in v] if isinstance(v, list) else v
                            for k, v in adapter_result.items()
                        }
                    elif adapter_result and "error" in adapter_result:
                        results[f"{adapter_name}_sync"] = {"error": adapter_result["error"]}

                # Output
                if args.json:
                    payload: Dict[str, Any] = dict(results)
                    if profiler is not None:
                        payload["profiling"] = profiler.to_dict()
                    formatter.json_output(payload)
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
                    if profiler is not None:
                        totals = profiler.summary_ms()
                        top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:15]
                        formatter.text("\nProfiling (top spans):")
                        for name, ms in top:
                            formatter.text(f"- {name}: {ms:.1f}ms")

                return 0

    except Exception as e:
        formatter.error(e, error_code="compose_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args()
    sys.exit(main(args))
