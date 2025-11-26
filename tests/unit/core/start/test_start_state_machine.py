from pathlib import Path


START_FILES = [
    Path("src/edison/data/start/START_NEW_SESSION.md"),
    Path("src/edison/data/start/START_RESUME_SESSION.md"),
    Path("src/edison/data/start/START_VALIDATE_SESSION.md"),
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_start_prompts_include_state_machine_documentation():
    required_snippets = (
        "Session State Machine",
        "NEW → WIP → READY → VALIDATING → COMPLETE",
        "Valid state transitions",
        "Transition triggers",
    )
    diagram_markers = ("```mermaid", "ASCII diagram", "State diagram")

    for path in START_FILES:
        content = read_text(path)
        for snippet in required_snippets:
            assert snippet in content, f"{path.name} missing '{snippet}'"
        assert any(marker in content for marker in diagram_markers), (
            f"{path.name} missing state diagram representation"
        )
