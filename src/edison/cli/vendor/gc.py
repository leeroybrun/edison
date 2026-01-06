"""
Edison vendor gc command.

SUMMARY: Garbage collect unused vendor caches
"""
from __future__ import annotations

import argparse

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Garbage collect unused vendor caches"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be cleaned without doing it",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="clean_all",
        help="Clean all caches including active ones",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Garbage collect unused vendor caches."""
    from edison.core.vendors.gc import VendorGarbageCollector

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        gc = VendorGarbageCollector(repo_root)

        result = gc.collect(
            dry_run=args.dry_run,
            clean_all=args.clean_all,
        )

        if formatter.json_mode:
            data = {
                "removed_mirrors": result.removed_mirrors,
                "removed_checkouts": result.removed_checkouts,
                "bytes_freed": result.bytes_freed,
                "dry_run": args.dry_run,
            }
            formatter.json_output(data)
        else:
            if args.dry_run:
                formatter.text("Dry run - would clean:")
            else:
                formatter.text("Cleaned:")

            formatter.text(f"  Mirrors removed: {len(result.removed_mirrors)}")
            for mirror in result.removed_mirrors:
                formatter.text(f"    - {mirror}")

            formatter.text(f"  Checkouts removed: {len(result.removed_checkouts)}")
            for checkout in result.removed_checkouts:
                formatter.text(f"    - {checkout}")

            if result.bytes_freed > 0:
                size_mib = result.bytes_freed / (1024 * 1024)
                formatter.text(f"  Space freed: {size_mib:.2f} MiB")

        return 0

    except Exception as e:
        formatter.error(e, error_code="vendor_gc_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    parsed = parser.parse_args()
    exit(main(parsed))
