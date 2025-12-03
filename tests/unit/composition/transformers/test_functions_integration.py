"""Integration test for FunctionTransformer with layered functions."""
from __future__ import annotations

from pathlib import Path

from edison.core.composition.engine import TemplateEngine
from edison.core.composition.transformers.functions_loader import load_functions


def test_function_transformer_executes_core_function(tmp_path: Path) -> None:
    # Ensure core functions are loaded (tasks_states)
    load_functions(project_root=None, active_packs=[])

    engine = TemplateEngine(config={}, packs=[], project_root=tmp_path)
    content, _ = engine.process("{{function:tasks_states()}}", entity_name="test")

    assert "- todo" in content
    assert "- done" in content
