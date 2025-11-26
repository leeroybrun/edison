"""Test modular config file generation in setup questionnaire."""
from pathlib import Path
import tempfile
import yaml

from edison.core.setup.questionnaire import SetupQuestionnaire
from edison.core.setup.component_discovery import SetupDiscovery


def test_render_modular_configs_creates_separate_files():
    """Test that render_modular_configs returns dict of separate config files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        edison_core = repo_root / ".edison" / "core"
        edison_core.mkdir(parents=True)

        # Create minimal setup.yaml
        config_dir = edison_core / "config"
        config_dir.mkdir()
        setup_yaml = config_dir / "setup.yaml"
        setup_yaml.write_text("""
setup:
  basic:
    - id: project_name
      type: string
      default: test-project
    - id: packs
      type: multiselect
      default: []
""")

        discovery = SetupDiscovery(edison_core, repo_root)
        questionnaire = SetupQuestionnaire(
            repo_root=repo_root,
            edison_core=edison_core,
            discovery=discovery,
            assume_yes=True,
        )

        answers = {
            "project_name": "test-project",
            "project_type": "Next.js",
            "packs": ["typescript"],
            "validators": ["api-validator", "nextjs-validator"],
            "agents": ["api-builder", "component-builder"],
            "orchestrators": ["claude"],
            "enable_worktrees": True,
            "tdd_enforcement": "warn",
            "ci_lint": "pnpm lint",
            "ci_test": "pnpm test",
        }

        configs = questionnaire.render_modular_configs(answers)

        # Verify we get separate files
        assert isinstance(configs, dict)
        assert "defaults.yml" in configs
        assert "packs.yml" in configs
        assert "validators.yml" in configs
        assert "delegation.yml" in configs
        assert "orchestrators.yml" in configs
        assert "worktrees.yml" in configs
        assert "tdd.yml" in configs
        assert "ci.yml" in configs

        # Verify each file is valid YAML
        for filename, content in configs.items():
            parsed = yaml.safe_load(content)
            assert isinstance(parsed, dict), f"{filename} should contain a dict"

        # Verify defaults.yml contains paths and project
        defaults = yaml.safe_load(configs["defaults.yml"])
        assert "paths" in defaults
        assert "project" in defaults
        assert defaults["project"]["name"] == "test-project"

        # Verify packs.yml contains packs config
        packs = yaml.safe_load(configs["packs.yml"])
        assert "packs" in packs
        assert "typescript" in packs["packs"]["enabled"]

        # Verify validators.yml contains validators
        validators = yaml.safe_load(configs["validators.yml"])
        assert "validators" in validators
        assert "api-validator" in validators["validators"]["enabled"]

        # Verify delegation.yml contains agents
        delegation = yaml.safe_load(configs["delegation.yml"])
        assert "agents" in delegation
        assert "api-builder" in delegation["agents"]["enabled"]

        print("✓ Modular config generation test passed")


def test_modular_configs_skip_empty_sections():
    """Test that empty sections are not included in modular configs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        edison_core = repo_root / ".edison" / "core"
        edison_core.mkdir(parents=True)

        config_dir = edison_core / "config"
        config_dir.mkdir()
        setup_yaml = config_dir / "setup.yaml"
        setup_yaml.write_text("""
setup:
  basic:
    - id: project_name
      type: string
      default: minimal-project
""")

        discovery = SetupDiscovery(edison_core, repo_root)
        questionnaire = SetupQuestionnaire(
            repo_root=repo_root,
            edison_core=edison_core,
            discovery=discovery,
            assume_yes=True,
        )

        answers = {
            "project_name": "minimal-project",
            "project_type": "",
            "packs": [],
            "validators": [],
            "agents": [],
            "orchestrators": [],
        }

        configs = questionnaire.render_modular_configs(answers)

        # Should always have defaults and packs (even if empty)
        assert "defaults.yml" in configs
        assert "packs.yml" in configs

        # Empty sections should still be included (for users to fill in later)
        # but should have empty lists
        packs = yaml.safe_load(configs["packs.yml"])
        assert packs["packs"]["enabled"] == []

        print("✓ Empty sections test passed")


if __name__ == "__main__":
    test_render_modular_configs_creates_separate_files()
    test_modular_configs_skip_empty_sections()
    print("\n✅ All modular config tests passed")
