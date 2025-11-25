from __future__ import annotations

from pathlib import Path

import pytest


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if parent.name == ".edison":
            continue
        if (parent / ".git").exists():
            return parent
    raise AssertionError("cannot locate repository root for integration tests")


def _core_scripts_root() -> Path:
    return _repo_root() / ".edison" / "core" / "scripts"


CLI_SCRIPTS = [
    "session/cli",
    "session/close",
    "session/validate",
    "session/next",
    "session/verify",
    "session/track",
    "session/recovery/clear-locks",
    "session/recovery/clean-worktrees",
    "session/recovery/recover-validation-tx",
    "session/recovery/repair-session",
    "session/recovery/recover-timed-out-sessions",
    "tasks/claim",
    "tasks/ensure-followups",
    "validators/validate",
    "delegation/validate",
    "delegation/validate-basic",
    "implement/validate",
]


@pytest.mark.integration
def test_all_clis_use_run_cli_pattern() -> None:
    """Ensure all Edison CLI entrypoints delegate to cli_utils.run_cli()."""
    scripts_root = _core_scripts_root()

    for rel in CLI_SCRIPTS:
        path = scripts_root / rel
        assert path.exists(), f"CLI script missing: {path}"

        text = path.read_text(encoding="utf-8")
        assert "cli_utils.run_cli" in text, f"CLI {rel} does not use cli_utils.run_cli at entrypoint"
