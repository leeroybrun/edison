from __future__ import annotations

import json
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[4]
PRE_EDISON_AGENTS_ROOT = (
    REPO_ROOT
    / ".project"
    / "qa"
    / "archive"
    / "agents-pre-cleanup-20251118-093031"
    / ".agents"
)


def test_pre_edison_agents_have_core_and_claude_equivalents() -> None:
    """Every pre‑Edison agent role must have Edison core + Claude equivalents."""
    pre_agents_dir = PRE_EDISON_AGENTS_ROOT / "agents"
    assert pre_agents_dir.is_dir(), f"Missing pre‑Edison agents dir at {pre_agents_dir}"

    pre_roles = {p.stem for p in pre_agents_dir.glob("*.md")}
    assert pre_roles, "No pre‑Edison agent role files found"

    for role in sorted(pre_roles):
        core_path = REPO_ROOT / ".edison" / "core" / "agents" / f"{role}-core.md"
        claude_path = REPO_ROOT / ".claude" / "agents" / f"{role}.md"
        assert core_path.is_file(), f"Missing Edison core agent for role '{role}': {core_path}"
        assert claude_path.is_file(), f"Missing Claude agent for role '{role}': {claude_path}"


def test_pre_edison_agents_have_zen_role_mappings() -> None:
    """Pre‑Edison roles must be mapped to project Zen roles in .agents/config.yml."""
    cfg = yaml.safe_load((REPO_ROOT / ".agents" / "config.yml").read_text())
    zen_roles_cfg = cfg.get("zen", {}).get("roles", {}) or {}
    zen_role_keys = set(zen_roles_cfg.keys())
    assert zen_role_keys, "Expected non‑empty zen.roles mapping in .agents/config.yml"

    pre_roles = {
        p.stem for p in (PRE_EDISON_AGENTS_ROOT / "agents").glob("*.md")
    }
    expected_project_roles = {f"project-{r}" for r in pre_roles}

    missing = sorted(expected_project_roles - zen_role_keys)
    assert not missing, (
        "Some pre‑Edison agent roles are not mapped to project Zen roles "
        f"in .agents/config.yml: {missing}"
    )


def test_pre_edison_core_guidelines_exist_in_edison_core() -> None:
    """Upper‑case pre‑Edison core guidelines must exist under .edison/core/guidelines."""
    names = [
        "CONTEXT7",
        "DELEGATION",
        "EPHEMERAL_SUMMARIES_POLICY",
        "GIT_WORKFLOW",
        "HONEST_STATUS",
        "QUALITY",
        "SESSION_WORKFLOW",
        "TDD",
        "VALIDATION",
    ]
    for name in names:
        path = REPO_ROOT / ".edison" / "core" / "guidelines" / f"{name}.md"
        assert path.is_file(), f"Missing core guideline migrated from pre‑Edison: {path}"


def test_project_guidelines_preserved_from_pre_edison() -> None:
    """project‑specific guidelines from pre‑Edison must be present in .agents."""
    pre_dir = PRE_EDISON_AGENTS_ROOT / "guidelines"
    cur_dir = REPO_ROOT / ".agents" / "guidelines"
    assert pre_dir.is_dir(), f"Missing pre‑Edison guidelines dir at {pre_dir}"
    assert cur_dir.is_dir(), f"Missing current guidelines dir at {cur_dir}"

    pre_files = sorted(pre_dir.glob("project-*.md"))
    assert pre_files, "No pre‑Edison project guidelines found"

    for pre_path in pre_files:
        cur_path = cur_dir / pre_path.name
        assert cur_path.is_file(), f"Missing migrated project guideline: {cur_path}"
        pre_text = pre_path.read_text(encoding="utf-8")
        cur_text = cur_path.read_text(encoding="utf-8")
        cur_text_norm = cur_text.replace("\r\n", "\n")
        # Every non-empty line from the pre‑Edison guideline must appear
        # somewhere in the current file; the Edison version may insert
        # additional lines but must not drop existing ones.
        missing_lines: list[str] = []
        for line in pre_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped not in cur_text_norm:
                missing_lines.append(stripped)
        assert not missing_lines, (
            "project guideline content from pre‑Edison must be preserved line‑by‑line "
            f"(extensions allowed); missing lines in {pre_path.name}: {missing_lines}"
        )


def test_pre_edison_validator_ids_present_in_core_roster() -> None:
    """Global + critical validator IDs from pre‑Edison must exist in core roster."""
    pre_cfg_path = PRE_EDISON_AGENTS_ROOT / "validators" / "config.json"
    assert pre_cfg_path.is_file(), f"Missing pre‑Edison validators config at {pre_cfg_path}"
    pre_cfg = json.loads(pre_cfg_path.read_text(encoding="utf-8"))

    pre_ids: set[str] = set()
    for tier in ("global", "critical"):
        for v in pre_cfg.get("validators", {}).get(tier, []):
            vid = v.get("id")
            if vid:
                pre_ids.add(str(vid))
    assert pre_ids, "No validator IDs discovered from pre‑Edison config.json"

    core_cfg_path = REPO_ROOT / ".edison" / "core" / "config" / "validators.yaml"
    core_cfg = yaml.safe_load(core_cfg_path.read_text(encoding="utf-8"))
    roster = (core_cfg.get("validation") or {}).get("roster") or {}

    core_ids: set[str] = set()
    for tier in ("global", "critical"):
        for v in roster.get(tier, []):
            vid = v.get("id")
            if vid:
                core_ids.add(str(vid))

    missing = sorted(pre_ids - core_ids)
    assert not missing, (
        "Some pre‑Edison validator IDs are missing from .edison/core/config/validators.yaml "
        f"roster: {missing}"
    )


