from __future__ import annotations

import os
from pathlib import Path
import re

import sys

from edison.core.composition import (
    resolve_includes,
    compose_prompt,
    ComposeError,
    dry_duplicate_report,
)


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


def test_compose_integration_smoke():
    # Compose using real core + no packs to avoid external deps
    codex_core = ROOT / "validators" / "global" / "codex-core.md"
    assert codex_core.exists(), "codex-core.md must exist"
    res = compose_prompt(
        validator_id="codex-global",
        core_base=codex_core,
        pack_contexts=[],
        overlay=ROOT.parent / ".agents" / "validators" / "overlays" / "codex-global-overlay.md",
        enforce_dry=True,
    )
    assert res.cache_path and res.cache_path.exists()
    assert "Core Edison Principles" in res.text
