from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from edison.data import get_data_path, read_yaml


CONFIG = read_yaml("config", "instruction_dedup.yaml")
DATA_ROOT = get_data_path("config").parent


def _strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) > 2:
            return parts[2]
    return text


def _normalize_block(block: str) -> str:
    lines = [line.rstrip() for line in block.strip().splitlines()]
    return "\n".join(lines)


def _extract_blocks(path: Path, *, min_words: int, min_lines: int) -> list[str]:
    text = _strip_frontmatter(path.read_text(encoding="utf-8"))
    blocks: list[str] = []

    for raw in text.split("\n\n"):
        normalized = _normalize_block(raw)
        if not normalized:
            continue
        if len(normalized.split()) < min_words:
            continue
        if len(normalized.splitlines()) < min_lines:
            continue
        blocks.append(normalized)

    return blocks


def _find_duplicates(paths: list[Path], *, min_words: int, min_lines: int) -> dict[str, list[Path]]:
    seen: dict[str, list[Path]] = defaultdict(list)
    for path in paths:
        for block in _extract_blocks(path, min_words=min_words, min_lines=min_lines):
            seen[block].append(path)
    return {block: locations for block, locations in seen.items() if len(locations) > 1}


def _format_duplicates(duplicates: dict[str, list[Path]], *, max_examples: int) -> str:
    lines: list[str] = []
    for block, paths in list(duplicates.items())[:max_examples]:
        relative_paths = [p.relative_to(DATA_ROOT) for p in paths]
        lines.append(
            f"Block starting '{block.splitlines()[0][:80]}...' appears in: {[str(p) for p in relative_paths]}"
        )
    return "\n".join(lines)


def test_agent_instruction_blocks_are_deduplicated() -> None:
    cfg = CONFIG["agent_instruction_blocks"]
    agents_dir = get_data_path("agents")
    agent_paths = sorted(agents_dir.glob("*.md"))

    duplicates = _find_duplicates(agent_paths, min_words=cfg["min_words"], min_lines=cfg["min_lines"])

    assert not duplicates, _format_duplicates(duplicates, max_examples=cfg["max_examples"])


def test_validator_instruction_blocks_are_deduplicated() -> None:
    cfg = CONFIG["validator_instruction_blocks"]
    validators_dir = get_data_path("validators")
    validator_paths = sorted(validators_dir.rglob("*.md"))

    duplicates = _find_duplicates(validator_paths, min_words=cfg["min_words"], min_lines=cfg["min_lines"])

    assert not duplicates, _format_duplicates(duplicates, max_examples=cfg["max_examples"])