def test_pre_edison_global_validator_overlays_still_present() -> None:
    """Codex/Claude global overlays from pre‑Edison must still exist in project overlays."""
    pre_overlays = PRE_EDISON_AGENTS_ROOT / "validators" / "overlays"
    cur_overlays = REPO_ROOT / ".agents" / "validators" / "overlays"
    for name in ("codex-global-overlay.md", "claude-global-overlay.md"):
        pre_path = pre_overlays / name
        cur_path = cur_overlays / name
        assert pre_path.is_file(), f"Missing pre‑Edison overlay: {pre_path}"
        assert cur_path.is_file(), f"Missing migrated overlay: {cur_path}"


def test_pre_edison_project_validator_overlays_migrated() -> None:
    """project‑specific validator overlays must be available in .agents/validators/overlays/."""
    pre_overlays = PRE_EDISON_AGENTS_ROOT / "validators" / "overlays"
    cur_overlays = REPO_ROOT / ".agents" / "validators" / "overlays"
    expected = {
        "global-project-context.md",
        "performance-project-benchmarks.md",
        "security-project-requirements.md",
    }

    for name in sorted(expected):
        pre_path = pre_overlays / name
        assert pre_path.is_file(), f"Missing pre‑Edison project overlay: {pre_path}"
        cur_path = cur_overlays / name
        assert cur_path.is_file(), (
            "project validator overlay must be migrated into .agents/validators/overlays: "
            f"{cur_path}"
        )


def test_implementer_workflow_present_under_agents() -> None:
    """Implementer workflow must exist at the path referenced by core docs."""
    path = REPO_ROOT / ".agents" / "implementation" / "IMPLEMENTER_WORKFLOW.md"
    assert path.is_file(), (
        "Implementer workflow missing at .agents/implementation/IMPLEMENTER_WORKFLOW.md; "
        "migrate it from the pre‑Edison archive."
    )


def test_implementation_output_format_present_under_agents() -> None:
    """Implementation Report output format must exist at the canonical .agents path."""
    path = REPO_ROOT / ".agents" / "implementation" / "OUTPUT_FORMAT.md"
    assert path.is_file(), (
        "Implementation Report OUTPUT_FORMAT missing at .agents/implementation/OUTPUT_FORMAT.md; "
        "migrate it from the pre‑Edison archive."
    )
    text = path.read_text(encoding="utf-8")
    assert ".edison/core/schemas/implementation-report.schema.json" in text, (
        "Implementation OUTPUT_FORMAT must reference the canonical implementation-report "
        "schema under .edison/core/schemas/."
    )


def test_pre_edison_worktree_config_preserved_in_agents_config() -> None:
    """Worktree base/branch config from pre‑Edison must match .agents/config.yml."""
    pre_cfg_path = PRE_EDISON_AGENTS_ROOT / "delegation" / "config.json"
    pre_cfg = json.loads(pre_cfg_path.read_text(encoding="utf-8"))
    pre_wt = pre_cfg.get("worktrees") or {}

    cfg = yaml.safe_load((REPO_ROOT / ".agents" / "config.yml").read_text(encoding="utf-8"))
    wt = cfg.get("worktrees") or {}

    for key in ("baseDirectory", "branchPrefix", "defaultBaseBranch"):
        assert pre_wt.get(key) == wt.get(key), (
            f"Worktree setting '{key}' drifted between pre‑Edison delegation config "
            f"and .agents/config.yml: pre={pre_wt.get(key)!r}, current={wt.get(key)!r}"
        )


def test_no_runtime_references_to_pre_edison_archive_tree() -> None:
    """Runtime config/code must not reference the archived pre‑Edison .agents tree."""
    needle = ".project/qa/archive/agents-pre-cleanup-20251118-093031/.agents"
    search_roots = [
        REPO_ROOT / ".edison" / "core",
        REPO_ROOT / ".agents",
        REPO_ROOT / ".claude",
    ]

    offenders: list[str] = []
    for root in search_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            # Ignore this test module itself, which intentionally references the path
            if path.name == Path(__file__).name:
                continue
            # Limit to likely text/config files
            if path.suffix.lower() not in {
                ".py",
                ".md",
                ".json",
                ".yaml",
                ".yml",
                ".sh",
                ".ts",
                ".tsx",
                ".js",
            } and path.name not in {"config.yml", "config.json"}:
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except Exception:
                continue
            if needle in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))

    assert not offenders, (
        "Archived pre‑Edison .agents tree should not be referenced from runtime "
        f"code/config; found references in: {offenders}"
    )


if __name__ == "__main__":  # pragma: no cover
    import pytest

    raise SystemExit(pytest.main([__file__]))
