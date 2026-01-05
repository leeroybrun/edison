"""
Edison vendor show command.

SUMMARY: Show details for a vendor
"""
from __future__ import annotations

import argparse

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Show details for a vendor"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    parser.add_argument(
        "name",
        help="Vendor name to show",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """Show vendor details."""
    from edison.core.vendors.config import VendorConfig
    from edison.core.vendors.lock import VendorLock
    from edison.core.vendors.redaction import redact_url_credentials

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        config = VendorConfig(repo_root)
        lock = VendorLock(repo_root)
        lock.load()

        source = config.get_source_by_name(args.name)
        if source is None:
            formatter.error(
                Exception(f"Vendor not found: {args.name}"),
                error_code="vendor_not_found",
            )
            return 1

        entry = lock.get_entry(args.name)
        vendor_path = repo_root / source.path
        synced = vendor_path.exists()

        if formatter.json_mode:
            data = {
                "name": source.name,
                "url": redact_url_credentials(source.url),
                "ref": source.ref,
                "path": source.path,
                "sparse": source.sparse,
                "locked_commit": entry.commit if entry else None,
                "synced": synced,
                "vendor_path": str(vendor_path) if synced else None,
            }
            formatter.json_output(data)
        else:
            formatter.text(f"Vendor: {source.name}")
            formatter.text("")
            formatter.text(f"  URL:    {redact_url_credentials(source.url)}")
            formatter.text(f"  Ref:    {source.ref}")
            formatter.text(f"  Path:   {source.path}")
            if source.sparse:
                formatter.text(f"  Sparse: {', '.join(source.sparse)}")
            if entry:
                formatter.text(f"  Commit: {entry.commit}")
            formatter.text(f"  Synced: {'Yes' if synced else 'No'}")
            if synced:
                formatter.text(f"  Location: {vendor_path}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="vendor_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    parsed = parser.parse_args()
    exit(main(parsed))
