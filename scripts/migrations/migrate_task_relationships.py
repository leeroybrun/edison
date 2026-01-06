from __future__ import annotations

import argparse
from pathlib import Path

from edison.core.task.relationships.migration import migrate_task_markdown_relationships


def _iter_markdown_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() == ".md":
            files.append(path)
            continue
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="migrate_task_relationships.py",
        description="Migrate legacy task relationship frontmatter keys to canonical `relationships:`.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to operate on (default: current directory).",
    )
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        help="Path (file or directory) to scan. Can be repeated. Default: .project/tasks",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not write files.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if any file would change.",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    raw_paths = args.paths or [".project/tasks"]
    paths = [root / p for p in raw_paths]
    files = _iter_markdown_files(paths)

    changed: list[Path] = []
    for path in files:
        before = path.read_text(encoding="utf-8")
        after = migrate_task_markdown_relationships(before)
        if after != before:
            changed.append(path)
            if not args.dry_run:
                path.write_text(after, encoding="utf-8")

    for path in changed:
        print(f"migrated: {path.relative_to(root)}")

    if args.check and changed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

