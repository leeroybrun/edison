from __future__ import annotations
from helpers.io_utils import write_yaml

import sys
from pathlib import Path
from typing import Dict, Any

import pytest

from tests.helpers.paths import get_repo_root

ROOT = get_repo_root()
core_path = ROOT / ".edison" / "core"
from edison.core.composition.ide.hooks import HookComposer, HookDefinition  # type: ignore  # noqa: E402

ALLOWED_TYPES = [
    "PreToolUse",
    "PostToolUse",
    "UserPromptSubmit",
    "SessionStart",
    "SessionEnd",
    "PreCompact",
    "Stop",
    "SubagentStop",
]

def _sample_hook_def(
    id: str,
    *,
    type: str = "PreToolUse",
    hook_type: str = "command",
    enabled: bool = True,
    blocking: bool = False,
    matcher: str | None = None,
    description: str = "Test hook",
    template: str = "hook.sh.template",
    config: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "type": type,
        "hook_type": hook_type,
        "enabled": enabled,
        "blocking": blocking,
        "description": description,
        "template": template,
        "config": config or {},
    }
    if matcher is not None:
        data["matcher"] = matcher
    return {id: data}

def test_hook_definition_dataclass() -> None:
    hook = HookDefinition(
        id="remind",
        type="PreToolUse",
        hook_type="command",
        enabled=True,
        blocking=False,
        matcher="Write|Edit",
        description="Remind about TDD",
        template="remind.sh.template",
        config={"only_for_states": ["wip"]},
    )

    assert hook.id == "remind"
    assert hook.matcher == "Write|Edit"
    assert hook.config["only_for_states"] == ["wip"]

def test_load_core_definitions(tmp_path: Path) -> None:
    # Write to project override location (.edison/config/hooks.yml)
    # HookComposer loads bundled core hooks, then pack hooks, then project overrides
    project_override = _sample_hook_def("project-hook", description="From project")
    write_yaml(tmp_path / ".edison/config/hooks.yml", {"hooks": {"definitions": project_override}})

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    defs = composer.load_definitions()

    # Project override hook should be present
    assert "project-hook" in defs
    loaded = defs["project-hook"]
    assert loaded.description == "From project"
    assert loaded.config == {}
    # Bundled core hooks should also be present
    assert "remind-tdd" in defs or "inject-session-context" in defs

def test_merge_pack_definitions(tmp_path: Path) -> None:
    # HookComposer uses bundled core hooks, but pack definitions override them
    # Test that pack hooks override a bundled hook (remind-tdd exists in bundled core)
    pack_override = _sample_hook_def(
        "remind-tdd",  # Override bundled hook
        description="pack override",
        config={"nested": {"b": 2}, "list": ["=b"]},
    )
    pack_only = _sample_hook_def("pack-only", description="pack only")

    # Write pack hooks config
    write_yaml(
        tmp_path / ".edison/packs/pack1/config/hooks.yml",
        {"hooks": {"definitions": {**pack_override, **pack_only}}},
    )
    # Write packs.active config so PacksConfig can read it
    write_yaml(tmp_path / ".edison/config/edison.yaml", {"packs": {"active": ["pack1"]}})

    composer = HookComposer(config={}, repo_root=tmp_path)
    defs = composer.load_definitions()

    # Pack-only hook should be present
    assert "pack-only" in defs
    # remind-tdd should have pack override applied (merged with bundled)
    shared = defs["remind-tdd"]
    assert shared.description == "pack override"
    assert shared.config.get("nested", {}).get("b") == 2

def test_apply_project_overrides(tmp_path: Path) -> None:
    # Use a bundled hook name (remind-tdd) and override it at pack and project levels
    pack_override = _sample_hook_def("remind-tdd", description="pack", matcher="Write")
    project_override = _sample_hook_def("remind-tdd", description="project", matcher="Edit")

    write_yaml(
        tmp_path / ".edison/packs/pack1/config/hooks.yml",
        {"hooks": {"definitions": pack_override}},
    )
    write_yaml(tmp_path / ".edison/config/hooks.yml", {"hooks": {"definitions": project_override}})
    # Write packs.active config so PacksConfig can read it
    write_yaml(tmp_path / ".edison/config/edison.yaml", {"packs": {"active": ["pack1"]}})

    composer = HookComposer(config={}, repo_root=tmp_path)
    defs = composer.load_definitions()
    shared = defs["remind-tdd"]

    # Project override wins
    assert shared.description == "project"
    assert shared.matcher == "Edit"

