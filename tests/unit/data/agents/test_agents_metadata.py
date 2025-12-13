from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[4]
AGENTS_DIR = ROOT / "src/edison/data/agents"


def _load_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    sections = text.split("---", 2)
    assert len(sections) >= 3, f"{path} missing YAML frontmatter"
    raw_frontmatter = sections[1]
    return yaml.safe_load(raw_frontmatter)


def _line_count(text: str) -> int:
    return len(text.splitlines())


def test_all_agents_have_metadata_version_and_linecount() -> None:
    agent_files = sorted(AGENTS_DIR.glob("*.md"))
    assert len(agent_files) == 6, "Expected six core agent files"

    for path in agent_files:
        frontmatter = _load_frontmatter(path)
        metadata = frontmatter.get("metadata")

        assert metadata, f"{path.name} missing metadata section"
        assert metadata.get("version") == "2.0.0"
        # last_updated is required to make pack/core drift visible in reviews.
        assert metadata.get("last_updated"), f"{path.name} missing last_updated"
