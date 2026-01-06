"""
Edison vendor sync command.

SUMMARY: Sync vendor checkouts to locked state
"""
from __future__ import annotations

import argparse

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Sync vendor checkouts to locked state"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "name",
        nargs="?",
        help="Vendor name to sync (all if omitted)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force sync even if already synced",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Sync vendor checkouts."""
    from edison.core.vendors.sync import VendorSyncManager

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        manager = VendorSyncManager(repo_root)

        if args.name:
            results = [manager.sync_vendor(args.name, force=args.force)]
        else:
            results = manager.sync_all(force=args.force)

        if formatter.json_mode:
            data = {
                "results": [
                    {
                        "vendor": r.vendor_name,
                        "success": r.success,
                        "commit": r.commit,
                        "changed": r.changed,
                        "error": r.error,
                    }
                    for r in results
                ]
            }
            formatter.json_output(data)
        else:
            if not results:
                formatter.text("No vendors configured.")
                return 0

            success_count = sum(1 for r in results if r.success)
            formatter.text(f"Synced {success_count}/{len(results)} vendors:")
            formatter.text("")
            for result in results:
                status = "OK" if result.success else "FAILED"
                changed = " (changed)" if result.changed else ""
                formatter.text(f"  {result.vendor_name}: {status}{changed}")
                if result.commit:
                    commit_short = result.commit[:12] if len(result.commit) >= 12 else result.commit
                    formatter.text(f"    Commit: {commit_short}")
                if result.error:
                    formatter.text(f"    Error: {result.error}")

        failed = [r for r in results if not r.success]
        return 1 if failed else 0

    except Exception as e:
        formatter.error(e, error_code="vendor_sync_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    parsed = parser.parse_args()
    exit(main(parsed))
