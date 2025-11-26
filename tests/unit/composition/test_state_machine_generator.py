from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.composition.state_machine import generate_state_machine_doc


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_state_machine_doc_written_to_generated_dir(isolated_project_env: Path) -> None:
    repo_root = isolated_project_env
    output_path = repo_root / ".edison" / "_generated" / "STATE_MACHINE.md"

    generate_state_machine_doc(output_path, repo_root=repo_root)

    assert output_path.exists(), "STATE_MACHINE.md must be written to .edison/_generated"
    content = _read(output_path)
    assert "AUTO-GENERATED FILE" in content
    assert "# State Machine" in content


def test_generator_uses_yaml_config_not_hardcoded(isolated_project_env: Path) -> None:
    repo_root = isolated_project_env
    config_dir = repo_root / ".edison" / "core" / "config"

    # Override the statemachine config with unique states/guards to prove dynamic loading
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "state-machine.yaml").write_text(
        """
statemachine:
  task:
    states:
      plan:
        description: "Planning work"
        initial: true
        allowed_transitions:
          - to: build
            guard: ready_to_build
      build:
        description: "Building solution"
        allowed_transitions:
          - to: review
            guard: ready_for_review
  qa:
    states:
      triage:
        description: "Queued for QA"
        initial: true
        allowed_transitions:
          - to: verify
            guard: ready_to_verify
      verify:
        description: "Verifying"
        allowed_transitions:
          - to: triage
            guard: needs_more_info
  session:
    states:
      spinup:
        description: "Preparing session"
        allowed_transitions:
          - to: active
            guard: can_activate
      active:
        description: "Active session"
        initial: true
        allowed_transitions:
          - to: closing
            guard: ready_to_close
      closing:
        description: "Closing session"
        allowed_transitions:
          - to: archived
            guard: finalized
      archived:
        description: "Archived"
        final: true
        allowed_transitions: []
""",
        encoding="utf-8",
    )

    output_path = repo_root / ".edison" / "_generated" / "STATE_MACHINE.md"
    generate_state_machine_doc(output_path, repo_root=repo_root)

    content = _read(output_path)

    # Prove dynamic generation: unique states and guards must appear
    assert "plan" in content and "build" in content
    assert "ready_to_build" in content
    assert "triage" in content and "verify" in content
    assert "spinup" in content and "closing" in content
    # Avoid legacy hardcoding of default states
    assert "todo" not in content.lower(), "Generator must rely on YAML, not baked-in defaults"
