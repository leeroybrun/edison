"""Tests for the {{fn:...}} function-call alias."""

from __future__ import annotations

from pathlib import Path

from edison.core.composition.engine import TemplateEngine


def test_fn_alias_calls_function_without_args(tmp_path: Path) -> None:
    engine = TemplateEngine(config={}, packs=[], project_root=tmp_path)
    content, _ = engine.process("{{fn:tasks_states}}", entity_name="test")
    assert "**todo**" in content


def test_fn_alias_supports_context_var_substitution(tmp_path: Path) -> None:
    engine = TemplateEngine(config={}, packs=[], project_root=tmp_path)
    content, _ = engine.process(
        "{{fn:tasks_states current_state}}",
        entity_name="test",
        context_vars={"current_state": "wip"},
    )
    assert content.startswith("wip:")


def test_fn_alias_supports_parenthesized_args(tmp_path: Path) -> None:
    engine = TemplateEngine(config={}, packs=[], project_root=tmp_path)
    content, _ = engine.process('{{fn:tasks_states("done")}}', entity_name="test")
    assert content.startswith("done:")

