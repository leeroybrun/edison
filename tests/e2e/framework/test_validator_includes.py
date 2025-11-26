from __future__ import annotations

import re
from pathlib import Path

import pytest


VALIDATOR_FILES = [
    Path(".agents/validators/global/global-codex.md"),
    Path(".agents/validators/global/global-claude.md"),
    Path(".agents/validators/security/codex-security.md"),
    Path(".agents/validators/performance/codex-performance.md"),
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_validator_files_exist():
    """All validator files must exist in expected locations."""
    missing = [str(p) for p in VALIDATOR_FILES if not p.exists()]
    assert not missing, f"Missing validator files: {missing}"


def test_validators_use_includes():
    """Each validator must use include-based composition with at least two includes."""
    for vf in VALIDATOR_FILES:
        if not vf.exists():
            pytest.skip("validators not created yet")
        content = _read(vf)
        includes = re.findall(r"\{\{include:([^}]+)\}\}", content)
        assert len(includes) >= 2, f"{vf} should contain at least 2 include directives"


def test_include_paths_valid():
    """Include directives must point to real template and overlay files."""
    expected_map = {
        ".agents/validators/global/global-codex.md": [
            ".edison/core/validators/templates/global-comprehensive.md",
            ".agents/validators/overlays/global-project.md",
        ],
        ".agents/validators/global/global-claude.md": [
            ".edison/core/validators/templates/global-comprehensive.md",
            ".agents/validators/overlays/global-project.md",
        ],
        ".agents/validators/security/codex-security.md": [
            ".edison/core/validators/templates/critical-security.md",
            ".agents/validators/overlays/security-project-requirements.md",
        ],
        ".agents/validators/performance/codex-performance.md": [
            ".edison/core/validators/templates/critical-performance.md",
            ".agents/validators/overlays/performance-project-benchmarks.md",
        ],
    }

    for vf in VALIDATOR_FILES:
        if not vf.exists():
            pytest.skip("validators not created yet")
        content = _read(vf)
        includes = re.findall(r"\{\{include:([^}]+)\}\}", content)
        included_paths = set(p.strip() for p in includes)
        for required in expected_map[str(vf)]:
            assert required in included_paths, f"{vf} missing include for: {required}"
            assert Path(required).exists(), f"Include target does not exist: {required}"


def test_no_mixed_content_above_includes():
    """Validators should not contain project-specific inline content before includes.

    We allow a small header and composition paragraph, but all concrete project
    tech stack details should live in overlays or 'Execution Notes' below includes.
    """
    forbidden_terms = [
        "nextjs",
        "prisma",
        "React",
        "uistyles",
        "sqldb",
        "Context7",
    ]

    for vf in VALIDATOR_FILES:
        if not vf.exists():
            pytest.skip("validators not created yet")
        content = _read(vf)
        # Only look at content before the first include
        pre_include = content.split("{{include:", 1)[0]
        hits = [t for t in forbidden_terms if t.lower() in pre_include.lower()]
        assert not hits, f"{vf} contains project-specific terms before includes: {hits}"


def test_rendered_output_complete(tmp_path: Path):
    """Rendered validators must contain both template and overlay content.

    Uses Python composition module to resolve includes.
    """
    from edison.core.composition.includes import resolve_includes

    # Probe strings expected in template and overlay outputs
    template_probes = {
        ".edison/core/validators/templates/global-comprehensive.md": [
            "Architecture",  # header expected in global template
            "Code Quality",
        ],
        ".edison/core/validators/templates/critical-security.md": [
            "Authentication & Session",
            "Input Validation & Output Encoding",
        ],
        ".edison/core/validators/templates/critical-performance.md": [
            "Performance",
            "Profiling",
        ],
    }

    overlay_probes = {
        ".agents/validators/overlays/global-project.md": ["project", "ExampleApp"],
        ".agents/validators/overlays/security-project-requirements.md": ["Authentication", "API"],
        ".agents/validators/overlays/performance-project-benchmarks.md": ["nextjs", "prisma"],
    }

    for vf in VALIDATOR_FILES:
        if not vf.exists():
            pytest.skip("validators not created yet")

        # Render using Python module
        content = _read(vf)
        try:
            output, _ = resolve_includes(content, vf)
        except Exception as e:
            pytest.fail(f"Include resolution failed for {vf}: {e}")

        assert "{{include:" not in output, "Unresolved include in rendered output"

        # Validate template probes
        for inc in re.findall(r"\{\{include:([^}]+)\}\}", content):
            inc = inc.strip()
            if inc in template_probes:
                for probe in template_probes[inc]:
                    assert probe.lower() in output.lower(), (
                        f"Rendered output missing template probe '{probe}' for {vf}"
                    )
            if inc in overlay_probes:
                found = any(p.lower() in output.lower() for p in overlay_probes[inc])
                assert found, f"Rendered output missing overlay content for {vf} from {inc}"