from __future__ import annotations

import re
from pathlib import Path

import pytest

from edison.data import get_data_path


DATA_ROOT = get_data_path("config").parent

# Canonical validator templates live in bundled data (not `.agents/validators/*`).
VALIDATOR_TEMPLATES = [
    get_data_path("validators", "global.md"),
    get_data_path("validators", "critical/security.md"),
    get_data_path("validators", "critical/performance.md"),
]


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_validator_files_exist() -> None:
    missing = [str(p) for p in VALIDATOR_TEMPLATES if not p.exists()]
    assert not missing, f"Missing validator templates: {missing}"


def test_validators_use_includes() -> None:
    """Validators must include the shared validator constitution (minimum)."""
    for vf in VALIDATOR_TEMPLATES:
        content = _read_file(vf)
        includes = [p.strip() for p in re.findall(r"\{\{include:([^}]+)\}\}", content)]
        assert includes, f"{vf} should contain at least one {{include:...}} directive"


def test_include_paths_valid() -> None:
    """Every {{include:*}} target must exist relative to the bundled data root."""
    for vf in VALIDATOR_TEMPLATES:
        content = _read_file(vf)
        includes = [p.strip().strip("'\"") for p in re.findall(r"\{\{include:([^}]+)\}\}", content)]
        for inc in includes:
            target = (DATA_ROOT / inc).resolve()
            assert target.exists(), f"Include target does not exist: {inc} -> {target}"


def test_rendered_output_has_no_unresolved_includes() -> None:
    """Rendering via TemplateEngine must fully resolve nested includes."""
    from edison.core.composition.engine import TemplateEngine

    engine = TemplateEngine(
        config={},
        packs=[],
        project_root=Path(".").resolve(),
        source_dir=DATA_ROOT,
        include_provider=None,
        strip_section_markers=True,
    )

    for vf in VALIDATOR_TEMPLATES:
        content = _read_file(vf)
        output, _report = engine.process(content, entity_name=str(vf), entity_type="validators")
        assert "{{include:" not in output, f"Unresolved include in rendered output for {vf}"