def test_filter_enabled_only(tmp_path: Path) -> None:
    # Disable ALL bundled hooks and add custom ones
    # Get all bundled hook names and disable them
    bundled_hooks = [
        "inject-session-context", "inject-task-rules", "remind-tdd",
        "remind-state-machine", "commit-guard", "prevent-prod-edits",
        "check-tests", "auto-format", "session-init", "session-cleanup",
        "compaction-reminder", "stop-validate"
    ]
    custom_defs: Dict[str, Any] = {}
    for hook_name in bundled_hooks:
        custom_defs.update(_sample_hook_def(hook_name, enabled=False, template=f"{hook_name}.sh.template"))

    # Add our test hooks
    custom_defs.update(_sample_hook_def("custom-enabled", enabled=True, template="tmpl1.sh"))
    custom_defs.update(_sample_hook_def("custom-disabled", enabled=False, template="tmpl2.sh"))

    write_yaml(tmp_path / ".edison/config/hooks.yml", {"hooks": {"definitions": custom_defs}})

    # Create templates for our custom hooks in the project templates dir
    tmpl_dir = tmp_path / ".edison/templates/hooks"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "tmpl1.sh").write_text("#!/bin/bash\necho enabled\n", encoding="utf-8")
    (tmpl_dir / "tmpl2.sh").write_text("#!/bin/bash\necho disabled\n", encoding="utf-8")

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    scripts = composer.compose_hooks()

    # custom-enabled should be in scripts
    assert "custom-enabled" in scripts
    assert scripts["custom-enabled"].exists()
    # custom-disabled should NOT be in scripts (disabled)
    assert "custom-disabled" not in scripts
    # Bundled hooks should all be disabled
    for hook_name in bundled_hooks:
        assert hook_name not in scripts

def test_render_hook_from_template(tmp_path: Path) -> None:
    # Use project templates dir (.edison/templates/hooks) which has higher priority
    tmpl_dir = tmp_path / ".edison/templates/hooks"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "simple.sh.template").write_text(
        "ID={{ id }} TYPE={{ type }} DESC={{ description }} CFG={{ config.flag }}", encoding="utf-8"
    )

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    hook_def = HookDefinition(
        id="simple",
        type="UserPromptSubmit",
        hook_type="prompt",
        enabled=True,
        blocking=False,
        matcher=None,
        description="Simple hook",
        template="simple.sh.template",
        config={"flag": "on"},
    )

    rendered = composer.render_hook(hook_def)

    assert "ID=simple" in rendered.replace(" ", "")
    assert "CFG=on" in rendered

def test_compose_all_hooks(tmp_path: Path) -> None:
    # Disable ALL bundled hooks
    bundled_hooks = [
        "inject-session-context", "inject-task-rules", "remind-tdd",
        "remind-state-machine", "commit-guard", "prevent-prod-edits",
        "check-tests", "auto-format", "session-init", "session-cleanup",
        "compaction-reminder", "stop-validate"
    ]
    custom_defs: Dict[str, Any] = {}
    for hook_name in bundled_hooks:
        custom_defs.update(_sample_hook_def(hook_name, enabled=False, template=f"{hook_name}.sh.template"))

    # Use project templates dir
    tmpl_dir = tmp_path / ".edison/templates/hooks"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "compose.sh.template").write_text("#!/usr/bin/env bash\necho {{ id }}", encoding="utf-8")

    # Add our custom hook via project override
    custom_defs.update(_sample_hook_def("compose", template="compose.sh.template", description="Compose me"))
    write_yaml(tmp_path / ".edison/config/hooks.yml", {"hooks": {"definitions": custom_defs}})

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    scripts = composer.compose_hooks()

    # Our custom hook should be composed
    assert "compose" in scripts
    out_path = scripts["compose"]
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8").strip().endswith("compose")
    assert out_path.parent == tmp_path / ".claude" / "hooks"
    assert out_path.stat().st_mode & 0o111, "script should be executable"

