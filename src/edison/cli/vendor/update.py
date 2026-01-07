"""
Edison vendor update command.

SUMMARY: Update vendors to latest refs
"""
from __future__ import annotations

import argparse

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Update vendors to latest refs"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "name",
        nargs="?",
        help="Vendor name to update (all if omitted)",
    )
    parser.add_argument(
        "--ref",
        help="Override ref to update to (only with single vendor)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Update vendors to latest refs."""
    from edison.core.vendors.sync import VendorSyncManager

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)

        if args.ref and not args.name:
            formatter.error(
                Exception("--ref requires a specific vendor name"),
                error_code="invalid_args",
            )
            return 1

        manager = VendorSyncManager(repo_root)

        if args.name:
            results = [manager.update_vendor(args.name, ref=args.ref)]
        else:
            results = manager.update_all()

        if formatter.json_mode:
            data = {
                "results": [
                    {
                        "vendor": r.vendor_name,
                        "success": r.success,
                        "commit": r.commit,
                        "previous_commit": r.previous_commit,
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
            formatter.text(f"Updated {success_count}/{len(results)} vendors:")
            formatter.text("")
            for result in results:
                status = "OK" if result.success else "FAILED"
                formatter.text(f"  {result.vendor_name}: {status}")
                if result.previous_commit and result.commit:
                    if result.previous_commit != result.commit:
                        formatter.text(
                            f"    {result.previous_commit[:12]} -> {result.commit[:12]}"
                        )
                    else:
                        formatter.text(f"    Already at {result.commit[:12]}")
                elif result.commit:
                    formatter.text(f"    Commit: {result.commit[:12]}")
                if result.error:
                    formatter.text(f"    Error: {result.error}")

        failed = [r for r in results if not r.success]
        return 1 if failed else 0

    except Exception as e:
        formatter.error(e, error_code="vendor_update_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    parsed = parser.parse_args()
    exit(main(parsed))
