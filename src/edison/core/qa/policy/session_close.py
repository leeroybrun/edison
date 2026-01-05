"""Session-close validation policy helpers.

Session close is intentionally NOT inferred from changed files. It is an explicit
policy configured via:

    validation.sessionClose.preset

The returned ValidationPolicy can then be used to drive:
- required evidence commands (edison evidence capture --session-close)
- session close verification (edison session verify --phase closing)
"""

from __future__ import annotations

from pathlib import Path

from edison.core.config.domains.qa import QAConfig
from edison.core.qa.policy.resolver import ValidationPolicyResolver
from edison.core.qa.policy.models import ValidationPolicy


def get_session_close_policy(*, project_root: Path | None = None) -> ValidationPolicy:
    """Return the explicit session-close validation policy (fail-closed)."""
    qa_cfg = QAConfig(repo_root=project_root)
    session_close = qa_cfg.validation_config.get("sessionClose")
    if not isinstance(session_close, dict):
        raise ValueError("validation.sessionClose must be an object")

    preset = str(session_close.get("preset") or "").strip()
    if not preset:
        raise ValueError("validation.sessionClose.preset is required")

    # Explicit preset: must not depend on task file inference.
    resolver = ValidationPolicyResolver(project_root=qa_cfg.repo_root)
    return resolver.resolve_for_task("__session_close__", preset_name=preset)


__all__ = ["get_session_close_policy"]

