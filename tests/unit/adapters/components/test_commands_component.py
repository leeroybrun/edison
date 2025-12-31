"""Integration tests for CommandComposer (no mocks)."""
from __future__ import annotations

from pathlib import Path

from edison.core.adapters.components.base import AdapterContext
from edison.core.adapters.components.commands import CommandComposer
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.config import ConfigManager


class _AdapterStub:
    def __init__(self, packs: list[str]) -> None:
        self._packs = packs

    def get_active_packs(self) -> list[str]:
        return self._packs


def _build_context(tmp_path: Path, *, packs: list[str] | None = None) -> AdapterContext:
    """Create a minimal AdapterContext backed by temp dirs."""
    project_root = tmp_path
    project_dir = project_root / ".edison"
    user_dir = project_root / ".edison-user"
    core_dir = project_root / "core"
    bundled_packs_dir = project_root / "bundled_packs"
    user_packs_dir = user_dir / "packs"
    project_packs_dir = project_dir / "packs"

    project_dir.mkdir(parents=True, exist_ok=True)
    user_dir.mkdir(parents=True, exist_ok=True)
    core_dir.mkdir(parents=True, exist_ok=True)
    (core_dir / "config").mkdir(exist_ok=True)
    (bundled_packs_dir).mkdir(exist_ok=True)
    user_packs_dir.mkdir(parents=True, exist_ok=True)
    project_packs_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "config").mkdir(exist_ok=True)

    cfg_mgr = ConfigManager(project_root)
    writer = CompositionFileWriter(base_dir=project_root)
    adapter_stub = _AdapterStub(list(packs or []))

    return AdapterContext(
        project_root=project_root,
        project_dir=project_dir,
        user_dir=user_dir,
        core_dir=core_dir,
        bundled_packs_dir=bundled_packs_dir,
        user_packs_dir=user_packs_dir,
        project_packs_dir=project_packs_dir,
        cfg_mgr=cfg_mgr,
        config={},
        writer=writer,
        adapter=adapter_stub,
    )


def _build_context_with_config(tmp_path: Path, *, config: dict) -> AdapterContext:
    ctx = _build_context(tmp_path)
    return AdapterContext(
        project_root=ctx.project_root,
        project_dir=ctx.project_dir,
        user_dir=ctx.user_dir,
        core_dir=ctx.core_dir,
        bundled_packs_dir=ctx.bundled_packs_dir,
        user_packs_dir=ctx.user_packs_dir,
        project_packs_dir=ctx.project_packs_dir,
        cfg_mgr=ctx.cfg_mgr,
        config=config,
        writer=ctx.writer,
        adapter=ctx.adapter,
    )


def test_command_composer_writes_platform_files(tmp_path: Path) -> None:
    """CommandComposer loads markdown definitions and writes them."""
    ctx = _build_context(tmp_path)

    # Provide a minimal core command definition in markdown (new system).
    cmd = ctx.core_dir / "commands" / "session" / "session-next.md"
    cmd.parent.mkdir(parents=True, exist_ok=True)
    cmd.write_text(
        "---\n"
        "id: session-next\n"
        "domain: session\n"
        "command: next\n"
        "short_desc: \"Show next session steps\"\n"
        "cli: \"edison session next <session_id>\"\n"
        "args:\n"
        "  - name: session_id\n"
        "    description: \"Session identifier\"\n"
        "    required: true\n"
        "when_to_use: \"Use when you need next steps\"\n"
        "related_commands: []\n"
        "---\n\n"
        "Hello from markdown definition.\n",
        encoding="utf-8",
    )

    composer = CommandComposer(ctx)
    definitions = composer.compose()

    ids = {d.id for d in definitions}
    assert "session-next" in ids

    # Compose for claude platform
    results = composer.compose_for_platform("claude", definitions)

    assert "session-next" in results

    # Verify files are actually written
    for cmd_id, out_path in results.items():
        assert out_path.exists(), f"Command file should exist: {out_path}"
        content = out_path.read_text(encoding="utf-8")
        assert len(content) > 0, f"Command file should have content: {cmd_id}"


def test_command_composer_pack_definitions_do_not_replace_core(tmp_path: Path) -> None:
    """Active packs may add commands without removing core commands."""
    ctx = _build_context(tmp_path, packs=["example-pack"])

    core_cmd = ctx.core_dir / "commands" / "session" / "session-next.md"
    core_cmd.parent.mkdir(parents=True, exist_ok=True)
    core_cmd.write_text(
        "---\n"
        "id: session-next\n"
        "domain: session\n"
        "command: next\n"
        "short_desc: \"Show next session steps\"\n"
        "cli: \"edison session next <session_id>\"\n"
        "args: []\n"
        "when_to_use: \"\"\n"
        "related_commands: []\n"
        "---\n\n"
        "Core body.\n",
        encoding="utf-8",
    )

    pack_cmd = ctx.bundled_packs_dir / "example-pack" / "commands" / "task" / "task-pack.md"
    pack_cmd.parent.mkdir(parents=True, exist_ok=True)
    pack_cmd.write_text(
        "---\n"
        "id: task-pack\n"
        "domain: task\n"
        "command: pack\n"
        "short_desc: \"Pack-added command\"\n"
        "cli: \"edison task list\"\n"
        "args: []\n"
        "when_to_use: \"\"\n"
        "related_commands: []\n"
        "---\n\n"
        "Pack body.\n",
        encoding="utf-8",
    )

    composer = CommandComposer(ctx)
    defs = composer.load_definitions()
    ids = {d.id for d in defs}

    assert "session-next" in ids
    assert "task-pack" in ids


