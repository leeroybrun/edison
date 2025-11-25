from __future__ import annotations

from pathlib import Path


def _core_lib_root() -> Path:
    # This file lives at .edison/core/tests/legacy/...
    return Path(__file__).resolve().parents[3] / ".edison" / "core" / "lib"


def _iter_python_files(root: Path):
    for path in root.rglob("*.py"):
        # Skip compiled caches or non-files defensively
        if path.is_file():
            yield path


def test_no_project_pre_edison_paths_in_core_libs() -> None:
    """
    Core libraries must not reference project-pre-edison paths at runtime.
    """
    root = _core_lib_root()
    markers = ("project-pre-edison", "../project-pre-edison")

    for path in _iter_python_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for marker in markers:
            assert marker not in text, f"Legacy pre-Edison marker '{marker}' found in {path}"


def test_no_edison_validators_config_json_in_core_libs() -> None:
    """
    Core libraries must not load legacy .edison/validators/config.json at runtime.
    """
    root = _core_lib_root()
    forbidden = ".edison/validators/config.json"

    for path in _iter_python_files(root):
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert forbidden not in text, f"Legacy validators config path found in {path}"

