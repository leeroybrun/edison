"""Guards against legacy CLI references in Edison source code.

Ensures the modern `edison` CLI fully replaces historical
`.agents/scripts/*` invocations within `src/edison`.
"""

from __future__ import annotations

from pathlib import Path
import re
from typing import Iterable


TEXT_EXTENSIONS = {
    ".py",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".sh",
}

FORBIDDEN_PATTERN = re.compile(r"\.agents/scripts")


def _iter_text_files(root: Path) -> Iterable[Path]:
    """Yield text-like files under ``root``.

    Binary files are skipped by extension to avoid decode errors.
    """

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in TEXT_EXTENSIONS or path.suffix == "":
            yield path


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return None


def test_no_legacy_cli_references_in_src_edison() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    src_root = repo_root / "src" / "edison"
    assert src_root.exists(), "src/edison directory missing"

    offenders: list[str] = []
    for path in _iter_text_files(src_root):
        text = _read_text(path)
        if text and FORBIDDEN_PATTERN.search(text):
            offenders.append(str(path.relative_to(repo_root)))

    assert not offenders, (
        "Legacy CLI references found in: " + ", ".join(sorted(offenders))
    )
