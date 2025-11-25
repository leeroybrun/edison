from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any

import yaml
import pytest

ROOT = Path(__file__).resolve().parents[4]
core_path = ROOT / ".edison" / "core"
from edison.core.composition.hooks import HookComposer, HookDefinition  # type: ignore  # noqa: E402


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


def _write_yaml(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


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
    core_defs = _sample_hook_def("core-hook", description="From core")
    _write_yaml(tmp_path / ".edison/core/config/hooks.yaml", {"hooks": {"definitions": core_defs}})

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    defs = composer.load_definitions()

    assert "core-hook" in defs
    loaded = defs["core-hook"]
    assert loaded.description == "From core"
    assert loaded.config == {}


def test_merge_pack_definitions(tmp_path: Path) -> None:
    core_defs = _sample_hook_def(
        "shared",
        description="core",
        config={"nested": {"a": 1}, "list": ["a"]},
    )
    pack_override = _sample_hook_def(
        "shared",
        description="pack",
        config={"nested": {"b": 2}, "list": ["=b"]},
    )
    pack_only = _sample_hook_def("pack-only", description="pack only")

    _write_yaml(tmp_path / ".edison/core/config/hooks.yaml", {"hooks": {"definitions": core_defs}})
    _write_yaml(
        tmp_path / ".edison/packs/pack1/config/hooks.yml",
        {"hooks": {"definitions": {**pack_override, **pack_only}}},
    )

    config = {"hooks": {}, "packs": {"active": ["pack1"]}}
    composer = HookComposer(config=config, repo_root=tmp_path)
    defs = composer.load_definitions()

    shared = defs["shared"]
    assert shared.description == "pack"
    assert shared.config["nested"] == {"a": 1, "b": 2}
    assert shared.config["list"] == ["b"]
    assert "pack-only" in defs


def test_apply_project_overrides(tmp_path: Path) -> None:
    core_defs = _sample_hook_def("shared", description="core", matcher="*")
    pack_override = _sample_hook_def("shared", description="pack", matcher="Write")
    project_override = _sample_hook_def("shared", description="project", matcher="Edit")

    _write_yaml(tmp_path / ".edison/core/config/hooks.yaml", {"hooks": {"definitions": core_defs}})
    _write_yaml(
        tmp_path / ".edison/packs/pack1/config/hooks.yml",
        {"hooks": {"definitions": pack_override}},
    )
    _write_yaml(tmp_path / ".agents/config/hooks.yml", {"hooks": {"definitions": project_override}})

    config = {"hooks": {}, "packs": {"active": ["pack1"]}}
    composer = HookComposer(config=config, repo_root=tmp_path)
    defs = composer.load_definitions()
    shared = defs["shared"]

    assert shared.description == "project"
    assert shared.matcher == "Edit"


def test_filter_enabled_only(tmp_path: Path) -> None:
    core_defs = {
        **_sample_hook_def("enabled-hook", enabled=True, template="tmpl1.sh"),
        **_sample_hook_def("disabled-hook", enabled=False, template="tmpl2.sh"),
    }
    _write_yaml(tmp_path / ".edison/core/config/hooks.yaml", {"hooks": {"definitions": core_defs}})

    tmpl_dir = tmp_path / ".edison/core/templates/hooks"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "tmpl1.sh").write_text("#!/bin/bash\necho enabled\n", encoding="utf-8")
    (tmpl_dir / "tmpl2.sh").write_text("#!/bin/bash\necho disabled\n", encoding="utf-8")

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    scripts = composer.compose_hooks()

    assert set(scripts.keys()) == {"enabled-hook"}
    assert scripts["enabled-hook"].exists()


def test_render_hook_from_template(tmp_path: Path) -> None:
    tmpl_dir = tmp_path / ".edison/core/templates/hooks"
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
    tmpl_dir = tmp_path / ".edison/core/templates/hooks"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "compose.sh.template").write_text("#!/usr/bin/env bash\necho {{ id }}", encoding="utf-8")

    core_defs = _sample_hook_def("compose", template="compose.sh.template", description="Compose me")
    _write_yaml(tmp_path / ".edison/core/config/hooks.yaml", {"hooks": {"definitions": core_defs}})

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    scripts = composer.compose_hooks()

    out_path = scripts["compose"]
    assert out_path.exists()
    assert out_path.read_text(encoding="utf-8").strip().endswith("compose")
    assert out_path.parent == tmp_path / ".claude" / "hooks"
    assert out_path.stat().st_mode & 0o111, "script should be executable"


def test_generate_settings_json_section(tmp_path: Path) -> None:
    tmpl_dir = tmp_path / ".edison/core/templates/hooks"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "a.sh.template").write_text("#!/bin/bash\necho A", encoding="utf-8")
    (tmpl_dir / "b.sh.template").write_text("#!/bin/bash\necho B", encoding="utf-8")

    defs = {
        **_sample_hook_def(
            "remind",
            type="PreToolUse",
            hook_type="command",
            matcher="Write|Edit",
            template="a.sh.template",
        ),
        **_sample_hook_def(
            "inject",
            type="UserPromptSubmit",
            hook_type="prompt",
            matcher="*",
            template="b.sh.template",
        ),
    }
    _write_yaml(tmp_path / ".edison/core/config/hooks.yaml", {"hooks": {"definitions": defs}})

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    composer.compose_hooks()  # ensure scripts exist
    hooks_section = composer.generate_settings_json_hooks_section()

    assert "hooks" in hooks_section
    pre = hooks_section["hooks"]["PreToolUse"][0]
    assert pre["matcher"] == "Write|Edit"
    assert pre["hooks"][0]["type"] == "command"
    assert pre["hooks"][0]["command"].endswith(".claude/hooks/remind.sh")

    prompt = hooks_section["hooks"]["UserPromptSubmit"][0]["hooks"][0]
    assert prompt["type"] == "prompt"
    assert prompt["prompt"].endswith(".claude/hooks/inject.sh")


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
    _write_yaml(tmp_path / ".edison/core/config/hooks.yaml", {"hooks": {"definitions": defs}})
    tmpl_dir = tmp_path / ".edison/core/templates/hooks"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "t.sh.template").write_text("#!/bin/bash\n", encoding="utf-8")

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    loaded = composer.load_definitions()

    assert set(loaded.keys()) == {f"hook-{i}" for i in range(len(ALLOWED_TYPES))}

    bad_defs = _sample_hook_def("bad", type="UnknownType")
    _write_yaml(tmp_path / ".edison/core/config/hooks.yaml", {"hooks": {"definitions": bad_defs}})
    with pytest.raises(ValueError):
        HookComposer(config={"hooks": {}}, repo_root=tmp_path).load_definitions()


def test_blocking_only_for_pretooluse(tmp_path: Path) -> None:
    defs = _sample_hook_def(
        "post-blocking",
        type="PostToolUse",
        blocking=True,
        template="t.sh.template",
    )
    _write_yaml(tmp_path / ".edison/core/config/hooks.yaml", {"hooks": {"definitions": defs}})
    tmpl_dir = tmp_path / ".edison/core/templates/hooks"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    (tmpl_dir / "t.sh.template").write_text("#!/bin/bash\n", encoding="utf-8")

    composer = HookComposer(config={"hooks": {}}, repo_root=tmp_path)
    with pytest.raises(ValueError):
        composer.load_definitions()
