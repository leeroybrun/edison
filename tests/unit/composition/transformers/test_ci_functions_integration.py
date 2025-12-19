"""Integration tests for CI command template functions."""

from __future__ import annotations

from pathlib import Path

from edison.core.composition.engine import TemplateEngine


def test_ci_command_falls_back_when_missing(tmp_path: Path) -> None:
    engine = TemplateEngine(config={}, packs=[], project_root=tmp_path)
    content, _ = engine.process('CMD={{function:ci_command("test")}}', entity_name="test")
    assert content == "CMD=<test-command>"


def test_ci_command_uses_project_config_value(tmp_path: Path) -> None:
    engine = TemplateEngine(
        config={"ci": {"commands": {"test": "pytest -q"}}},
        packs=[],
        project_root=tmp_path,
    )
    content, _ = engine.process('CMD={{function:ci_command("test")}}', entity_name="test")
    assert content == "CMD=pytest -q"


def test_ci_command_treats_blank_as_missing(tmp_path: Path) -> None:
    engine = TemplateEngine(config={"ci": {"commands": {"test": ""}}}, packs=[], project_root=tmp_path)
    content, _ = engine.process('CMD={{function:ci_command("test")}}', entity_name="test")
    assert content == "CMD=<test-command>"


def test_ci_command_supports_hyphenated_keys(tmp_path: Path) -> None:
    engine = TemplateEngine(
        config={"ci": {"commands": {"type-check": "mypy --strict"}}},
        packs=[],
        project_root=tmp_path,
    )
    content, _ = engine.process('CMD={{function:ci_command("type-check")}}', entity_name="test")
    assert content == "CMD=mypy --strict"

