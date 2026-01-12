"""Integration tests for HookComposer (no mocks)."""
from __future__ import annotations

from pathlib import Path

from edison.core.adapters.components.base import AdapterContext
from edison.core.adapters.components.hooks import HookComposer
from edison.core.composition.output.writer import CompositionFileWriter
from edison.core.config import ConfigManager


class _AdapterStub:
    def __init__(self, packs: list[str]) -> None:
        self._packs = packs

    def get_active_packs(self) -> list[str]:
        return self._packs


def _build_context(tmp_path: Path, config: dict) -> AdapterContext:
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
    (core_dir / "templates" / "hooks").mkdir(parents=True, exist_ok=True)
    (project_dir / "templates" / "hooks").mkdir(parents=True, exist_ok=True)
    bundled_packs_dir.mkdir(exist_ok=True)
    user_packs_dir.mkdir(parents=True, exist_ok=True)
    project_packs_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "config").mkdir(exist_ok=True)

    cfg_mgr = ConfigManager(project_root)
    writer = CompositionFileWriter(base_dir=project_root)
    adapter_stub = _AdapterStub([])

    ctx = AdapterContext(
        project_root=project_root,
        project_dir=project_dir,
        user_dir=user_dir,
        core_dir=core_dir,
        bundled_packs_dir=bundled_packs_dir,
        user_packs_dir=user_packs_dir,
        project_packs_dir=project_packs_dir,
        cfg_mgr=cfg_mgr,
        config=config,
        writer=writer,
        adapter=adapter_stub,
    )
    # Minimal bundled hooks config to avoid auto-generated defaults
    bundled_hooks = core_dir / "config" / "hooks.yaml"
    if not bundled_hooks.exists():
        bundled_hooks.write_text("hooks:\n  definitions: {}\n", encoding="utf-8")

    return ctx


def test_hook_composer_renders_core_hook(tmp_path: Path) -> None:
    ctx = _build_context(
        tmp_path,
        config={"hooks": {"enabled": True, "platforms": ["claude"]}},
    )

    # Project hook definition (overlays bundled defaults)
    hooks_yaml = ctx.project_dir / "config" / "hooks.yml"
    hooks_yaml.write_text(
        """
hooks:
  definitions:
    sample:
      type: PreToolUse
      description: run sample hook
      template: sample.hook
""",
        encoding="utf-8",
    )

    # Hook template placed in project templates
    template = ctx.project_dir / "templates" / "hooks" / "sample.hook"
    template.write_text("#!/bin/bash\necho sample\n", encoding="utf-8")

    composer = HookComposer(ctx)
    results = composer.compose_hooks()

    # At least one hook is generated and includes our template content
    assert results
    found = any(path.read_text(encoding="utf-8").find("sample") != -1 for path in results.values())
    assert found


def test_core_hook_templates_emit_audit_events(tmp_path: Path) -> None:
    """Bundled core hooks should emit structured audit events (when enabled).

    This validates we don't rely on ad-hoc per-hook log files (e.g. `.edison/logs/*`)
    and instead funnel hook execution into the unified audit log pipeline.
    """
    ctx = _build_context(
        tmp_path,
        config={"hooks": {"enabled": True, "platforms": ["claude"]}},
    )

    composer = HookComposer(ctx)
    scripts = composer.compose_hooks()

    # A few high-signal hooks should always include the audit event helper.
    expected = {
        "compaction-reminder": "hook.compaction-reminder",
        "session-cleanup": "hook.session-cleanup",
        "session-init": "hook.session-init",
        "commit-guard": "hook.commit-guard",
    }

    for hook_id, event_prefix in expected.items():
        assert hook_id in scripts
        content = scripts[hook_id].read_text(encoding="utf-8")
        assert "edison audit event" in content
        assert event_prefix in content


def test_core_hooks_include_worktree_enforcement(tmp_path: Path) -> None:
    ctx = _build_context(
        tmp_path,
        config={"hooks": {"enabled": True, "platforms": ["claude"]}},
    )

    composer = HookComposer(ctx)
    scripts = composer.compose_hooks()

    assert "enforce-worktree" in scripts
    content = scripts["enforce-worktree"].read_text(encoding="utf-8")
    assert "WORKTREE ENFORCEMENT" in content
    assert "edison session detect" in content


def test_settings_json_hook_commands_use_claude_project_dir(tmp_path: Path) -> None:
    """settings.json hook command paths must be worktree-independent."""
    ctx = _build_context(
        tmp_path,
        config={"hooks": {"enabled": True, "platforms": ["claude"]}},
    )

    composer = HookComposer(ctx)
    composer.compose_hooks()
    hooks = composer.generate_settings_json_hooks_section()

    # At least one hook should be emitted and use the stable $CLAUDE_PROJECT_DIR form.
    commands: list[str] = []
    for entries in hooks.values():
        for entry in entries:
            for hook in entry.get("hooks") or []:
                cmd = hook.get("command")
                if isinstance(cmd, str):
                    commands.append(cmd)
    assert commands
    assert any(cmd.startswith("$CLAUDE_PROJECT_DIR/.claude/hooks/") for cmd in commands)
