#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Tuple

from edison.core.adapters import ClaudeSync
from edison.core.composition import CompositionEngine
from edison.core.config import ConfigManager
from edison.core.utils.subprocess import run_with_timeout


def _get_repo_root() -> Path:
    """Return the outermost git repository root (project root)."""
    current = Path(__file__).resolve()
    last_git_root: Path | None = None
    while current != current.parent:
        if (current / ".git").exists():
            last_git_root = current
        current = current.parent
    if last_git_root is None:
        raise RuntimeError("Could not find repository root")
    return last_git_root


REPO_ROOT = _get_repo_root()
SCRIPTS_ROOT = REPO_ROOT / ".edison" / "core" / "scripts"


def _run_compose(*args: str) -> Tuple[int, str, str]:
    """Invoke the Edison compose CLI with a controlled environment."""
    env = os.environ.copy()
    # Ensure composition resolves paths relative to the real project root
    env["AGENTS_PROJECT_ROOT"] = str(REPO_ROOT)
    proc = run_with_timeout(
        [str(SCRIPTS_ROOT / "prompts" / "compose"), *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _split_frontmatter(text: str) -> tuple[str, str]:
    """Split a Claude agent document into (header, body)."""
    lines = text.splitlines()
    sep_index = None
    for i, line in enumerate(lines):
        if line.strip() == "---":
            sep_index = i
            break
    if sep_index is None:
        raise AssertionError("Missing frontmatter separator '---' in Claude agent document")
    header = "\n".join(lines[:sep_index]).strip()
    body = "\n".join(lines[sep_index + 1 :]).strip()
    return header, body


def test_compose_help_exposes_claude_flags() -> None:
    rc, out, err = _run_compose("--help")
    assert rc == 0, f"--help failed:\nSTDOUT:\n{out}\nSTDERR:\n{err}"
    # Core Claude integration flags should be visible to callers
    assert "--claude" in out
    assert "--sync-claude" in out
    assert "--sync-claude-agents" in out


def test_claude_agent_sync_round_trip() -> None:
    # 1) Ensure Edison has composed agents into .agents/_generated/agents
    rc, out, err = _run_compose("--agents")
    assert rc == 0, f"--agents failed:\nSTDOUT:\n{out}\nSTDERR:\n{err}"

    generated_dir = REPO_ROOT / ".agents" / "_generated" / "agents"
    assert generated_dir.is_dir(), f"Missing generated agents dir: {generated_dir}"
    src_agents = sorted(generated_dir.glob("*.md"))
    assert src_agents, "No generated agents found under .agents/_generated/agents"

    # 2) Sync composed agents into Claude Code layout
    rc, out, err = _run_compose("--sync-claude-agents")
    assert rc == 0, f"--sync-claude-agents failed:\nSTDOUT:\n{out}\nSTDERR:\n{err}"

    claude_agents_dir = REPO_ROOT / ".claude" / "agents"
    assert claude_agents_dir.is_dir(), f"Missing Claude agents dir: {claude_agents_dir}"

    # 3) Verify per-agent mapping and body preservation
    for src in src_agents:
        dest = claude_agents_dir / src.name
        assert dest.exists(), f"Missing Claude agent for {src.stem}: {dest}"

        src_text = src.read_text(encoding="utf-8").strip()
        dest_text = dest.read_text(encoding="utf-8")

        header, body = _split_frontmatter(dest_text)
        header_lines = [ln.strip() for ln in header.splitlines() if ln.strip()]

        # Basic frontmatter invariants
        assert any(ln.startswith("name:") for ln in header_lines), f"Missing name field in {dest}"
        assert any(
            ln.startswith("description:") for ln in header_lines
        ), f"Missing description field in {dest}"
        assert any(ln.startswith("model:") for ln in header_lines), f"Missing model field in {dest}"

        # Body should match the Edison-composed agent exactly (modulo surrounding whitespace)
        assert (
            body == src_text
        ), f"Claude agent body mismatch for {src.stem}: expected Edison body to be preserved"


def test_compose_claude_agents_api_surface() -> None:
    """CompositionEngine should expose a dedicated Claude agent composer."""
    cfg = ConfigManager(REPO_ROOT).load_config(validate=False)
    engine = CompositionEngine(cfg, repo_root=REPO_ROOT)
    out_dir = REPO_ROOT / ".agents" / "_generated" / "agents"

    result = engine.compose_claude_agents(out_dir)  # type: ignore[attr-defined]
    # Expect mapping of agent name → generated path
    assert isinstance(result, dict) and result, "compose_claude_agents should return non-empty mapping"
    for name, path in result.items():
        assert isinstance(name, str) and name
        assert isinstance(path, Path) and path.is_file()
        assert path.parent == out_dir


def test_claude_agent_schema_valid_for_all_agents() -> None:
    # Ensure latest agents + Claude sync are in place
    rc, out, err = _run_compose("--agents")
    assert rc == 0, f"--agents failed:\nSTDOUT:\n{out}\nSTDERR:\n{err}"

    generated_dir = REPO_ROOT / ".agents" / "_generated" / "agents"
    assert generated_dir.is_dir(), f"Missing generated agents dir: {generated_dir}"

    adapter = ClaudeSync(repo_root=REPO_ROOT)

    # Every composed agent should yield a schema-valid payload
    for src in sorted(generated_dir.glob("*.md")):
        text = src.read_text(encoding="utf-8")
        sections = adapter._parse_edison_agent(text, fallback_name=src.stem)
        # Role must be non-empty to satisfy schema expectations
        assert sections.role.strip(), f"Empty Role section in Edison agent: {src}"

        payload = adapter._build_agent_payload(sections, config={})
        # Will raise ClaudeAdapterError if schema validation fails and jsonschema is available
        adapter._validate_agent_payload(src.stem, payload)


def test_sync_claude_generates_config_and_orchestrator() -> None:
    # Ensure orchestrator and agents are composed
    rc, out, err = _run_compose("--orchestrator")
    assert rc == 0, f"--orchestrator failed:\nSTDOUT:\n{out}\nSTDERR:\n{err}"
    rc, out, err = _run_compose("--agents")
    assert rc == 0, f"--agents failed:\nSTDOUT:\n{out}\nSTDERR:\n{err}"

    # Run full Claude sync (agents + orchestrator guide + config.json)
    rc, out, err = _run_compose("--sync-claude")
    assert rc == 0, f"--sync-claude failed:\nSTDOUT:\n{out}\nSTDERR:\n{err}"

    claude_dir = REPO_ROOT / ".claude"
    claude_md = claude_dir / "CLAUDE.md"
    config_path = claude_dir / "config.json"

    assert claude_md.is_file(), f"Expected orchestrator file at {claude_md}"
    assert config_path.is_file(), f"Expected Claude config at {config_path}"

    cfg = json.loads(config_path.read_text(encoding="utf-8") or "{}")
    assert cfg.get("claudeDir") == ".claude"
    assert isinstance(cfg.get("agents"), dict)
    # Default agent should be present and non-empty
    default_agent = cfg.get("defaultAgent")
    assert isinstance(default_agent, str) and default_agent