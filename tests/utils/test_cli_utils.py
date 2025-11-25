from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

import pytest
import yaml


def _write_cli_config(repo_root: Path) -> None:
    """Provision minimal config so cli utils pull values from YAML, not code defaults."""
    cfg = {
        "cli": {
            "json": {"indent": 4, "sort_keys": True, "ensure_ascii": False},
            "table": {"padding": 1, "column_gap": 2},
            "confirm": {"assume_yes_env": "EDISON_ASSUME_YES", "default": True},
            "output": {
                "success_prefix": "[OK]",
                "error_prefix": "[ERR]",
                "warning_prefix": "[WARN]",
                "use_color": False,
            },
        },
        "subprocess_timeouts": {
            "default": 5.0,
            "git_operations": 5.0,
            "file_operations": 5.0,
            "test_execution": 30.0,
            "build_operations": 60.0,
        },
    }
    cfg_dir = repo_root / ".edison" / "core" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "defaults.yaml"
    cfg_path.write_text(yaml.safe_dump(cfg), encoding="utf-8")


@pytest.fixture()
def cli_module(isolated_project_env: Path, monkeypatch):
    _write_cli_config(isolated_project_env)
    # Ensure module picks up fresh config for this repo root
    import edison.core.utils.cli as cli  # type: ignore

    importlib.reload(cli)
    return cli


def test_output_json_respects_configured_indent_and_sort(cli_module):
    text = cli_module.output_json({"b": 1, "a": 2}, pretty=True)
    loaded = json.loads(text)
    assert list(loaded.keys()) == ["a", "b"]  # sorted keys come from config
    # Indent=4 → nested line starts with 4 spaces
    assert "\n    \"a\": 2" in text


def test_output_table_formats_columns(cli_module):
    table = cli_module.output_table(
        rows=[["alpha", 1], ["beta", 22]],
        headers=["name", "count"],
    )
    lines = table.splitlines()
    # Header row padded and aligned
    assert lines[0].startswith("name")
    assert "count" in lines[0]
    # Column gap of 2 spaces
    assert "  " in lines[1]
    # Numeric values rendered as strings
    assert lines[2].strip().endswith("22")


def test_confirm_honors_env_shortcuts(cli_module, monkeypatch, capsys):
    # Environment variable should auto‑accept without prompting
    monkeypatch.setenv("EDISON_ASSUME_YES", "1")
    assert cli_module.confirm("Proceed?") is True
    captured = capsys.readouterr()
    assert "Proceed?" in captured.out  # message still echoed


def test_confirm_uses_default_on_empty_input(cli_module, monkeypatch):
    monkeypatch.delenv("EDISON_ASSUME_YES", raising=False)
    monkeypatch.setattr("builtins.input", lambda _: "")
    assert cli_module.confirm("Continue?") is True  # default comes from YAML (True)


def test_confirm_rejects_negative_response(cli_module, monkeypatch):
    monkeypatch.delenv("EDISON_ASSUME_YES", raising=False)
    monkeypatch.setattr("builtins.input", lambda _: "n")
    assert cli_module.confirm("Continue?") is False


def test_error_and_success_use_prefixes(cli_module, capsys):
    code = cli_module.error("Something went wrong", exit_code=3)
    out = capsys.readouterr()
    assert "[ERR] Something went wrong" in out.err
    assert code == 3

    cli_module.success("All good")
    out = capsys.readouterr()
    assert "[OK] All good" in out.out


def test_parse_common_args_adds_flags(cli_module):
    parser = argparse.ArgumentParser(add_help=False)
    cli_module.parse_common_args(parser)
    args = parser.parse_args(["--json", "--yes", "--repo-root", "/tmp/demo"])
    assert args.json is True
    assert args.yes is True
    assert Path(args.repo_root) == Path("/tmp/demo")


def test_session_parent_adds_session_flag(cli_module):
    parser = argparse.ArgumentParser(parents=[cli_module.session_parent()], add_help=False)
    args = parser.parse_args(["--session", "sess-123"])
    assert args.session == "sess-123"


def test_session_parent_can_require_value(cli_module):
    parser = argparse.ArgumentParser(parents=[cli_module.session_parent(required=True)], add_help=False)
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_dry_run_parent_adds_boolean_flag(cli_module):
    parser = argparse.ArgumentParser(parents=[cli_module.dry_run_parent()], add_help=False)
    args = parser.parse_args(["--dry-run"])
    assert args.dry_run is True
