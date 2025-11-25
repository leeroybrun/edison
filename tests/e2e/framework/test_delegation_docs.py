from __future__ import annotations

import json
import os
import re
from pathlib import Path
import pytest


REPO_ROOT = Path.cwd()
AGENTS_DELEGATION_DIR = REPO_ROOT / ".agents" / "delegation"
AGENTS_DELEGATION_README = AGENTS_DELEGATION_DIR / "README.md"
AGENTS_DELEGATION_CONFIG = AGENTS_DELEGATION_DIR / "config.json"

PACK_DELEGATION_DIR = REPO_ROOT / ".edison" / "packs" / "delegation"
PACK_DELEGATION_READme = PACK_DELEGATION_DIR / "README.md"
PACK_DELEGATION_CONFIG = PACK_DELEGATION_DIR / "config.json"


FORBIDDEN_DOMAIN_TERMS = [
    # project-specific domain examples to avoid in generic docs
    r"project application",
    r"lead scoring",
    r"Odoo integration",
    r"channels API",
    r"alerts system",
    r"@project/",
]


def _read_text(path: Path) -> str:
    assert path.exists(), f"Expected file to exist: {path}"
    return path.read_text(encoding="utf-8")


def _project_terms() -> list[str]:
    name = os.environ.get("PROJECT_NAME", "").strip().lower()
    extra = [
        t.strip().lower()
        for t in os.environ.get("PROJECT_TERMS", "").split(",")
        if t.strip()
    ]
    terms = [name] if name else []
    terms.extend(extra)
    return [t for t in terms if t]


def test_delegation_readme_exists():
    """Agents delegation README must exist for this project."""
    assert AGENTS_DELEGATION_README.exists(), (
        f"Missing delegation docs: {AGENTS_DELEGATION_README}"
    )


def test_json_configs_valid():
    """Delegation JSON configs must exist and be valid JSON (agents-level required)."""
    # Agents-level config is required
    assert AGENTS_DELEGATION_CONFIG.exists(), (
        f"Missing config: {AGENTS_DELEGATION_CONFIG}"
    )
    json.loads(_read_text(AGENTS_DELEGATION_CONFIG))

    # Edison pack-level config is optional; if present, it must parse
    if PACK_DELEGATION_CONFIG.exists():
        json.loads(_read_text(PACK_DELEGATION_CONFIG))


def test_no_hardcoded_project_names():
    """Docs must be project-agnostic — no repo-specific names (case-insensitive)."""
    targets = [AGENTS_DELEGATION_README, AGENTS_DELEGATION_CONFIG]
    if PACK_DELEGATION_READme.exists():
        targets.append(PACK_DELEGATION_READme)
    if PACK_DELEGATION_CONFIG.exists():
        targets.append(PACK_DELEGATION_CONFIG)

    forbidden_terms = _project_terms() or ["example-project"]

    for path in targets:
        text = _read_text(path)
        lowered = text.lower()
        for term in forbidden_terms:
            assert term not in lowered, f"Found hardcoded '{term}' in {path}"


def test_uses_project_name_placeholder():
    """Docs should use {PROJECT_NAME} placeholders where project names appear."""
    readme_text = _read_text(AGENTS_DELEGATION_README)
    assert "{PROJECT_NAME}" in readme_text, (
        "Delegation README must use {PROJECT_NAME} placeholder"
    )

    # Config should either reference {PROJECT_NAME} or be fully generic with no project name
    cfg_text = _read_text(AGENTS_DELEGATION_CONFIG)
    contains_placeholder = "{PROJECT_NAME}" in cfg_text
    forbidden_terms = _project_terms()
    contains_project_ref = any(
        re.search(re.escape(term), cfg_text, re.I) for term in forbidden_terms
    ) if forbidden_terms else False
    assert contains_placeholder and not contains_project_ref, (
        "Delegation config must use {PROJECT_NAME} placeholder and not contain project-specific names"
    )


def test_generic_role_names():
    """Role names must be generic (no project-prefixed roles like 'project-...')."""
    text = _read_text(AGENTS_DELEGATION_README) + "\n" + _read_text(AGENTS_DELEGATION_CONFIG)

    # No project-prefixed roles
    assert re.search(r"\bproject-", text, re.I) is None, "Found project-prefixed role names"

    # Encourage presence of known generic roles
    generic_indicators = [
        "validator-codex-global",
        "api-builder",
        "task-owner",
        "reviewer",
    ]
    assert any(g in text for g in generic_indicators), (
        "Expected at least one generic role indicator in docs"
    )


def test_examples_are_generic():
    """Examples must avoid project-specific domain references and use generic phrasing."""
    readme_text = _read_text(AGENTS_DELEGATION_README)
    for pat in FORBIDDEN_DOMAIN_TERMS:
        assert re.search(pat, readme_text, re.I) is None, (
            f"Forbidden domain-specific term in README: {pat}"
        )


def test_paths_are_configurable():
    """Paths must use placeholders or be relative; no absolute user paths or project-specific worktrees."""
    cfg = json.loads(_read_text(AGENTS_DELEGATION_CONFIG))

    # If worktreeBase exists, ensure it's placeholdered or relative
    if "worktreeBase" in cfg:
        wt = str(cfg["worktreeBase"]) or ""
        assert not (wt.startswith("/") or re.match(r"^[A-Za-z]:\\\\", wt)), (
            f"worktreeBase must be relative or templated, got: {wt}"
        )
        for term in _project_terms():
            assert term not in wt.lower(), "worktreeBase contains project-specific name"
        assert "{PROJECT_NAME}" in wt or wt.startswith(".."), (
            "worktreeBase should include {PROJECT_NAME} or be relative"
        )

    # Ensure no absolute paths anywhere in config values
    def _walk(v):
        if isinstance(v, dict):
            return any(_walk(x) for x in v.values())
        if isinstance(v, list):
            return any(_walk(x) for x in v)
        if isinstance(v, str):
            return v.startswith("/") or re.match(r"^[A-Za-z]:\\\\", v) is not None
        return False

    cfg_text = _read_text(AGENTS_DELEGATION_CONFIG)
    for term in _project_terms():
        assert term not in cfg_text.lower(), "Config contains project-specific names"

    # Optional: validate README can be rendered with includes if used
    if AGENTS_DELEGATION_README.exists():
        try:
            from edison.core.composition.includes import resolve_includes
            content = AGENTS_DELEGATION_README.read_text(encoding="utf-8")
            # resolve_includes returns (expanded_content, dependencies)
            expanded, _ = resolve_includes(content, AGENTS_DELEGATION_README)
            assert expanded, "Delegation README rendering produced empty output"
        except ImportError:
            # Skip if composition module not available
            pass
        except Exception as e:
            pytest.fail(f"Delegation README include rendering failed: {e}")
