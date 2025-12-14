from __future__ import annotations

import os
from pathlib import Path

from edison.core.utils.subprocess import run_with_timeout


def _assert_no_consecutive_duplicate_headings(*, content: str, file_path: Path) -> None:
    """Guardrail: composition must not emit duplicated wrapper headings.

    This catches a common failure mode where a template adds a heading and then
    includes a section that starts with the same heading, producing consecutive
    duplicate headings (usually with no content between).
    """

    def is_heading(line: str) -> bool:
        stripped = line.strip()
        return stripped.startswith("#") and stripped.lstrip("#").startswith(" ")

    lines = content.splitlines()

    def next_non_empty_idx(start: int) -> int | None:
        for i in range(start, len(lines)):
            if lines[i].strip():
                return i
        return None

    i = 0
    while True:
        i = next_non_empty_idx(i)
        if i is None:
            return

        line = lines[i].strip()
        if not is_heading(line):
            i += 1
            continue

        j = next_non_empty_idx(i + 1)
        if j is None:
            return

        nxt = lines[j].strip()
        if is_heading(nxt) and nxt == line:
            raise AssertionError(
                "Consecutive duplicate heading emitted by composition: "
                f"{file_path}\n\nHeading: {line!r}"
            )

        i = j


class TestAgentPromptGeneration:
    def test_compose_all_claude_sync_has_no_duplicate_headings(
        self, isolated_project_env: Path
    ) -> None:
        root = isolated_project_env

        env = os.environ.copy()
        env["AGENTS_PROJECT_ROOT"] = str(root)

        proc = run_with_timeout(
            ["uv", "run", "edison", "compose", "all", "--claude"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
        )

        assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

        generated_agents_dir = root / ".edison" / "_generated" / "agents"
        claude_agents_dir = root / ".claude" / "agents"

        assert generated_agents_dir.exists(), "compose all must emit _generated/agents"
        assert claude_agents_dir.exists(), "compose all --claude must emit .claude/agents"

        generated_files = sorted(generated_agents_dir.glob("*.md"))
        assert generated_files, "expected at least one composed agent prompt"

        for p in generated_files:
            _assert_no_consecutive_duplicate_headings(
                content=p.read_text(encoding="utf-8"), file_path=p
            )

        claude_files = sorted(claude_agents_dir.glob("*.md"))
        assert claude_files, "expected at least one Claude agent prompt"

        for p in claude_files:
            _assert_no_consecutive_duplicate_headings(
                content=p.read_text(encoding="utf-8"), file_path=p
            )


