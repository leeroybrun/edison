from __future__ import annotations

import os
from pathlib import Path
import re
import shutil

import sys

from edison.core.composition import (
    resolve_includes,
    compose_prompt,
    ComposeError,
    dry_duplicate_report,
)
from edison.core.composition.includes import _get_max_depth

# Define ROOT as the edison project root directory
ROOT = Path(__file__).resolve().parent.parent


def _p(rel: str) -> Path:
    return ROOT / "tests" / "context" / "comp_samples" / rel


def test_basic_include_and_optional():
    base = _p("base.md")
    text = base.read_text(encoding="utf-8")
    expanded, deps = resolve_includes(text, base)
    assert "A1" in expanded and "B1" in expanded
    assert "LEGACY" in expanded  # via legacy shim
    # optional missing include should be dropped silently
    assert "maybe.md" not in expanded
    assert any("include/sub/b.md" in str(p) for p in deps)


def test_circular_detection():
    a = _p("circular/a.md")
    with open(a, "r", encoding="utf-8") as f:
        content = f.read()
    try:
        resolve_includes(content, a)
        assert False, "Expected circular include detection"
    except ComposeError as err:
        assert "Circular include detected" in str(err)


def test_depth_limit():
    # Build a chain > 3 levels deep dynamically
    tmp_dir = ROOT / "tests" / "context" / "comp_samples" / "deep"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    for i in range(5):
        cur = tmp_dir / f"{i}.md"
        nxt = tmp_dir / f"{i+1}.md"
        if i < 4:
            body = "L{} {{{{include:{}}}}}".format(i, nxt.relative_to(cur.parent))
        else:
            body = "END"
        cur.write_text(body, encoding="utf-8")
    base = tmp_dir / "0.md"
    try:
        resolve_includes(base.read_text(encoding="utf-8"), base)
        assert False, "Expected depth overflow"
    except ComposeError as err:
        assert ">3" in str(err) or "exceeded" in str(err)


def test_max_depth_from_config():
    """Test that max_depth is loaded from configuration."""
    # This test verifies that _get_max_depth() reads from defaults.yaml
    max_depth = _get_max_depth()
    # Should be 3 from defaults.yaml
    assert max_depth == 3, f"Expected max_depth=3 from config, got {max_depth}"


def test_depth_limit_configurable():
    """Test that max_depth can be configured via the max_depth parameter."""
    # Build a chain of 3 levels deep
    tmp_dir = ROOT / "tests" / "context" / "comp_samples" / "configurable_depth"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    # Create a 3-level include chain: 0 -> 1 -> 2 -> END
    for i in range(4):
        cur = tmp_dir / f"{i}.md"
        nxt = tmp_dir / f"{i+1}.md"
        if i < 3:
            body = "L{} {{{{include:{}}}}}".format(i, nxt.relative_to(cur.parent))
        else:
            body = "END"
        cur.write_text(body, encoding="utf-8")

    base = tmp_dir / "0.md"
    content = base.read_text(encoding="utf-8")

    # Should work with max_depth=3 (default)
    expanded, deps = resolve_includes(content, base, max_depth=3)
    assert "L0" in expanded and "L1" in expanded and "L2" in expanded and "END" in expanded

    # Should fail with max_depth=1 (only allows 0->1, not 0->1->2)
    try:
        resolve_includes(content, base, max_depth=1)
        assert False, "Expected depth overflow with max_depth=1"
    except ComposeError as err:
        assert ">1" in str(err) or "exceeded" in str(err)

    # Should work with max_depth=5
    expanded, deps = resolve_includes(content, base, max_depth=5)
    assert "L0" in expanded and "L1" in expanded and "L2" in expanded and "END" in expanded


def test_dry_linter():
    core = "# H\n" + ("alpha beta gamma delta " * 12)
    packs = ("alpha beta gamma delta " * 12)
    report = dry_duplicate_report({"core": core, "packs": packs, "overlay": ""}, min_shingles=2, k=12)
    assert report["violations"], "Expected DRY violations"


def test_compose_integration_smoke(isolated_project_env: Path):
    # Use isolated environment to avoid polluting Edison repo
    root = isolated_project_env

    # Copy validators directory structure to isolated environment
    # isolated_project_env creates .edison/core, so we should copy validators there
    src_validators = ROOT / "src" / "edison" / "data" / "validators"
    dst_validators = root / ".edison" / "core" / "validators"
    if src_validators.exists():
        dst_validators.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_validators, dst_validators, dirs_exist_ok=True)

    # Compose using real core + no packs to avoid external deps
    codex_core = dst_validators / "global" / "codex.md"
    assert codex_core.exists(), "codex.md must exist"

    # Set repo root override for composition modules to use isolated env
    import edison.core.composition.includes as includes
    import edison.core.composition.composers as composers
    includes._REPO_ROOT_OVERRIDE = root
    composers._REPO_ROOT_OVERRIDE = root

    res = compose_prompt(
        validator_id="global-codex",
        core_base=codex_core,
        pack_contexts=[],
        overlay=None,  # No overlay needed for smoke test
        enforce_dry=True,
    )
    assert res.cache_path and res.cache_path.exists()
    assert "Codex Global Validator" in res.text

    # Verify cache is in isolated environment, not Edison repo
    assert root in res.cache_path.parents, f"Cache path {res.cache_path} not in isolated env {root}"
