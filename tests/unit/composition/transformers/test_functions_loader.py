import textwrap
from pathlib import Path
from typing import Optional

import pytest

from edison.core.composition.engine import TemplateEngine
from edison.core.composition.transformers.functions_loader import load_functions
from edison.core.composition.transformers.functions import global_registry


def _write_function(path: Path, name: str, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body), encoding="utf-8")


def test_load_functions_core_pack_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Functions from project override pack which override core."""

    # Fake project layout
    project_root = tmp_path
    core_dir = project_root / "core"  # will be pointed to via CompositionPathResolver monkeypatch
    packs_dir = project_root / "packs"
    project_dir = project_root / ".edison"

    # Prepare directory structure
    (core_dir / "functions").mkdir(parents=True, exist_ok=True)
    (packs_dir / "p1" / "functions").mkdir(parents=True, exist_ok=True)
    (project_dir / "functions").mkdir(parents=True, exist_ok=True)

    # Write functions
    _write_function(
        core_dir / "functions" / "greet.py",
        "greet",
        """
        def greet():
            return "hello from core"
        """,
    )

    _write_function(
        packs_dir / "p1" / "functions" / "greet.py",
        "greet",
        """
        def greet():
            return "hello from pack"
        """,
    )

    _write_function(
        project_dir / "functions" / "greet.py",
        "greet",
        """
        def greet():
            return "hello from project"
        """,
    )

    # Monkeypatch CompositionPathResolver to use our fake layout
    from edison.core.composition.core import paths as paths_mod
    from edison.core.composition.transformers import functions_loader as fl_mod

    class FakeResolver:
        def __init__(self, project_root: Path, content_type: Optional[str] = None):
            self.repo_root = project_root
            self.project_root = project_root
            self.project_dir = project_dir
            self.user_dir = project_root / ".edison-user"
            self.core_dir = core_dir
            self.packs_dir = packs_dir
            self.bundled_packs_dir = packs_dir
            self.user_packs_dir = self.user_dir / "packs"
            self.project_packs_dir = project_dir / "packs"

    monkeypatch.setattr(paths_mod, "CompositionPathResolver", FakeResolver)
    monkeypatch.setattr(fl_mod, "CompositionPathResolver", FakeResolver)

    # Clear registry before loading
    for name in list(global_registry.list_functions()):
        global_registry._functions.pop(name, None)  # type: ignore[attr-defined]

    load_functions(project_root, ["p1"])

    assert "greet" in global_registry
    func = global_registry.get("greet")
    assert func is not None
    assert func() == "hello from project"  # project overrides pack/core


def test_template_engine_executes_functions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    project_root = tmp_path

    # Project-layer function (loaded from .edison/functions)
    project_dir = project_root / ".edison"
    _write_function(
        project_dir / "functions" / "adder.py",
        "adder",
        """
        def add(a, b):
            return str(int(a) + int(b))
        """,
    )

    engine = TemplateEngine(config={}, packs=[], project_root=project_root)
    result, _ = engine.process("Result: {{function:add(2, 3)}}")
    assert "Result: 5" in result
