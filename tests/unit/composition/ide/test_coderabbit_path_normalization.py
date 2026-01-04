"""Test CodeRabbit config directory naming consistency.

This test ensures that CodeRabbit configs use "config" (singular) directory
consistently with other IDE composers, not "configs" (plural).

Following Edison principles:
- TDD: Write failing test first, then fix implementation
- NO MOCKS: Test real path resolution
- NO LEGACY: No backward compatibility for "configs" directory
"""
from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.adapters import CoderabbitAdapter
from tests.helpers.io_utils import write_yaml


def test_coderabbit_composer_uses_config_not_configs_for_templates(tmp_path: Path) -> None:
    """CoderabbitAdapter should look for templates in templates/config/ not templates/configs/."""
    # Setup: Create bundled template in CORRECT location (config, singular)
    templates_dir = tmp_path / "templates" / "config"
    templates_dir.mkdir(parents=True, exist_ok=True)

    template_config = {
        "reviews": {
            "auto_review": True,
        },
    }
    write_yaml(templates_dir / "coderabbit.yaml", template_config)

    # Create minimal packs config
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(config_dir / "edison.yaml", {"packs": {"active": []}})

    # Mock core_dir to point to tmp_path (simulating bundled data)
    composer = CoderabbitAdapter(project_root=tmp_path)
    composer.core_dir = tmp_path

    # ACT: Compose config
    loaded = composer.compose_coderabbit_config()

    # ASSERT: Should successfully load from templates/config/ directory
    assert loaded == template_config, \
        "Should load template from templates/config/ not templates/configs/"


def test_coderabbit_composer_uses_config_not_configs_for_packs(tmp_path: Path) -> None:
    """CoderabbitAdapter should look for pack configs in packs/{pack}/config/ not packs/{pack}/configs/."""
    # Setup: Create pack config in CORRECT location (config, singular)
    pack_config_dir = tmp_path / "packs" / "python" / "config"
    pack_config_dir.mkdir(parents=True, exist_ok=True)

    pack_config = {
        "path_instructions": [
            {"path": "**/*.py", "instructions": "Python pack instructions"},
        ],
    }
    write_yaml(pack_config_dir / "coderabbit.yaml", pack_config)

    # Create packs config
    project_config_dir = tmp_path / ".edison" / "config"
    project_config_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(project_config_dir / "edison.yaml", {"packs": {"active": ["python"]}})

    # Mock bundled_packs_dir to point to tmp_path/packs
    composer = CoderabbitAdapter(project_root=tmp_path)
    composer.bundled_packs_dir = tmp_path / "packs"
    composer.project_packs_dir = tmp_path / "packs"

    # ACT: Compose config (includes pack)
    loaded = composer.compose_coderabbit_config()

    # ASSERT: Should successfully include from packs/python/config/ directory
    assert loaded.get("path_instructions") == pack_config.get("path_instructions"), (
        "Should load pack config from packs/python/config/ not packs/python/configs/"
    )


def test_coderabbit_composer_uses_config_not_configs_for_project(tmp_path: Path) -> None:
    """CoderabbitAdapter should look for project configs in .edison/config/ not .edison/configs/."""
    # Setup: Create project config in CORRECT location (config, singular)
    project_config_dir = tmp_path / ".edison" / "config"
    project_config_dir.mkdir(parents=True, exist_ok=True)

    project_config = {
        "path_instructions": [
            {"path": "**/*.py", "instructions": "Project-specific instructions"},
        ],
    }
    write_yaml(project_config_dir / "coderabbit.yaml", project_config)
    write_yaml(project_config_dir / "edison.yaml", {"packs": {"active": []}})

    # ACT: Create composer and compose config
    composer = CoderabbitAdapter(project_root=tmp_path)
    loaded = composer.compose_coderabbit_config()

    # ASSERT: Should successfully include from .edison/config/ directory
    assert loaded.get("path_instructions") == project_config.get("path_instructions"), (
        "Should load project config from .edison/config/ not .edison/configs/"
    )


def test_no_legacy_configs_directory_support(tmp_path: Path) -> None:
    """CoderabbitAdapter should NOT fallback to "configs" directory (no legacy support)."""
    # Setup: Create config in WRONG location (configs, plural) - should be ignored
    wrong_dir = tmp_path / ".edison" / "configs"
    wrong_dir.mkdir(parents=True, exist_ok=True)

    wrong_config = {
        "path_instructions": [
            {"path": "**/*.py", "instructions": "This should be ignored"},
        ],
    }
    write_yaml(wrong_dir / "coderabbit.yaml", wrong_config)

    # Create correct directory structure (empty)
    correct_dir = tmp_path / ".edison" / "config"
    correct_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(correct_dir / "edison.yaml", {"packs": {"active": []}})

    # ACT: Create composer and compose config
    composer = CoderabbitAdapter(project_root=tmp_path)
    loaded = composer.compose_coderabbit_config()

    # ASSERT: Should NOT load from legacy .edison/configs/ directory
    assert loaded.get("path_instructions") != wrong_config.get("path_instructions"), (
        "Should NOT load from legacy .edison/configs/ directory"
    )


def test_bundled_data_structure_uses_config_directory(tmp_path: Path) -> None:
    """Verify bundled data structure in src/edison/data uses 'config' not 'configs'."""
    from edison.data import get_data_path

    # ACT: Check actual bundled data directory structure
    data_root = Path(get_data_path(""))
    templates_dir = data_root / "templates"
    packs_dir = data_root / "packs"

    # ASSERT: Templates should use "config" directory
    templates_configs_dir = templates_dir / "configs"

    # "configs" plural should NOT contain coderabbit configs.
    if templates_configs_dir.exists():
        coderabbit_files = list(templates_configs_dir.glob("coderabbit.y*"))
        assert len(coderabbit_files) == 0, (
            f"Found coderabbit files in templates/configs/: {coderabbit_files}. Should be in templates/config/"
        )

    # Pack directories should also avoid "configs" for coderabbit.
    if packs_dir.exists():
        for pack_dir in packs_dir.iterdir():
            if not pack_dir.is_dir():
                continue

            pack_configs_dir = pack_dir / "configs"
            if pack_configs_dir.exists():
                coderabbit_files = list(pack_configs_dir.glob("coderabbit.y*"))
                assert len(coderabbit_files) == 0, (
                    f"Found coderabbit files in {pack_dir.name}/configs/: {coderabbit_files}. Should be in {pack_dir.name}/config/"
                )
def test_coderabbit_composer_loads_company_pack_config(tmp_path: Path) -> None:
    """Company-layer packs should contribute coderabbit.yaml when active."""
    company_dir = tmp_path / "company-layer"
    (company_dir / "config").mkdir(parents=True, exist_ok=True)    # Insert company layer before user.
    config_dir = tmp_path / ".edison" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "layers.yaml").write_text(
        "layers:\n"
        "  roots:\n"
        "    - id: mycompany\n"
        f"      path: {company_dir.as_posix()}\n"
        "      before: user\n",
        encoding="utf-8",
    )    # Provide a pack coderabbit config in the company pack root.
    pack_config_dir = company_dir / "packs" / "python" / "config"
    pack_config_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(
        pack_config_dir / "coderabbit.yaml",
        {"coderabbit": {"company_pack": True}},
    )    # Activate the pack in project config so adapter loads it.
    write_yaml(config_dir / "edison.yaml", {"packs": {"active": ["python"]}})
    composer = CoderabbitAdapter(project_root=tmp_path)
    loaded = composer.compose_coderabbit_config()
    assert loaded.get("coderabbit", {}).get("company_pack") is True