from __future__ import annotations

import os
import re
from pathlib import Path
from typing import List

import pytest
import yaml
from edison.data import get_data_path

pytestmark = pytest.mark.skip(reason="Documentation not yet written - guide files moved/pending")

# These files don't exist in bundled data yet - when they're added, update these paths
GUIDE_PATH = get_data_path("docs", "guides/session.md")  # Will be bundled
STATE_MACHINE_PATH = get_data_path("docs", "architecture/state-machine.md")  # Will be bundled
START_SESSION_PATH = get_data_path("start", "START_NEW_SESSION.md")  # Already bundled


def _read_file() -> List[str]:
    if not GUIDE_PATH.exists():
        return []
    return GUIDE_PATH.read_text(encoding='utf-8').splitlines()


def test_session_guide_exists():
    assert GUIDE_PATH.exists(), f"Missing guide at {GUIDE_PATH}"


def test_session_guide_length():
    lines = _read_file()
    assert len(lines) >= 500, f"Guide too short: {len(lines)} lines (<500)"


def test_required_sections_present():
    text = "\n".join(_read_file())
    # Required section headings by exact title (12 minimum; we enforce all 13 requested)
    required = [
        '## Session Overview',
        '## Session Structure',
        '## Session Lifecycle',
        '## Session Creation',
        '## Session Isolation',
        '## Active Session Management',
        '## Session Timeout and Recovery',
        '## Session Closing',
        '## Session Validation',
        '## Multi-Session Workflows',
        '## Session Configuration',
        '## Common Patterns',
        '## Troubleshooting',
    ]
    missing = [h for h in required if h not in text]
    assert not missing, f"Missing required sections: {missing}"


def test_lifecycle_diagram_included():
    text = "\n".join(_read_file())
    has_mermaid = '```mermaid' in text and ('flowchart' in text or 'graph' in text)
    has_ascii = any(sym in text for sym in ['┌', '└', '│']) and ('ACTIVE' in text or 'Active' in text)
    has_arrows = '->' in text or '→' in text
    assert (has_mermaid or has_ascii) and has_arrows, "Lifecycle diagram missing (expected mermaid and/or ASCII with arrows)"


def _extract_yaml_blocks(text: str) -> List[str]:
    blocks: List[str] = []
    pattern = re.compile(r"```(?:yaml|yml)\n(.*?)```", re.DOTALL | re.IGNORECASE)
    for m in pattern.finditer(text):
        blocks.append(m.group(1))
    return blocks


def test_configuration_examples_valid_yaml():
    text = "\n".join(_read_file())
    blocks = _extract_yaml_blocks(text)
    assert blocks, "No YAML configuration examples found"
    loaded = [yaml.safe_load(b) for b in blocks]
    # At least one example should contain top-level 'session'
    assert any(isinstance(d, dict) and 'session' in d for d in loaded), "At least one YAML example must define 'session' key"


def test_cross_references_valid():
    text = "\n".join(_read_file())
    assert STATE_MACHINE_PATH.exists(), f"Missing reference file: {STATE_MACHINE_PATH}"
    assert START_SESSION_PATH.exists(), f"Missing reference file: {START_SESSION_PATH}"

    # Check that the guide links to both files using markdown links
    assert str(STATE_MACHINE_PATH) in text, "Guide must link to state-machine.md by path"
    assert str(START_SESSION_PATH) in text, "Guide must link to START.SESSION.md by path"


def test_project_agnostic_language():
    text = "\n".join(_read_file())
    assert '{PROJECT_NAME}' in text, "Guide must use {PROJECT_NAME} placeholder"
    lowered = text.lower()
    assert 'project' not in lowered, "Guide must be project-agnostic (no 'project' mentions)"


def test_timeout_documentation_complete():
    text = "\n".join(_read_file()).lower()
    # Expect mentions of timeout, threshold (minutes/hours), and detection/check interval
    assert 'timeout' in text, "Must document session timeout"
    assert any(k in text for k in ['minutes', 'hours']), "Timeout must discuss minutes/hours"
    assert any(k in text for k in ['threshold', 'threshold_minutes', 'threshold_hours']), "Timeout threshold not documented"
    assert any(k in text for k in ['check interval', 'checkinterval', 'stale_check_interval']), "Timeout check interval not documented"


def test_recovery_workflow_documented():
    text = "\n".join(_read_file())
    t = text.lower()
    assert 'recovery' in t, "Recovery state must be documented"
    assert any(k in t for k in ['resume', 'resuming', 'auto-resume', 'manual resume']), "Must explain how to resume from recovery"


def test_examples_are_present_and_clear():
    # Heuristic: at least 5 distinct example headings/labels
    lines = _read_file()
    example_like = [ln for ln in lines if re.search(r"^(###|####)?\s*(Example|Workflow Example|Pattern)\b", ln, re.IGNORECASE)]
    assert len(example_like) >= 5, f"Expected >=5 example/pattern headings, found {len(example_like)}"

