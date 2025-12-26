from __future__ import annotations

from pathlib import Path

import yaml


def _repo_root() -> Path:
    cur = Path(__file__).resolve()
    for parent in cur.parents:
        if (parent / ".git").exists():
            return parent
    raise RuntimeError("cannot locate repository root (.git)")


def test_default_composition_config_sets_managed_block_policies_for_instruction_files() -> None:
    root = _repo_root()
    cfg_path = root / "src/edison/data/config/composition.yaml"
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))

    composition = data["composition"]
    rules = composition.get("write_policies") or []
    assert rules, "composition.write_policies should define managed instruction file behavior"

    def rule_matches(glob_pattern: str) -> bool:
        for r in rules:
            globs = r.get("globs") or []
            if isinstance(globs, str):
                globs = [globs]
            if glob_pattern in globs:
                return True
        return False

    assert rule_matches("AGENTS.md")
    assert rule_matches(".claude/CLAUDE.md")

