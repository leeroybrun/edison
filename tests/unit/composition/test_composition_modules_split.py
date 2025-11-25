from __future__ import annotations

import importlib
from pathlib import Path

import pytest


def test_includes_resolve_and_cache_dir(tmp_path: Path) -> None:
    repo = tmp_path
    project_dir = repo / ".edison" / "config"
    project_dir.mkdir(parents=True)

    base = repo / "docs"
    base.mkdir()
    inc = base / "inc.md"
    inc.write_text("world", encoding="utf-8")
    main = base / "main.md"
    main.write_text("hello {{include:inc.md}}", encoding="utf-8")

    includes = importlib.import_module("edison.core.composition.includes")
    includes._REPO_ROOT_OVERRIDE = repo

    expanded, deps = includes.resolve_includes(main.read_text(), main)

    assert "world" in expanded
    assert inc.resolve() in deps

    cache_dir = includes.get_cache_dir()
    assert cache_dir.name == "composed"
    assert repo in cache_dir.parents


def test_packs_auto_activation_respects_triggers(tmp_path: Path) -> None:
    repo = tmp_path
    packs_root = repo / "packs"
    packs_root.mkdir()

    pack_dir = packs_root / "alpha"
    pack_dir.mkdir()
    (pack_dir / "pack.yml").write_text(
        "triggers:\n  filePatterns:\n    - \"src/**/models/*.py\"\n",
        encoding="utf-8",
    )

    changed = repo / "src/service/models/model.py"
    changed.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("# model", encoding="utf-8")

    includes = importlib.import_module("edison.core.composition.includes")
    includes._REPO_ROOT_OVERRIDE = repo

    packs = importlib.import_module("edison.core.composition.packs")
    if getattr(packs, "yaml", None) is None:
        pytest.skip("PyYAML not installed")

    activated = packs.auto_activate_packs([changed], pack_root=packs_root)
    assert activated == {"alpha"}


def test_formatting_strips_code_fences() -> None:
    formatting = importlib.import_module("edison.core.composition.formatting")
    content = "# Title\n```python\nprint('x')\n```\n"
    rendered = formatting.format_for_zen(content)
    assert "```" not in rendered
    assert "Title" in rendered


def test_orchestrator_workflow_loop_defaults() -> None:
    orchestrator = importlib.import_module("edison.core.composition.orchestrator")
    loop = orchestrator.get_workflow_loop_instructions()
    assert "scripts/session next" in loop["command"]
