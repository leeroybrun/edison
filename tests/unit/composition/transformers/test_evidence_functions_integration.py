"""Integration tests for evidence template functions."""

from __future__ import annotations

from pathlib import Path

from edison.core.composition.engine import TemplateEngine


def test_evidence_file_uses_config_value(tmp_path: Path) -> None:
    engine = TemplateEngine(
        config={"validation": {"evidence": {"files": {"test": "pytest-output.txt"}}}},
        packs=[],
        project_root=tmp_path,
    )
    content, _ = engine.process('E={{function:evidence_file("test")}}', entity_name="test")
    assert content == "E=pytest-output.txt"


def test_evidence_file_falls_back_when_missing(tmp_path: Path) -> None:
    engine = TemplateEngine(config={}, packs=[], project_root=tmp_path)
    content, _ = engine.process('E={{function:evidence_file("test")}}', entity_name="test")
    assert content == "E=command-test.txt"


def test_evidence_file_treats_blank_as_missing(tmp_path: Path) -> None:
    engine = TemplateEngine(
        config={"validation": {"evidence": {"files": {"test": ""}}}},
        packs=[],
        project_root=tmp_path,
    )
    content, _ = engine.process('E={{function:evidence_file("test")}}', entity_name="test")
    assert content == "E=command-test.txt"

