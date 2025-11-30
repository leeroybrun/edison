"""
Edison rules migration utilities.

These are standalone scripts for migrating rules registries.

Architecture:
- Bundled rules: edison.data/rules/registry.yml
- Project rules: .edison/rules/registry.yml (overrides)
- NO .edison/core/ - that is legacy
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from edison.core.utils.paths import get_project_config_dir
from edison.data import get_data_path
from edison.cli import OutputFormatter


def rules_migrate_registry_paths() -> int:
    """
    Migrate legacy .agents/ prefixes to .edison/ in project registry.

    This fixes paths that reference the old .agents directory structure.
    Project-level rules are at .edison/rules/registry.json (not .edison/core/rules/).
    """
    formatter = OutputFormatter(json_mode=False)

    try:
        # Find project root
        cwd = Path.cwd()
        config_dir = get_project_config_dir(cwd, create=False)
        
        # Project-level rules at .edison/rules/ (not .edison/core/rules/)
        registry_path = config_dir / "rules" / "registry.json"

        if not registry_path.exists():
            formatter.text(f"No project-level rules registry at {registry_path}")
            formatter.text("Bundled rules are at edison.data/rules/registry.yml")
            return 0

        # Load registry
        data = json.loads(registry_path.read_text(encoding="utf-8"))

        # Migrate paths
        modified = False
        for rule in data.get("rules", []):
            source_path = rule.get("sourcePath", "")
            if source_path.startswith(".agents/"):
                # Map .agents/guidelines/ -> .edison/guidelines/ (no /core/)
                new_path = source_path.replace(".agents/guidelines/", ".edison/guidelines/")
                new_path = new_path.replace(".agents/guides/", ".edison/guides/")
                new_path = new_path.replace(".agents/validators/", ".edison/validators/")
                rule["sourcePath"] = new_path
                modified = True
                formatter.text(f"Migrated: {source_path} -> {new_path}")
            elif ".edison/core/" in source_path:
                # Also migrate legacy .edison/core/ paths
                new_path = source_path.replace(".edison/core/", ".edison/")
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
    Migrate project rules registry from JSON to YAML format.

    Creates registry.yml from registry.json with version bump and enriched metadata.
    Project-level rules are at .edison/rules/ (not .edison/core/rules/).
    """
    formatter = OutputFormatter(json_mode=False)

    try:
        # Find project root
        cwd = Path.cwd()
        config_dir = get_project_config_dir(cwd, create=False)
        
        # Project-level rules at .edison/rules/ (not .edison/core/rules/)
        json_path = config_dir / "rules" / "registry.json"
        yaml_path = config_dir / "rules" / "registry.yml"

        if not json_path.exists():
            formatter.text(f"No project-level JSON registry at {json_path}")
            formatter.text("Bundled rules are at edison.data/rules/registry.yml")
            return 0

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

    Checks both bundled and project-level rules registries.
    """
    formatter = OutputFormatter(json_mode=False)

    try:
        cwd = Path.cwd()
        config_dir = get_project_config_dir(cwd, create=False)
        
        # Check bundled rules first
        bundled_yaml_path = get_data_path("rules", "registry.yml")
        
        # Check project-level rules at .edison/rules/
        project_yaml_path = config_dir / "rules" / "registry.yml"

        total_verified = 0
        failures = []

        for yaml_path, source_name in [
            (bundled_yaml_path, "bundled"),
            (project_yaml_path, "project"),
        ]:
            if not yaml_path.exists():
                continue

            # Load YAML
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))

            for rule in data.get("rules", []):
                rule_id = rule.get("id", "UNKNOWN")
                source_path = rule.get("sourcePath", "")

                if "#" in source_path:
                    file_path, anchor = source_path.split("#", 1)
                    
                    # Resolve file path - check bundled data first, then project
                    full_path = None
                    if file_path.startswith(".edison/"):
                        # Project-relative path
                        full_path = cwd / file_path
                    else:
                        # Try bundled data
                        bundled_path = Path(get_data_path("")) / file_path
                        if bundled_path.exists():
                            full_path = bundled_path
                        else:
                            full_path = cwd / file_path

                    if full_path is None or not full_path.exists():
                        failures.append(f"[{source_name}] {rule_id}: File not found: {file_path}")
                        continue

                    # Check for anchor markers in file
                    content = full_path.read_text(encoding="utf-8")
                    anchor_marker = f"<!-- ANCHOR: {anchor} -->"
                    end_marker = f"<!-- END ANCHOR: {anchor} -->"

                    if anchor_marker not in content:
                        failures.append(f"[{source_name}] {rule_id}: Start anchor not found: {anchor_marker}")
                    elif end_marker not in content:
                        failures.append(f"[{source_name}] {rule_id}: End anchor not found: {end_marker}")
                    else:
                        total_verified += 1

        if failures:
            formatter.error(
                Exception("Anchor verification failures"),
                error_code="error"
            )
            for failure in failures:
                formatter.text(f"  - {failure}")
            return 1

        formatter.text(f"✓ All {total_verified} rule anchors verified")
        return 0

    except Exception as e:
        formatter.error(e, error_code="error")
        return 1
