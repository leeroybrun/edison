"""
Edison vendor list command.

SUMMARY: List configured vendor sources
"""
from __future__ import annotations

import argparse

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "List configured vendor sources"


def register_args(parser: argparse.ArgumentParser) -> None:
    """Register command-specific arguments."""
    add_json_flag(parser)
    add_repo_root_flag(parser)


def main(args: argparse.Namespace) -> int:
    """List configured vendors."""
    from edison.core.vendors.config import VendorConfig
    from edison.core.vendors.lock import VendorLock
    from edison.core.vendors.redaction import redact_url_credentials

    formatter = OutputFormatter(json_mode=getattr(args, "json", False))

    try:
        repo_root = get_repo_root(args)
        config = VendorConfig(repo_root)
        lock = VendorLock(repo_root)
        lock.load()

        sources = config.get_sources()

        if formatter.json_mode:
            vendors_data = []
            for source in sources:
                entry = lock.get_entry(source.name)
                vendors_data.append({
                    "name": source.name,
                    "url": redact_url_credentials(source.url),
                    "ref": source.ref,
                    "path": source.path,
                    "sparse": source.sparse,
                    "locked_commit": entry.commit if entry else None,
                    "synced": (repo_root / source.path).exists(),
                })
            formatter.json_output({"vendors": vendors_data})
        else:
            if not sources:
                formatter.text("No vendors configured.")
                formatter.text("")
                formatter.text("Add vendors in .edison/config/vendors.yaml:")
                formatter.text("  vendors:")
                formatter.text("    sources:")
                formatter.text("      - name: example")
                formatter.text("        url: https://github.com/org/repo.git")
                formatter.text("        ref: main")
                formatter.text("        path: vendors/example")
            else:
                formatter.text(f"Configured vendors ({len(sources)}):")
                formatter.text("")
                for source in sources:
                    entry = lock.get_entry(source.name)
                    synced = (repo_root / source.path).exists()
                    status = "synced" if synced else "not synced"
                    formatter.text(f"  {source.name}")
                    formatter.text(f"    URL:    {redact_url_credentials(source.url)}")
                    formatter.text(f"    Ref:    {source.ref}")
                    formatter.text(f"    Path:   {source.path}")
                    if entry:
                        formatter.text(f"    Commit: {entry.commit[:12]}")
                    formatter.text(f"    Status: {status}")
                    formatter.text("")

        return 0

    except Exception as e:
        formatter.error(e, error_code="vendor_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    parsed = parser.parse_args()
    exit(main(parsed))
