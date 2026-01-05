from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.qa.engines.base import EngineConfig
from edison.core.qa.engines.cli import CLIEngine
from edison.core.registries.validators import ValidatorMetadata


@pytest.mark.qa
def test_cli_engine_stdin_prompt_without_sentinel_uses_stdin_not_prompt_path(tmp_path: Path) -> None:
    prompt_file = tmp_path / "prompt.md"
    prompt_file.write_text("BASE_PROMPT_ONLY", encoding="utf-8")

    cfg = EngineConfig.from_dict(
        "stdin-cat",
        {
            "type": "cli",
            "command": "bash",
            "pre_flags": ["-lc", "cat"],
            "output_flags": [],
            "read_only_flags": [],
            "prompt_mode": "stdin",
            # Intentionally omit stdin_prompt_arg: tools like `claude -p` can read prompt from stdin
            # without requiring a sentinel arg like "-" (unlike some other CLIs).
            "response_parser": "plain_text",
        },
    )
    engine = CLIEngine(cfg, project_root=tmp_path)
    validator = ValidatorMetadata(
        id="stdin-cat-validator",
        name="stdin-cat",
        engine="stdin-cat",
        wave="test",
        prompt=str(prompt_file),
    )

    result = engine.run(
        validator,
        task_id="T-1",
        session_id="S-1",
        worktree_path=tmp_path,
        round_num=None,
        evidence_service=None,
    )

    # When stdin prompt is correctly wired, cat will echo the full rendered prompt (prelude + base),
    # which starts with the standard prelude header.
    assert "# Edison Validator Run (Auto)" in (result.raw_output or "")

