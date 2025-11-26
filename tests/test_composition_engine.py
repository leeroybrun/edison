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
    codex_core = dst_validators / "global" / "codex-core.md"
    assert codex_core.exists(), "codex-core.md must exist"

    # Set repo root override for composition modules to use isolated env
    import edison.core.composition.includes as includes
    import edison.core.composition.composers as composers
    includes._REPO_ROOT_OVERRIDE = root
    composers._REPO_ROOT_OVERRIDE = root

    res = compose_prompt(
        validator_id="codex-global",
        core_base=codex_core,
        pack_contexts=[],
        overlay=None,  # No overlay needed for smoke test
        enforce_dry=True,
    )
    assert res.cache_path and res.cache_path.exists()
    assert "Codex Global Validator" in res.text

    # Verify cache is in isolated environment, not Edison repo
    assert root in res.cache_path.parents, f"Cache path {res.cache_path} not in isolated env {root}"
