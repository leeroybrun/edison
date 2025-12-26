from __future__ import annotations

import re
from pathlib import Path

import yaml

from edison.data import get_data_path


DELEGATION_GUIDE = get_data_path("guidelines", "shared/DELEGATION.md")
DELEGATION_CONFIG = get_data_path("config", "delegation.yaml")


FORBIDDEN_DOMAIN_TERMS = [
    # project-specific domain examples to avoid in generic docs
    r"lead scoring",
    r"odoo integration",
    r"channels api",
]


def test_delegation_guideline_exists() -> None:
    assert DELEGATION_GUIDE.exists(), f"Missing delegation guideline: {DELEGATION_GUIDE}"


def test_delegation_config_exists_and_is_valid_yaml() -> None:
    assert DELEGATION_CONFIG.exists(), f"Missing delegation config: {DELEGATION_CONFIG}"
    data = yaml.safe_load(DELEGATION_CONFIG.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "delegation" in data


def test_delegation_docs_are_generic() -> None:
    text = DELEGATION_GUIDE.read_text(encoding="utf-8")
    for pat in FORBIDDEN_DOMAIN_TERMS:
        assert re.search(pat, text, re.I) is None, f"Forbidden domain-specific term in delegation docs: {pat}"


def test_delegation_docs_use_placeholders_when_needed() -> None:
    """Docs should prefer placeholders (e.g. {PROJECT_NAME}) instead of hardcoded repo names."""
    text = DELEGATION_GUIDE.read_text(encoding="utf-8")
    # This is a soft requirement: only assert that if docs show project naming, they use placeholders.
    if re.search(r"\bproject name\b", text, re.I):
        assert "{PROJECT_NAME}" in text, "Delegation docs mention project naming but do not use {PROJECT_NAME}"









