import pytest
from pathlib import Path


class TestZenWorkflowLoop:
    def test_all_generic_prompts_have_workflow_loop(self):
        """Test that all generic role prompts include workflow loop instructions."""
        repo_root = Path.cwd()
        zen_prompts_dir = (
            repo_root / ".zen" / "conf" / "systemprompts" / "clink" / "project"
        )

        if not zen_prompts_dir.exists():
            pytest.skip("Zen prompts directory not found")

        prompts = [
            "codex.txt",
            "claude.txt",
            "gemini.txt",
        ]

        for prompt_file in prompts:
            prompt_path = zen_prompts_dir / prompt_file

            if not prompt_path.exists():
                pytest.fail(f"Missing prompt file: {prompt_file}")

            content = prompt_path.read_text()

            # Verify workflow loop section exists
            assert "## Edison Workflow Loop" in content, (
                f"{prompt_file} missing workflow loop section"
            )

            # Verify key components
            assert "scripts/session next" in content, (
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

    def test_workflow_loop_emphasizes_rules_first(self):
        """Test that workflow loop emphasizes reading rules BEFORE actions."""
        repo_root = Path.cwd()
        zen_prompts_dir = (
            repo_root / ".zen" / "conf" / "systemprompts" / "clink" / "project"
        )

        if not zen_prompts_dir.exists():
            pytest.skip("Zen prompts directory not found")

        codex_prompt = zen_prompts_dir / "codex.txt"

        if not codex_prompt.exists():
            pytest.skip("codex.txt not found")

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
