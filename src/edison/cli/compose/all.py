"""
Edison compose all command.

SUMMARY: Compose all artifacts (agents, validators, constitutions, guidelines, schemas, start prompts)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, add_dry_run_flag, get_repo_root
from edison.core.composition import (
    generate_all_constitutions,
    generate_canonical_entry,
    GuidelineRegistry,
)
from edison.core.composition.generators import (
    AgentRosterGenerator,
    ValidatorRosterGenerator,
    StateMachineGenerator,
)
from edison.core.composition.registries import AgentRegistry, ValidatorRegistry
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.composition.registries.rules import RulesRegistry
from edison.core.composition.registries.schemas import JsonSchemaComposer
from edison.core.config import ConfigManager
from edison.core.utils.paths import get_project_config_dir
from edison.core.adapters.platforms.claude import ClaudeAdapter
from edison.core.adapters.platforms.cursor import CursorAdapter
from edison.core.adapters.platforms.zen.adapter import ZenAdapter
from edison.core.adapters.platforms.codex import CodexAdapter
from edison.core.adapters.components.base import AdapterContext
from edison.core.composition.core.paths import CompositionPathResolver
from edison.data import get_data_path

SUMMARY = "Compose all artifacts (agents, validators, constitutions, guidelines, schemas, documents, start prompts, hooks, settings, commands)"


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
        "--hooks",
        action="store_true",
        help="Only compose hooks",
    )
    parser.add_argument(
        "--settings",
        action="store_true",
        help="Only compose IDE settings",
    )
    parser.add_argument(
        "--commands",
        action="store_true",
        help="Only compose IDE commands",
    )
    parser.add_argument(
        "--rules",
        action="store_true",
        help="Only compose rules",
    )
    parser.add_argument(
        "--schemas",
        action="store_true",
        help="Only compose JSON schemas",
    )
    parser.add_argument(
        "--documents",
        action="store_true",
        help="Only compose document templates (TASK.md, QA.md)",
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
            getattr(args, "hooks", False),
            getattr(args, "settings", False),
            getattr(args, "commands", False),
            getattr(args, "rules", False),
            getattr(args, "schemas", False),
            getattr(args, "documents", False),
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
            agent_gen = AgentRosterGenerator(project_root=repo_root)
            agent_gen.write(output_path)

            validator_gen = ValidatorRosterGenerator(project_root=repo_root)
            validator_gen.write(output_path)

            sm_gen = StateMachineGenerator(project_root=repo_root)
            sm_gen.write(output_path)

            # Generate canonical entry point (AGENTS.md at repo root)
            from edison.core.composition.output import OutputConfigLoader
            output_config = OutputConfigLoader(repo_root=repo_root)
            canonical_path = output_config.get_canonical_entry_path()
            if canonical_path:
                generate_canonical_entry(canonical_path, repo_root=repo_root)
                results["canonical_entry"] = str(canonical_path)

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

        # Compose agents using unified registries
        if compose_all_types or args.agents:
            agent_registry = AgentRegistry(project_root=repo_root)
            agent_results = agent_registry.compose_all(active_packs)

            # Write agents to _generated/agents/
            generated_agents_dir = config_dir / "_generated" / "agents"
            writer = CompositionFileWriter(base_dir=repo_root)

            results["agents"] = {}
            for agent_name, text in agent_results.items():
                output_file = generated_agents_dir / f"{agent_name}.md"
                writer.write_text(output_file, text)
                results["agents"][agent_name] = str(output_file)

        if compose_all_types or args.guidelines:
            # Use GuidelineRegistry for concatenate + dedupe composition
            guideline_registry = GuidelineRegistry(repo_root=repo_root)
            guideline_names = guideline_registry.all_names(active_packs)
            guideline_files = []
            generated_guidelines_dir = config_dir / "_generated" / "guidelines"
            writer = CompositionFileWriter(base_dir=repo_root)

            for name in guideline_names:
                try:
                    result = guideline_registry.compose(name, active_packs)
                    output_file = generated_guidelines_dir / f"{name}.md"
                    writer.write_text(output_file, result.text)
                    guideline_files.append(output_file)
                except Exception:
                    pass  # Skip guidelines that fail to compose

            results["guidelines"] = [str(f) for f in guideline_files]

        if compose_all_types or args.validators:
            validator_registry = ValidatorRegistry(project_root=repo_root)
            validator_results = validator_registry.compose_all(active_packs)

            generated_validators_dir = config_dir / "_generated" / "validators"
            writer = CompositionFileWriter(base_dir=repo_root)

            results["validators"] = {}
            for vid, text in validator_results.items():
                output_file = generated_validators_dir / f"{vid}.md"
                writer.write_text(output_file, text)
                results["validators"][vid] = str(output_file)

        # Compose rules
        if compose_all_types or getattr(args, "rules", False):
            rules_registry = RulesRegistry(project_root=repo_root)
            output_dir = config_dir / "_generated" / "rules"
            output_dir.mkdir(parents=True, exist_ok=True)
            rules_output = output_dir / "registry.json"
            rules_registry.write_output(rules_output, packs=active_packs)
            results["rules"] = str(rules_output)

        # Compose schemas
        if compose_all_types or getattr(args, "schemas", False):
            schema_composer = JsonSchemaComposer(repo_root, active_packs)
            output_dir = config_dir / "_generated" / "schemas"
            output_dir.mkdir(parents=True, exist_ok=True)
            count = schema_composer.write_schemas(output_dir)
            results["schemas"] = {
                "count": count,
                "output_dir": str(output_dir),
            }

        # Compose document templates (TASK.md, QA.md)
        if compose_all_types or getattr(args, "documents", False):
            from edison.core.composition.registries.documents import DocumentTemplateRegistry
            doc_registry = DocumentTemplateRegistry(project_root=repo_root)
            written_docs = doc_registry.write_composed(active_packs)
            results["documents"] = [str(f) for f in written_docs]

        # Compose start prompts via DocumentTemplateRegistry (unified pipeline)
        if compose_all_types or args.start:
            from edison.core.composition.registries.documents import DocumentTemplateRegistry

            doc_registry = DocumentTemplateRegistry(project_root=repo_root)
            written_docs = doc_registry.write_composed(active_packs)
            results["start"] = [str(f) for f in written_docs if f.stem.startswith("START")]

        # Shared adapter context for platform-agnostic components
        resolver = CompositionPathResolver(repo_root)
        writer = CompositionFileWriter(base_dir=repo_root)

        class _AdapterStub:
            def __init__(self, packs: list[str]) -> None:
                self._packs = packs

            def get_active_packs(self) -> list[str]:
                return self._packs

        adapter_stub = _AdapterStub(active_packs)
        adapter_context = AdapterContext(
            project_root=repo_root,
            project_dir=config_dir,
            core_dir=resolver.core_dir,
            bundled_packs_dir=resolver.bundled_packs_dir,
            project_packs_dir=resolver.project_packs_dir,
            cfg_mgr=cfg_mgr,
            config=config,
            writer=writer,
            adapter=adapter_stub,
        )

        # Compose hooks
        if compose_all_types or getattr(args, "hooks", False):
            from edison.core.adapters.components.hooks import HookComposer

            hook_composer = HookComposer(adapter_context)
            hooks = hook_composer.compose_hooks()
            results["hooks"] = {name: str(path) for name, path in hooks.items()}

        # Compose commands
        if compose_all_types or getattr(args, "commands", False):
            from edison.core.adapters.components.commands import CommandComposer

            cmd_composer = CommandComposer(adapter_context)
            commands = cmd_composer.compose_all()
            results["commands"] = {
                platform: {name: str(path) for name, path in cmds.items()}
                for platform, cmds in commands.items()
            }

        # Compose settings (must come after hooks since it references hook paths)
        if compose_all_types or getattr(args, "settings", False):
            from edison.core.adapters.components.settings import SettingsComposer

            settings_composer = SettingsComposer(adapter_context)
            settings_path = settings_composer.write_settings_file()
            results["settings"] = str(settings_path)

        # Compose client files via registry/strategy (unified)
        if compose_all_types:
            from edison.core.composition.registries.documents import DocumentTemplateRegistry

            doc_registry = DocumentTemplateRegistry(project_root=repo_root)
            client_docs = doc_registry.write_composed(active_packs, category="clients")
            if client_docs:
                results["clients"] = {Path(p).stem: str(p) for p in client_docs}

        # Compose CodeRabbit configuration - always runs with compose_all_types
        if compose_all_types:
            from edison.core.adapters import CoderabbitAdapter
            coderabbit_adapter = CoderabbitAdapter(project_root=repo_root)
            coderabbit_path = coderabbit_adapter.write_coderabbit_config()
            results["coderabbit"] = str(coderabbit_path)

        # Sync to clients
        if args.claude:
            adapter = ClaudeAdapter(project_root=repo_root)
            changed = adapter.sync_all()
            results["claude_sync"] = {k: [str(f) for f in v] for k, v in changed.items()}

        if args.cursor:
            adapter = CursorAdapter(project_root=repo_root)
            changed = adapter.sync_all()
            results["cursor_sync"] = {k: [str(f) for f in v] for k, v in changed.items()}

        if args.zen:
            adapter = ZenAdapter(project_root=repo_root)
            changed = adapter.sync_all()
            results["zen_sync"] = {k: [str(f) for f in v] for k, v in changed.items()}

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
