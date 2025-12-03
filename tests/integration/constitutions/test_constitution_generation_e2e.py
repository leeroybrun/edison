from __future__ import annotations

import os
import re
from pathlib import Path

import yaml

from edison.core.rules import get_rules_for_role, load_bundled_rules
from edison.core.config import ConfigManager
from edison.core.composition import collect_validators
from edison.core.utils.paths.project import get_project_config_dir
from edison.core.utils.subprocess import run_with_timeout


def _write_minimal_validator_templates(root: Path) -> None:
    """Provide bare validator templates so compose --all can run end-to-end."""

    cfg_mgr = ConfigManager(root)
    config = cfg_mgr.load_config(validate=False)

    project_dir = get_project_config_dir(root)
    packs_dir = root / ".edison" / "packs"
    roster = collect_validators(
        config,
        project_root=root,
        project_dir=project_dir,
        packs_dir=packs_dir,
        active_packs=(config.get("packs", {}) or {}).get("active", []) or [],
    )

    # Create project-level validators (NOT .edison/core/ - that is legacy)
    # Core validators come from bundled edison.data, project adds custom validators
    validators_dir = root / ".edison" / "validators" / "global"
    validators_dir.mkdir(parents=True, exist_ok=True)

    validator_ids = set()
    for bucket in ("global", "critical", "specialized"):
        for entry in roster.get(bucket, []) or []:
            if isinstance(entry, dict) and entry.get("id"):
                validator_ids.add(str(entry["id"]))
            elif isinstance(entry, str):
                validator_ids.add(entry)

    for vid in sorted(validator_ids):
        role = vid.split("-", 1)[0]
        path = validators_dir / f"{role}.md"
        path.write_text(
            f"# {role.title()} Validator\n\nBase template for {vid}.\n",
            encoding="utf-8",
        )


class TestAgentsConstitutionGeneration:
    def test_compose_all_generates_agents_constitution(self, isolated_project_env: Path) -> None:
        root = isolated_project_env

        _write_minimal_validator_templates(root)

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
        # Support new schema: constitutions.<role>.mandatoryReads
        agents_config = constitution_cfg.get("constitutions", {}).get("agents", {})
        mandatory_reads = agents_config.get("mandatoryReads", [])
        assert mandatory_reads, "constitution.yaml must define constitutions.agents.mandatoryReads"

        for entry in mandatory_reads:
            expected_line = f"- {entry['path']}: {entry['purpose']}"
            assert expected_line in content, f"Missing mandatory read: {expected_line}"

        agent_rule_ids = {rule["id"] for rule in get_rules_for_role("agent")}
        assert agent_rule_ids, "Rules registry should expose agent rules"

        found_rule_ids = {
            match.group(1)
            for match in re.finditer(r"^###\s+([^:]+):", content, flags=re.MULTILINE)
        }
        assert found_rule_ids, "Generated constitution should list agent-applicable rules"
        assert found_rule_ids.issubset(agent_rule_ids)

        all_rules = load_bundled_rules()
        non_agent_rule = next(
            rule for rule in all_rules if "agent" not in (rule.get("applies_to") or [])
        )
        assert non_agent_rule["id"] not in content, "Non-agent rules must be excluded"
