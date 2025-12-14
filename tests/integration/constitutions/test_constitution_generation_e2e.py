from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from edison.core.rules import get_rules_for_role, compose_rules
from edison.core.utils.subprocess import run_with_timeout


class TestAgentsConstitutionGeneration:
    def test_compose_all_generates_agents_constitution(self, isolated_project_env: Path) -> None:
        root = isolated_project_env

        env = os.environ.copy()
        env["AGENTS_PROJECT_ROOT"] = str(root)

        proc = run_with_timeout(
            ["uv", "run", "edison", "compose", "all"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
        )

        assert proc.returncode == 0, f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"

        out_file = root / ".edison" / "_generated" / "constitutions" / "AGENTS.md"
        assert out_file.exists(), "compose --all should emit constitutions/AGENTS.md"

        content = out_file.read_text(encoding="utf-8")

        assert "<!-- Role: AGENT -->" in content

        # Read constitution config from bundled data (not project config)
        from edison.data import get_data_path
        constitution_cfg_path = get_data_path("config/constitution.yaml")
        constitution_cfg = yaml.safe_load(
            constitution_cfg_path.read_text(encoding="utf-8")
        )

        # Test conditional rendering of mandatoryReads
        agents_config = constitution_cfg.get("constitutions", {}).get("agents", {})
        mandatory_reads = agents_config.get("mandatoryReads", [])

        if mandatory_reads:
            # If mandatoryReads is populated, verify they appear
            assert "## Mandatory Preloads" in content
            for entry in mandatory_reads:
                expected_line = f"- {entry['path']}: {entry['purpose']}"
                assert expected_line in content, f"Missing mandatory read: {expected_line}"
        else:
            # If mandatoryReads is empty (v2.0 default), verify section is hidden
            assert "## Mandatory Preloads" not in content, (
                "mandatoryReads is empty but '## Mandatory Preloads' section still appears. "
                "The conditional {{if:config(...)}} should hide this section."
            )

        # Verify embedded Core Principles are present (v2.0 architecture)
        assert "## TDD Principles (All Roles)" in content, "Core TDD principles should be embedded"
        assert "## NO MOCKS Philosophy (All Roles)" in content, "Core NO MOCKS philosophy should be embedded"

        # Test optional reads - they should render if populated
        optional_reads = agents_config.get("optionalReads", [])
        if optional_reads:
            assert "## Optional References" in content
            for entry in optional_reads:
                expected_line = f"- {entry['path']}: {entry['purpose']}"
                assert expected_line in content, f"Missing optional read: {expected_line}"

        # Verify rules are rendered
        agent_rule_ids = {rule["id"] for rule in get_rules_for_role("agent")}
        assert agent_rule_ids, "Rules registry should expose agent rules"

        # Match rule IDs in format: ### RULE.XXX.YYY: Name
        found_rule_ids = {
            match.group(1)
            for match in re.finditer(r"^###\s+(RULE\.[A-Z0-9_.]+):", content, flags=re.MULTILINE)
        }
        assert found_rule_ids, "Generated constitution should list agent-applicable rules"
        assert found_rule_ids.issubset(agent_rule_ids)

        # Verify non-agent rules are excluded
        all_rules = compose_rules().get("rules", {})
        non_agent_rule_ids = [
            rule_id for rule_id, rule_data in all_rules.items()
            if isinstance(rule_data, dict) and "agent" not in (rule_data.get("applies_to") or [])
        ]
        if non_agent_rule_ids:
            non_agent_rule_id = non_agent_rule_ids[0]
            assert non_agent_rule_id not in content, f"Non-agent rule {non_agent_rule_id} must be excluded"
