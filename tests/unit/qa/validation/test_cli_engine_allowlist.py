from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from edison.core.qa.engines.base import EngineConfig
from edison.core.qa.engines.cli import CLIEngine


def _write_orchestration_allowlist(root: Path, value) -> None:
    cfg_dir = root / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    # Use YAML because that is how projects configure orchestration.
    (cfg_dir / "orchestration.yml").write_text(
        "orchestration:\n"
        f"  allowCliEngines: {value}\n",
        encoding="utf-8",
    )


def test_cli_engine_can_execute_respects_allowlist(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Allow only gemini-cli
    _write_orchestration_allowlist(isolated_project_env, "[gemini-cli]")

    cfg = EngineConfig.from_dict(
        "coderabbit-cli",
        {"type": "cli", "command": "coderabbit", "subcommand": "review"},
    )
    engine = CLIEngine(cfg, project_root=isolated_project_env)

    # Pretend the binary exists; the allowlist should still block execution.
    monkeypatch.setattr(shutil, "which", lambda _: "/bin/true")

    assert engine.can_execute() is False


def test_cli_engine_can_execute_allows_when_in_allowlist(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_orchestration_allowlist(isolated_project_env, "[gemini-cli]")

    cfg = EngineConfig.from_dict(
        "gemini-cli",
        {"type": "cli", "command": "gemini"},
    )
    engine = CLIEngine(cfg, project_root=isolated_project_env)
    monkeypatch.setattr(shutil, "which", lambda _: "/bin/true")

    assert engine.can_execute() is True


def test_cli_engine_can_execute_allows_all_when_true(
    isolated_project_env: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_orchestration_allowlist(isolated_project_env, "true")

    cfg = EngineConfig.from_dict(
        "coderabbit-cli",
        {"type": "cli", "command": "coderabbit", "subcommand": "review"},
    )
    engine = CLIEngine(cfg, project_root=isolated_project_env)
    monkeypatch.setattr(shutil, "which", lambda _: "/bin/true")

    assert engine.can_execute() is True