def test_generate_settings_json_section(tmp_path: Path) -> None:
    # Disable ALL bundled hooks
    bundled_hooks = [
        "inject-session-context", "inject-task-rules", "remind-tdd",
        "remind-state-machine", "commit-guard", "prevent-prod-edits",
        "check-tests", "auto-format", "session-init", "session-cleanup",
        "compaction-reminder", "stop-validate"
    ]
    custom_defs: Dict[str, Any] = {}
    for hook_name in bundled_hooks:
        custom_defs.update(_sample_hook_def(hook_name, enabled=False, template=f"{hook_name}.sh.template"))

    # Use project templates dir
    tmpl_dir = tmp_path / ".edison/templates/hooks"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "a.sh.template").write_text("#!/bin/bash\necho A", encoding="utf-8")
    (tmpl_dir / "b.sh.template").write_text("#!/bin/bash\necho B", encoding="utf-8")

    custom_defs.update(_sample_hook_def(
        "custom-remind",  # Use unique name to avoid bundled hook conflicts
        type="PreToolUse",
        hook_type="command",
        matcher="Write|Edit",
        template="a.sh.template",
    ))
    custom_defs.update(_sample_hook_def(
        "custom-inject",  # Use unique name
        type="UserPromptSubmit",
        hook_type="prompt",
        matcher="*",
        template="b.sh.template",
    ))

    write_yaml(tmp_path / ".edison/config/hooks.yml", {"hooks": {"definitions": custom_defs}})

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    composer.compose_hooks()  # ensure scripts exist
    hooks_section = composer.generate_settings_json_hooks_section()

    # hooks_section is now the direct mapping of event types (no double nesting)
    # This gets assigned to settings["hooks"] to produce the correct Claude Code structure
    assert "PreToolUse" in hooks_section
    # Find our custom-remind hook in PreToolUse hooks
    pre_hooks = [h for h in hooks_section["PreToolUse"] if h.get("matcher") == "Write|Edit"]
    assert len(pre_hooks) > 0
    found_remind = False
    for pre in pre_hooks:
        for h in pre.get("hooks", []):
            if h.get("command", "").endswith(".claude/hooks/custom-remind.sh"):
                found_remind = True
                assert h["type"] == "command"
                break
    assert found_remind, "custom-remind hook not found in settings"

    # Find our custom-inject hook
    assert "UserPromptSubmit" in hooks_section
    found_inject = False
    for entry in hooks_section["UserPromptSubmit"]:
        for h in entry.get("hooks", []):
            # According to Edison's hook design (lines 120-125 in hooks.py),
            # shell scripts always use type: "command", not type: "prompt"
            # The hook_type: "prompt" was for stdout injection, but Claude Code
            # handles that automatically for UserPromptSubmit command hooks
            if h.get("command", "").endswith(".claude/hooks/custom-inject.sh"):
                found_inject = True
                assert h["type"] == "command"
                break
    assert found_inject, f"custom-inject hook not found in settings. UserPromptSubmit section: {hooks_section.get('UserPromptSubmit', [])}"

def test_hook_types_validation(tmp_path: Path) -> None:
    defs: Dict[str, Dict[str, Any]] = {}
    for idx, hook_type in enumerate(ALLOWED_TYPES):
        defs.update(
            _sample_hook_def(
                f"hook-{idx}",
                type=hook_type,
                template="t.sh.template",
            )
        )
    write_yaml(tmp_path / ".edison/config/hooks.yml", {"hooks": {"definitions": defs}})
    tmpl_dir = tmp_path / ".edison/templates/hooks"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "t.sh.template").write_text("#!/bin/bash\n", encoding="utf-8")

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    loaded = composer.load_definitions()

    # All our custom hooks should be present (bundled hooks are also present)
    for i in range(len(ALLOWED_TYPES)):
        assert f"hook-{i}" in loaded, f"hook-{i} not found in loaded definitions"

    bad_defs = _sample_hook_def("bad", type="UnknownType")
    write_yaml(tmp_path / ".edison/config/hooks.yml", {"hooks": {"definitions": bad_defs}})
    with pytest.raises(ValueError):
        HookComposer(config={"hooks": {}}, repo_root=tmp_path).load_definitions()

def test_blocking_only_for_pretooluse(tmp_path: Path) -> None:
    defs = _sample_hook_def(
        "post-blocking",
        type="PostToolUse",
        blocking=True,
        template="t.sh.template",
    )
    write_yaml(tmp_path / ".edison/config/hooks.yml", {"hooks": {"definitions": defs}})
    tmpl_dir = tmp_path / ".edison/templates/hooks"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "t.sh.template").write_text("#!/bin/bash\n", encoding="utf-8")

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    with pytest.raises(ValueError):
        composer.load_definitions()
