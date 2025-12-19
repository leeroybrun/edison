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
                "config_file": ".edison/config/orchestrators.yaml",
                "fallback": ["claude", "cursor", "codex"],
            },
            "validators": {
                "config_file": ".edison/config/validators.yaml",
                "pack_pattern": ".edison/packs/*/config/validators.yml",
            },
            "agents": {
                "config_file": ".edison/config/agents.yaml",
                "pack_pattern": ".edison/packs/*/config/agents.yml",
            },
        },
    }
    cfg_path = repo_root / ".edison" / "config" / "setup.yaml"
    write_yaml(cfg_path, setup_cfg)
    return cfg_path

def test_discover_packs_uses_configured_directory(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    packs_dir = repo / ".edison" / "packs"
    # Packs are discoverable only when they have a pack.yml manifest.
    (packs_dir / "alpha").mkdir(parents=True, exist_ok=True)
    (packs_dir / "alpha" / "pack.yml").write_text("name: alpha\nversion: 0.0.0\ndescription: alpha\n", encoding="utf-8")
    (packs_dir / "beta").mkdir(parents=True, exist_ok=True)
    (packs_dir / "beta" / "pack.yml").write_text("name: beta\nversion: 0.0.0\ndescription: beta\n", encoding="utf-8")
    # Non-matching (no pack.yml) should be ignored.
    (packs_dir / "ghost").mkdir(parents=True, exist_ok=True)

    discovery = SetupDiscovery(repo / ".edison" / "config", repo)
    found = discovery.discover_packs()
    assert "alpha" in found
    assert "beta" in found
    assert "ghost" not in found

def test_discover_orchestrators_reads_profiles(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    orch_cfg = {
        "orchestrators": {
            "profiles": {
                "claude": {"command": "claude"},
                "cursor": {"command": "cursor"},
                "codex": {"command": "codex"},
            }
        }
    }
    write_yaml(repo / ".edison" / "config" / "orchestrators.yaml", orch_cfg)

    discovery = SetupDiscovery(repo / ".edison" / "config", repo)
    found = discovery.discover_orchestrators()
    # Core may define additional orchestrator profiles; ensure our configured
    # orchestrators are present.
    assert "claude" in found
    assert "cursor" in found
    assert "codex" in found

def test_discover_orchestrators_falls_back_when_missing(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    discovery = SetupDiscovery(repo / ".edison" / "config", repo)
    found = discovery.discover_orchestrators()
    assert "claude" in found

def test_discover_validators_merges_core_and_packs(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    core_cfg = {
        "validation": {
            "roster": {
                "global": [{"id": "core-global"}],
                "critical": [{"id": "core-critical"}],
            }
        }
    }
    write_yaml(repo / ".edison" / "config" / "validators.yaml", core_cfg)

    pack_cfg = {"validation": {"roster": {"specialized": [{"id": "pack-val"}]}}}
    pack_path = repo / ".edison" / "packs" / "alpha" / "config" / "validators.yml"
    write_yaml(pack_path, pack_cfg)
    # Enable the pack so ConfigManager includes its config overlays.
    write_yaml(repo / ".edison" / "config" / "packs.yml", {"packs": {"enabled": ["alpha"]}})
    (repo / ".edison" / "packs" / "alpha").mkdir(parents=True, exist_ok=True)
    (repo / ".edison" / "packs" / "alpha" / "pack.yml").write_text(
        "name: alpha\nversion: 0.0.0\ndescription: alpha\n", encoding="utf-8"
    )

    discovery = SetupDiscovery(repo / ".edison" / "config", repo)
    found = discovery.discover_validators(["alpha"])
    assert "core-global" in found
    assert "core-critical" in found
    assert "pack-val" in found

def test_discover_agents_combines_sources(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    core_cfg = {"agents": [{"id": "core-agent"}]}
    write_yaml(repo / ".edison" / "config" / "agents.yaml", core_cfg)

    pack_cfg = {"agents": [{"id": "pack-agent"}, {"id": "core-agent"}]}
    write_yaml(repo / ".edison" / "packs" / "alpha" / "config" / "agents.yml", pack_cfg)
    (repo / ".edison" / "packs" / "alpha").mkdir(parents=True, exist_ok=True)
    (repo / ".edison" / "packs" / "alpha" / "pack.yml").write_text(
        "name: alpha\nversion: 0.0.0\ndescription: alpha\n", encoding="utf-8"
    )

    discovery = SetupDiscovery(repo / ".edison" / "config", repo)
    found = discovery.discover_agents(["alpha"])
    assert "core-agent" in found
    assert "pack-agent" in found

def test_detect_project_name_prefers_package_json(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    write_json(repo / "package.json", {"name": "sample-app"})
    discovery = SetupDiscovery(repo / ".edison" / "config", repo)
    assert discovery.detect_project_name() == "sample-app"

def test_detect_project_type_uses_heuristics(isolated_project_env: Path) -> None:
    repo = isolated_project_env
    write_json(repo / "package.json", {"dependencies": {"next": "14.0.0"}})
    discovery = SetupDiscovery(repo / ".edison" / "config", repo)
    # Setup currently offers only generic project types; unknown heuristics
    # should fall back to "Other".
    assert discovery.detect_project_type() == "Other"

    # Rust detection when package.json absent or non-next
    (repo / "package.json").unlink()
    (repo / "Cargo.toml").write_text("[package]\nname='rusty'\n", encoding="utf-8")
    discovery = SetupDiscovery(repo / ".edison" / "config", repo)
    assert discovery.detect_project_type() == "Rust Project"
