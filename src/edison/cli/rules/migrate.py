"""
Edison rules migration utilities.

These are standalone scripts for migrating rules registries.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from edison.core.utils.paths import get_project_config_dir
from edison.cli import OutputFormatter


def rules_migrate_registry_paths() -> int:
    """
    Migrate legacy .agents/ prefixes to .edison/ in registry.json.

    This fixes paths that reference the old .agents directory structure.
    """
    formatter = OutputFormatter(json_mode=False)

    try:
        # Find project root
        cwd = Path.cwd()
        config_dir = get_project_config_dir(cwd, create=False)
        registry_path = config_dir / "core" / "rules" / "registry.json"

        if not registry_path.exists():
            formatter.error(
                Exception(f"Registry not found: {registry_path}"),
                error_code="error"
            )
            return 1

        # Load registry
        data = json.loads(registry_path.read_text(encoding="utf-8"))

        # Migrate paths
        modified = False
        for rule in data.get("rules", []):
            source_path = rule.get("sourcePath", "")
            if source_path.startswith(".agents/"):
                # Map .agents/guidelines/ -> .edison/core/guidelines/
                new_path = source_path.replace(".agents/guidelines/", ".edison/core/guidelines/")
                new_path = new_path.replace(".agents/guides/", ".edison/core/guides/")
                new_path = new_path.replace(".agents/validators/", ".edison/core/validators/")
                rule["sourcePath"] = new_path
                modified = True
                formatter.text(f"Migrated: {source_path} -> {new_path}")

        if modified:
            # Write back
            registry_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            formatter.text(f"\n✓ Updated {registry_path}")
        else:
            formatter.text("No paths needed migration")

        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1


def rules_json_to_yaml_migration() -> int:
    """
    Migrate rules registry from JSON to YAML format.

    Creates registry.yml from registry.json with version bump and enriched metadata.
    """
    formatter = OutputFormatter(json_mode=False)

    try:
        # Find project root
        cwd = Path.cwd()
        config_dir = get_project_config_dir(cwd, create=False)
        json_path = config_dir / "core" / "rules" / "registry.json"
        yaml_path = config_dir / "core" / "rules" / "registry.yml"

        if not json_path.exists():
            formatter.error(
                Exception(f"JSON registry not found: {json_path}"),
                error_code="error"
            )
            return 1

        # Load JSON
        data = json.loads(json_path.read_text(encoding="utf-8"))

        # Bump version to 2.0.0 for YAML
        data["version"] = "2.0.0"

        # Enrich rules with YAML-required fields
        for rule in data.get("rules", []):
            # Extract category from rule ID (e.g., RULE.DELEGATION.* -> delegation)
            rule_id = rule.get("id", "")
            if rule_id.startswith("RULE."):
                parts = rule_id.split(".")
                category = parts[1].lower() if len(parts) > 1 else "general"
            else:
                category = "general"

            # Add missing fields
            if "category" not in rule:
                rule["category"] = category
            if "blocking" not in rule:
                rule["blocking"] = False
            if "guidance" not in rule:
                rule["guidance"] = ""

            # Convert start/end markers to anchor-based sourcePath
            source_path = rule.get("sourcePath", "")
            start_marker = rule.get("start", "")
            end_marker = rule.get("end", "")

            # Extract anchor from markers if present
            # Format: <!-- RULE: RULE.ID START --> or <!-- ANCHOR: anchor-name -->
            if start_marker and "#" not in source_path:
                # Try to extract anchor name from marker
                if "ANCHOR:" in start_marker:
                    anchor = start_marker.split("ANCHOR:")[1].split("-->")[0].strip()
                    rule["sourcePath"] = f"{source_path}#{anchor}"
                elif "RULE:" in start_marker:
                    # Use rule ID as anchor in lowercase with dashes
                    anchor = rule_id.replace("RULE.", "").replace(".", "-").replace("_", "-").lower()
                    # Common anchors based on suffix
                    if rule_id.endswith(".PRIORITY_CHAIN"):
                        anchor = "priority-chain"
                    elif rule_id.endswith(".FIRST"):
                        anchor = rule_id.split(".")[-2].lower() + "-first"
                    rule["sourcePath"] = f"{source_path}#{anchor}"

            # Remove old start/end markers from YAML
            rule.pop("start", None)
            rule.pop("end", None)

        # Write YAML
        yaml_path.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True),
            encoding="utf-8"
        )

        formatter.text(f"✓ Created {yaml_path}")
        formatter.text(f"  Version: {data['version']}")
        formatter.text(f"  Rules: {len(data.get('rules', []))}")

        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        import traceback
        traceback.print_exc()
        return 1


def rules_verify_anchors() -> int:
    """
    Verify that all rule anchors in registry.yml are resolvable.

    Checks that each rule's sourcePath anchor exists in the source file.
    """
    formatter = OutputFormatter(json_mode=False)

    try:
        # Find project root
        cwd = Path.cwd()
        config_dir = get_project_config_dir(cwd, create=False)
        yaml_path = config_dir / "core" / "rules" / "registry.yml"

        if not yaml_path.exists():
            formatter.error(
                Exception(f"YAML registry not found: {yaml_path}"),
                error_code="error"
            )
            return 1

        # Load YAML
        data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

        failures = []
        for rule in data.get("rules", []):
            rule_id = rule.get("id", "UNKNOWN")
            source_path = rule.get("sourcePath", "")

            if "#" in source_path:
                file_path, anchor = source_path.split("#", 1)
                full_path = cwd / file_path

                if not full_path.exists():
                    failures.append(f"{rule_id}: File not found: {full_path}")
                    continue

                # Check for anchor markers in file
                content = full_path.read_text(encoding="utf-8")
                anchor_marker = f"<!-- ANCHOR: {anchor} -->"
                end_marker = f"<!-- END ANCHOR: {anchor} -->"

                if anchor_marker not in content:
                    failures.append(f"{rule_id}: Start anchor not found: {anchor_marker}")
                elif end_marker not in content:
                    failures.append(f"{rule_id}: End anchor not found: {end_marker}")

        if failures:
            formatter.error(
                Exception("Anchor verification failures"),
                error_code="error"
            )
            for failure in failures:
                formatter.text(f"  - {failure}")
            return 1

        formatter.text(f"✓ All {len(data.get('rules', []))} rule anchors verified")
        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1