def test_command_composer_ignores_legacy_yaml_definitions(tmp_path: Path) -> None:
    """Legacy YAML-based command definitions are not loaded (NO LEGACY)."""
    import yaml

    ctx = _build_context(tmp_path)

    # New system: markdown definition.
    cmd = ctx.core_dir / "commands" / "rules" / "rules-current.md"
    cmd.parent.mkdir(parents=True, exist_ok=True)
    cmd.write_text(
        "---\n"
        "id: rules-current\n"
        "domain: rules\n"
        "command: current\n"
        "short_desc: \"Show current rules\"\n"
        "cli: \"edison rules current\"\n"
        "args: []\n"
        "when_to_use: \"\"\n"
        "related_commands: []\n"
        "---\n\n"
        "Rules body.\n",
        encoding="utf-8",
    )

    # Old system: project config tries to inject commands.definitions.
    config_dir = ctx.project_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "commands.yaml").write_text(
        yaml.safe_dump(
            {
                "commands": {
                    "definitions": [
                        {
                            "id": "legacy-yaml-command",
                            "domain": "task",
                            "command": "legacy",
                            "short_desc": "Should not load",
                            "full_desc": "Legacy body",
                            "cli": "edison task list",
                            "args": [],
                            "when_to_use": "",
                            "related_commands": [],
                        }
                    ]
                }
            }
        ),
        encoding="utf-8",
    )

    composer = CommandComposer(ctx)
    ids = {d.id for d in composer.load_definitions()}
    assert "rules-current" in ids
    assert "legacy-yaml-command" not in ids


def test_command_composer_prunes_stale_files(tmp_path: Path) -> None:
    """Stale Edison-generated command files are always pruned."""
    ctx = _build_context_with_config(tmp_path, config={"commands": {"platform_config": {"claude": {"prefix": "edison."}}}})

    cmd = ctx.core_dir / "commands" / "session" / "session-status.md"
    cmd.parent.mkdir(parents=True, exist_ok=True)
    cmd.write_text(
        "---\n"
        "id: session-status\n"
        "domain: session\n"
        "command: status\n"
        "short_desc: \"Show session status\"\n"
        "cli: \"edison session status\"\n"
        "args: []\n"
        "when_to_use: \"\"\n"
        "related_commands: []\n"
        "---\n\n"
        "Status body.\n",
        encoding="utf-8",
    )

    composer = CommandComposer(ctx)
    defs = composer.compose()

    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    stale = out_dir / "edison.stale.md"
    stale.write_text(
        "---\n"
        "description: \"stale\"\n"
        "edison-generated: true\n"
        "---\n\n"
        "# edison.stale\n",
        encoding="utf-8",
    )
    assert stale.exists()

    composer.compose_for_platform("claude", defs, output_dir_override=out_dir)
    assert not stale.exists(), "Expected stale file to be removed"


def test_command_composer_prunes_unprefixed_legacy_generated_files(tmp_path: Path) -> None:
    """When a prefix is configured, old unprefixed generated files should be removed (NO LEGACY)."""
    ctx = _build_context_with_config(tmp_path, config={"commands": {"platform_config": {"claude": {"prefix": "edison."}}}})

    cmd = ctx.core_dir / "commands" / "session" / "session-status.md"
    cmd.parent.mkdir(parents=True, exist_ok=True)
    cmd.write_text(
        "---\n"
        "id: session-status\n"
        "domain: session\n"
        "command: status\n"
        "short_desc: \"Show session status\"\n"
        "cli: \"edison session status\"\n"
        "args: []\n"
        "when_to_use: \"\"\n"
        "related_commands: []\n"
        "---\n\n"
        "Status body.\n",
        encoding="utf-8",
    )

    composer = CommandComposer(ctx)
    defs = composer.compose()

    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    legacy = out_dir / "session-status.md"
    legacy.write_text(
        "---\n"
        "description: \"legacy\"\n"
        "edison-generated: true\n"
        "---\n\n"
        "# session-status\n",
        encoding="utf-8",
    )
    assert legacy.exists()

    composer.compose_for_platform("claude", defs, output_dir_override=out_dir)
    assert not legacy.exists(), "Expected unprefixed legacy file to be removed"
