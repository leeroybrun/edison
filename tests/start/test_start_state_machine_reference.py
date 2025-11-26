from __future__ import annotations

from pathlib import Path


def test_start_prompts_reference_generated_state_machine() -> None:
    start_dir = Path("src/edison/data/start")
    start_files = sorted(start_dir.glob("START_*.md"))

    assert start_files, "Expected START_*.md files to exist"

    for path in start_files:
        text = path.read_text(encoding="utf-8")

        assert "STATE_MACHINE.md" in text, (
            f"{path.name} must reference generated STATE_MACHINE.md instead of embedding states"
        )
        assert "States: " not in text, f"{path.name} should not hardcode state lists"
        assert "stateDiagram" not in text, f"{path.name} should not embed mermaid diagrams"
        assert "```mermaid" not in text, f"{path.name} should not embed mermaid diagrams"
