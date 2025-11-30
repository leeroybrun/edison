from __future__ import annotations
from helpers.io_utils import write_yaml, write_json

from pathlib import Path

import pytest

from edison.core.setup import SetupDiscovery

def _seed_setup_config(repo_root: Path) -> Path:
    """Write the canonical setup.yaml discovery section for tests."""
    setup_cfg = {
        "setup": {"version": "1.0", "modes": []},
        "discovery": {
            "packs": {"directory": ".edison/packs", "pattern": "*/config.yml"},
            "orchestrators": {
                "config_file": ".edison/core/config/orchestrators.yaml",
                "fallback": ["claude", "cursor", "codex"],
            },
            "validators": {
                "core_config": ".edison/core/config/validators.yaml",
                "pack_pattern": ".edison/packs/*/config/validators.yml",
            },
            "agents": {
                "core_config": ".edison/core/config/agents.yaml",
                "pack_pattern": ".edison/packs/*/config/agents.yml",
            },
        },
    }
    cfg_path = repo_root / ".edison" / "core" / "config" / "setup.yaml"
    write_yaml(cfg_path, setup_cfg)
    return cfg_path

def test_discover_packs_uses_configured_directory(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_setup_config(repo)
    packs_dir = repo / ".edison" / "packs"
    # Matching packs must contain config.yml
    (packs_dir / "alpha" / "config.yml").parent.mkdir(parents=True, exist_ok=True)
    (packs_dir / "alpha" / "config.yml").write_text("name: alpha", encoding="utf-8")
    (packs_dir / "beta" / "config.yml").parent.mkdir(parents=True, exist_ok=True)
    (packs_dir / "beta" / "config.yml").write_text("name: beta", encoding="utf-8")
    # Non-matching (no config.yml) should be ignored
    (packs_dir / "ghost").mkdir(parents=True, exist_ok=True)

    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    found = discovery.discover_packs()
    assert found == ["alpha", "beta"]

def test_discover_orchestrators_reads_profiles(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_setup_config(repo)
    orch_cfg = {
        "orchestrators": {
            "profiles": {
                "claude": {"command": "claude"},
                "cursor": {"command": "cursor"},
                "codex": {"command": "codex"},
            }
        }
    }
    write_yaml(repo / ".edison" / "core" / "config" / "orchestrators.yaml", orch_cfg)

    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    found = discovery.discover_orchestrators()
    assert found == ["claude", "cursor", "codex"]

def test_discover_orchestrators_falls_back_when_missing(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_setup_config(repo)
    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    assert discovery.discover_orchestrators() == ["claude", "cursor", "codex"]

def test_discover_validators_merges_core_and_packs(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_setup_config(repo)
    core_cfg = {
        "validation": {
            "roster": {
                "global": [{"id": "core-global"}],
                "critical": [{"id": "core-critical"}],
            }
        }
    }
    write_yaml(repo / ".edison" / "core" / "config" / "validators.yaml", core_cfg)

    pack_cfg = {"validation": {"roster": {"specialized": [{"id": "pack-val"}]}}}
    pack_path = repo / ".edison" / "packs" / "alpha" / "config" / "validators.yml"
    write_yaml(pack_path, pack_cfg)

    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    found = discovery.discover_validators(["alpha"])
    assert set(found) == {"core-global", "core-critical", "pack-val"}

def test_discover_agents_combines_sources(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_setup_config(repo)
    core_cfg = {"agents": [{"id": "core-agent"}]}
    write_yaml(repo / ".edison" / "core" / "config" / "agents.yaml", core_cfg)

    pack_cfg = {"agents": [{"id": "pack-agent"}, {"id": "core-agent"}]}
    write_yaml(repo / ".edison" / "packs" / "alpha" / "config" / "agents.yml", pack_cfg)

    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    found = discovery.discover_agents(["alpha"])
    assert found == ["core-agent", "pack-agent"]

def test_detect_project_name_prefers_package_json(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_setup_config(repo)
    write_json(repo / "package.json", {"name": "sample-app"})
    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    assert discovery.detect_project_name() == "sample-app"

def test_detect_project_type_uses_heuristics(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    _seed_setup_config(repo)
    write_json(repo / "package.json", {"dependencies": {"next": "14.0.0"}})
    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    assert discovery.detect_project_type() == "Next.js Full-Stack"

    # Rust detection when package.json absent or non-next
    (repo / "package.json").unlink()
    (repo / "Cargo.toml").write_text("[package]\nname='rusty'\n", encoding="utf-8")
    discovery = SetupDiscovery(repo / ".edison" / "core", repo)
    assert discovery.detect_project_type() == "Rust Project"
