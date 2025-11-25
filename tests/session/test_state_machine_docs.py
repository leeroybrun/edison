"""State machine documentation and visualization tests."""
from __future__ import annotations

from pathlib import Path

from edison.core.state_machine_docs import ( 
    generate_transition_matrix,
    generate_mermaid_diagram,
    write_state_machine_docs,
)


def test_generate_transition_matrix_contains_core_transitions() -> None:
    matrix = generate_transition_matrix()
    # Basic sanity checks for known transitions
    assert "| task | todo | wip |" in matrix
    assert "| task | wip | done |" in matrix
    assert "| session | active | closing |" in matrix


def test_generate_mermaid_diagram_has_expected_header_and_edges() -> None:
    diagram = generate_mermaid_diagram()
    assert "stateDiagram-v2" in diagram
    assert "todo --> wip" in diagram
    assert "wip --> done" in diagram


def test_write_state_machine_docs_writes_markdown(tmp_path: Path, monkeypatch) -> None:
    # Force project root to a temporary directory to avoid modifying real docs.
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    # Seed a minimal defaults.yaml with task/qa state machine.
    core_dir = tmp_path / ".edison" / "core"
    core_dir.mkdir(parents=True, exist_ok=True)
    defaults = """
statemachine:
  task:
    states:
      todo:
        allowed_transitions: [{to: wip}]
      wip:
        allowed_transitions: [{to: done}]
      done:
        allowed_transitions: [{to: validated}, {to: wip}]
  qa:
    states:
      waiting:
        allowed_transitions: [{to: todo}]
      todo:
        allowed_transitions: [{to: wip}]
      wip:
        allowed_transitions: [{to: done}]
      done:
        allowed_transitions: [{to: validated}, {to: wip}]
"""
    (core_dir / "defaults.yaml").write_text(defaults, encoding="utf-8")

    out_path = write_state_machine_docs()

    assert out_path.exists()
    text = out_path.read_text(encoding="utf-8")
    assert "# Edison State Machine" in text
    assert "## Transition Matrix" in text
    assert "```mermaid" in text
