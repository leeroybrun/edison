from __future__ import annotations

import os
from pathlib import Path

from edison.core.config.cache import clear_all_caches
from edison.core.config.domains.session import SessionConfig


def _write_config(root: Path, yaml_text: str) -> None:
    cfg_path = root / ".edison" / "config" / "config.yml"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(yaml_text, encoding="utf-8")
    (root / ".project").mkdir(exist_ok=True)


def _use_root(tmp_path: Path) -> None:
    os.environ["AGENTS_PROJECT_ROOT"] = str(tmp_path)
    clear_all_caches()


def test_session_states_honor_project_override(tmp_path: Path) -> None:
    """Project YAML should override state directory mapping without inline defaults."""

    _write_config(
        tmp_path,
        """
        session:
          paths:
            root: .project/sessions
          validation:
            maxLength: 32
          states:
            active: working
            done: shipped
        """,
    )
    _use_root(tmp_path)

    cfg = SessionConfig(repo_root=tmp_path)
    states = cfg.get_session_states()

    assert states["active"] == "working"
    assert states["done"] == "shipped"
    assert isinstance(states, dict) and states
