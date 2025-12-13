from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from edison.core.rules import RulesRegistry, get_rules_for_role
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
        # v2.0.0: mandatoryReads is intentionally empty because critical content is embedded.
        agents_config = constitution_cfg.get("constitutions", {}).get("agents", {})
        mandatory_reads = agents_config.get("mandatoryReads", [])
        assert mandatory_reads == [], "v2.0.0 should keep mandatoryReads empty (embedded constitution)"

        # Embedded base constitution content should be present
        assert "## TDD Principles (All Roles)" in content
        # Guardrail: composed constitutions must not duplicate sections due to
        # wrapper headings + include-section headings.
        assert content.count("## TDD Execution (Agents)") == 1, (
            "Generated AGENTS.md must not duplicate 'TDD Execution (Agents)'. "
            "This usually indicates a double-loaded heading in source templates."
        )

        # Optional reads should still render (on-demand deep dive)
        optional_reads = agents_config.get("optionalReads", [])
        assert optional_reads, "constitution.yaml must define constitutions.agents.optionalReads"
        for entry in optional_reads:
            expected_line = f"- {entry['path']}: {entry['purpose']}"
            assert expected_line in content, f"Missing optional read: {expected_line}"

        agent_rule_ids = {rule["id"] for rule in get_rules_for_role("agent")}
        assert agent_rule_ids, "Rules registry should expose agent rules"

        # Extract only rule headings of the form: "### RULE.SOMETHING:"
        # (avoid accidentally capturing other "### <Heading>:" sections).
        found_rule_ids = {
            match.group(1)
            for match in re.finditer(
                r"^###\s+(RULE\.[^:\n]+):", content, flags=re.MULTILINE
            )
        }
        assert found_rule_ids, "Generated constitution should list agent-applicable rules"
        assert found_rule_ids.issubset(agent_rule_ids)

        all_rules = RulesRegistry(project_root=root).load_core_registry().get("rules", [])
        non_agent_rule = next(
            rule for rule in all_rules if "agent" not in (rule.get("applies_to") or [])
        )
        assert non_agent_rule["id"] not in content, "Non-agent rules must be excluded"
