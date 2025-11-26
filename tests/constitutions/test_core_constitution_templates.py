"""Validation for core constitution base templates.

These tests enforce the contract defined in the Edison Migration Plan
task T-001. They ensure the core Handlebars templates exist and contain
the required sections/placeholders for orchestrators, agents, and
validators.
"""

from __future__ import annotations

from pathlib import Path
import pytest

from tests.conftest import REPO_ROOT


TEMPLATES = [
    {
        "role": "orchestrator",
        "role_label": "ORCHESTRATOR",
        "path": REPO_ROOT / "src/edison/core/constitutions/orchestrator-base.md",
        "constitution_path": ".edison/_generated/constitutions/ORCHESTRATORS.md",
        "mandatory_block": "{{#each mandatoryReads.orchestrator}}",
        "rules_block": "{{#each rules.orchestrator}}",
        "workflow_section": "Session Workflow",
        "workflow_ref": "guidelines/orchestrators/SESSION_WORKFLOW.md",
        "reread_bullets": [
            "- At the start of every new session",
            "- After any context compaction",
            "- When instructed by the user",
        ],
        "extra_blocks": ["{{#each delegationRules}}"],
        "header_reread": "<!-- RE-READ this file on each new session or compaction -->",
        "heading": "# Orchestrator Constitution",
    },
    {
        "role": "agents",
        "role_label": "AGENT",
        "path": REPO_ROOT / "src/edison/core/constitutions/agents-base.md",
        "constitution_path": ".edison/_generated/constitutions/AGENTS.md",
        "mandatory_block": "{{#each mandatoryReads.agents}}",
        "rules_block": "{{#each rules.agent}}",
        "workflow_section": "Workflow Requirements",
        "workflow_ref": "MANDATORY_WORKFLOW.md",
        "reread_bullets": [
            "- At the start of every task assignment",
            "- After any context compaction",
            "- When instructed by the orchestrator",
        ],
        "extra_blocks": [],
        "header_reread": "<!-- RE-READ this file on each new session or compaction -->",
        "heading": "# Agent Constitution",
    },
    {
        "role": "validators",
        "role_label": "VALIDATOR",
        "path": REPO_ROOT / "src/edison/core/constitutions/validators-base.md",
        "constitution_path": ".edison/_generated/constitutions/VALIDATORS.md",
        "mandatory_block": "{{#each mandatoryReads.validators}}",
        "rules_block": "{{#each rules.validator}}",
        "workflow_section": "Validation Workflow",
        "workflow_ref": "OUTPUT_FORMAT.md",
        "reread_bullets": [
            "- At the start of every validation assignment",
            "- After any context compaction",
        ],
        "extra_blocks": [],
        "header_reread": "<!-- RE-READ this file on each new session or compaction -->",
        "heading": "# Validator Constitution",
    },
]


COMMON_HEADER_FIELDS = [
    "<!-- GENERATED FILE - DO NOT EDIT DIRECTLY -->",
    "<!-- Source: {{source_layers}} -->",
    "<!-- Regenerate: edison compose --all -->",
]


def _require_block_closed(content: str, open_tag: str) -> None:
    start = content.find(open_tag)
    assert start != -1, f"Missing Handlebars block: {open_tag}"

    close_pos = content.find("{{/each}}", start)
    assert close_pos != -1, f"Block not closed for: {open_tag}"


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t["role"])
def test_constitution_template_exists_with_header(template: dict) -> None:
    path: Path = template["path"]

    assert path.is_file(), f"Template missing: {path}"

    content = path.read_text(encoding="utf-8")

    for field in COMMON_HEADER_FIELDS:
        assert field in content, f"Header field missing in {path.name}: {field}"

    assert f"<!-- Role: {template['role_label']} -->" in content
    assert f"<!-- Constitution: {template['constitution_path']} -->" in content
    assert template["header_reread"] in content


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t["role"])
def test_constitution_template_core_sections(template: dict) -> None:
    path: Path = template["path"]
    content = path.read_text(encoding="utf-8")

    assert template["heading"] in content
    assert template["constitution_path"] in content

    for bullet in template["reread_bullets"]:
        assert bullet in content

    assert template["mandatory_block"] in content
    assert template["rules_block"] in content

    _require_block_closed(content, template["mandatory_block"])
    _require_block_closed(content, template["rules_block"])
    for extra in template["extra_blocks"]:
        _require_block_closed(content, extra)

    assert template["workflow_section"] in content
    assert template["workflow_ref"] in content


def test_constitution_templates_directory_exists() -> None:
    base_dir = REPO_ROOT / "src/edison/core/constitutions"
    assert base_dir.is_dir(), "Missing constitutions directory"

