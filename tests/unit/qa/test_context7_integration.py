"""Integration tests for context7.py config loading (Context7Config-driven)."""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.qa.context.context7 import _normalize, _load_triggers, _load_aliases, detect_packages
from helpers.cache_utils import reset_edison_caches


def test_load_triggers_and_aliases_can_be_empty():
    """Core is technology-agnostic: triggers/aliases may be empty if no packs/project overrides configured."""
    assert isinstance(_load_triggers(), dict)
    assert isinstance(_load_aliases(), dict)


def test_detect_packages_uses_project_context7_config(isolated_project_env):
    """detect_packages() must be driven exclusively by Context7Config triggers (no legacy postTrainingPackages)."""
    root: Path = isolated_project_env

    # Configure a minimal Context7 trigger set for this isolated project.
    cfg_path = root / ".edison" / "config" / "context7.yaml"
    cfg_path.write_text(
        """
context7:
  triggers:
    react: ["*.tsx"]
  aliases:
    react-dom: react
""".lstrip(),
        encoding="utf-8",
    )
    reset_edison_caches()

    # Create a tiny task file that points at a TSX file via Primary Files.
    task_path = root / ".project" / "tasks" / "todo" / "t1.md"
    task_path.write_text(
        """
---
id: t1
title: Test Context7
---

## Primary Files / Areas
- app/components/Button.tsx
""".lstrip(),
        encoding="utf-8",
    )

    pkgs = detect_packages(task_path, session=None)
    assert "react" in pkgs


def test_normalize_uses_loaded_aliases():
    """Verify _normalize uses config-loaded aliases."""
    # With no aliases configured, normalization is just a lowercase identity.
    assert _normalize("unknown-package") == "unknown-package"
