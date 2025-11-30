from __future__ import annotations

from pathlib import Path

import yaml

from edison.data import get_data_path
from tests.helpers.paths import get_repo_root


PROJECT_ROOT = get_repo_root()


def _load_yaml(rel_path: str) -> dict:
    """Load YAML from bundled Edison data."""
    # Map old paths to new bundled data paths
    if rel_path.startswith("core/config/"):
        filename = rel_path.replace("core/config/", "")
        path = get_data_path("config", filename)
    elif rel_path.startswith("core/"):
        # For core/defaults.yaml → config/defaults.yaml
        filename = rel_path.replace("core/", "")
        path = get_data_path("config", filename)
    else:
        path = PROJECT_ROOT / rel_path

    assert path.exists(), f"missing config file: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_validators_yaml_uses_nextjs_and_database():
    data = _load_yaml("core/config/validators.yaml")
    specialized = data["validation"]["roster"]["specialized"]

    ids = {v["id"] for v in specialized}
    blob = "\n".join(str(v) for v in specialized)

    assert "nextjs" in ids, "specialized validators must include nextjs"
    assert "prisma" in ids, "specialized validators must include prisma (database validator)"
    assert "webapp" not in blob, "legacy webapp validator should be removed"
    assert "ormsuite" not in blob, "legacy ormsuite validator should be removed"


def test_delegation_yaml_routes_prisma_and_nextjs():
    data = _load_yaml("core/config/delegation.yaml")
    file_rules = data["delegation"]["filePatternRules"]

    assert "schema.prisma" in file_rules
    assert "prisma/migrations/**/*" in file_rules

    # App Router files should use nextjs-specific agent
    for key in ("**/layout.tsx", "**/page.tsx", "**/loading.tsx", "**/error.tsx"):
        assert file_rules[key]["subAgentType"].startswith("component-builder-nextjs")
