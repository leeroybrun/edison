from __future__ import annotations

from pathlib import Path
import os

from edison.core.utils.subprocess import run_with_timeout


class TestZenWorkflowLoop:
    def test_all_generic_prompts_have_workflow_loop(self, isolated_project_env: Path):
        """Test that all generic role prompts include workflow loop instructions."""
        repo_root = isolated_project_env

        env = os.environ.copy()
        env["AGENTS_PROJECT_ROOT"] = str(repo_root)

        result = run_with_timeout(
            ["uv", "run", "edison", "compose", "all"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0, (
            f"compose failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

        zen_prompts_dir = (
            repo_root / ".zen" / "conf" / "systemprompts" / "clink" / "project"
        )
        assert zen_prompts_dir.exists(), "Zen prompts directory not found after compose"

        prompts = [
            "codex.txt",
            "claude.txt",
            "gemini.txt",
        ]

        for prompt_file in prompts:
            prompt_path = zen_prompts_dir / prompt_file

            assert prompt_path.exists(), f"Missing prompt file: {prompt_file}"

            content = prompt_path.read_text()

            # Verify workflow loop section exists
            assert "## Edison Workflow Loop" in content, (
                f"{prompt_file} missing workflow loop section"
            )

            # Verify key components
            assert "edison session next" in content, (
                f"{prompt_file} missing session next command"
            )
            assert "APPLICABLE RULES" in content, (
                f"{prompt_file} missing rules section"
            )
            assert "RECOMMENDED ACTIONS" in content, (
                f"{prompt_file} missing actions section"
            )
            assert "DELEGATION HINT" in content, (
                f"{prompt_file} missing delegation section"
            )
            assert "VALIDATORS" in content, (
                f"{prompt_file} missing validators section"
            )
            assert "read first" in content.lower(), (
                f"{prompt_file} missing emphasis on reading rules first"
            )

    def test_workflow_loop_emphasizes_rules_first(self, isolated_project_env: Path):
        """Test that workflow loop emphasizes reading rules BEFORE actions."""
        repo_root = isolated_project_env

        env = os.environ.copy()
        env["AGENTS_PROJECT_ROOT"] = str(repo_root)

        result = run_with_timeout(
            ["uv", "run", "edison", "compose", "all"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0, (
            f"compose failed with exit code {result.returncode}\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

        zen_prompts_dir = (
            repo_root / ".zen" / "conf" / "systemprompts" / "clink" / "project"
        )

        assert zen_prompts_dir.exists(), "Zen prompts directory not found after compose"

        codex_prompt = zen_prompts_dir / "codex.txt"

        assert codex_prompt.exists(), "codex.txt not found after compose"

        content = codex_prompt.read_text()

        # Find workflow loop section
        workflow_section_start = content.find("## Edison Workflow Loop")
        assert workflow_section_start > 0

        workflow_section = content[workflow_section_start:]

        # Verify rules come BEFORE actions
        rules_position = workflow_section.find("APPLICABLE RULES")
        actions_position = workflow_section.find("RECOMMENDED ACTIONS")

        assert rules_position < actions_position, (
            "Rules should be listed BEFORE actions in workflow loop"
        )

        # Verify "FIRST" emphasis
        rules_line = workflow_section[rules_position : rules_position + 200]
        assert "FIRST" in rules_line.upper(), (
            "Rules section should emphasize reading FIRST"
        )
