"""Test that configure properly merges with existing config files."""
import tempfile
from pathlib import Path
import yaml

from edison.core.config import ConfigManager
from scripts.config.configure import ConfigurationMenu


def test_configure_merges_with_existing_config():
    """Test that changes are merged with existing project config, not replaced."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / ".git").mkdir()

        # Create edison core structure
        edison_core = repo_root / ".edison" / "core"
        config_dir = edison_core / "config"
        config_dir.mkdir(parents=True)

        # Create minimal setup.yaml
        (config_dir / "setup.yaml").write_text("""
setup:
  basic:
    - id: project_name
      type: string
      default: test-project
    - id: packs
      type: multiselect
      default: []
    - id: ci_lint
      type: string
      default: npm run lint
""")

        # Create project config directory with existing config
        project_config_dir = repo_root / ".agents" / "config"
        project_config_dir.mkdir(parents=True)

        # Existing defaults.yml with custom fields
        (project_config_dir / "defaults.yml").write_text("""
paths:
  config_dir: .agents
  management_dir: .project
project:
  name: original-project
  type: Next.js
  custom_field: important-value
  packs:
    - typescript
database:
  engine: postgresql
  custom_db_field: keep-this
""")

        # Existing ci.yml with custom fields
        (project_config_dir / "ci.yml").write_text("""
ci:
  commands:
    lint: pnpm lint
    test: pnpm test
    custom_command: npm run deploy
""")

        # Initialize configure menu
        menu = ConfigurationMenu(repo_root=repo_root, edison_core=edison_core)

        # Make a change: update project name only
        menu.set_value("project_name", "updated-project")

        # Save changes
        result = menu.save_changes(dry_run=False)
        assert result == 0

        # Load saved defaults.yml
        defaults = yaml.safe_load((project_config_dir / "defaults.yml").read_text())

        # Verify the change was applied
        assert defaults["project"]["name"] == "updated-project", "Changed value not saved"

        # Verify custom fields were preserved
        assert defaults["project"]["custom_field"] == "important-value", "Custom project field lost"
        assert defaults["database"]["custom_db_field"] == "keep-this", "Custom database field lost"
        assert defaults["project"]["type"] == "Next.js", "Existing project type lost"
        assert "typescript" in defaults["project"]["packs"], "Existing packs lost"

        # Verify ci.yml was NOT touched (no changes made to it)
        ci = yaml.safe_load((project_config_dir / "ci.yml").read_text())
        assert ci["ci"]["commands"]["custom_command"] == "npm run deploy", "Untouched file was modified"

        print("✓ Configure correctly merges with existing config")


def test_configure_creates_new_file_when_needed():
    """Test that configure creates new domain file if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / ".git").mkdir()

        edison_core = repo_root / ".edison" / "core"
        config_dir = edison_core / "config"
        config_dir.mkdir(parents=True)

        (config_dir / "setup.yaml").write_text("""
setup:
  basic:
    - id: project_name
      type: string
      default: test
    - id: ci_lint
      type: string
      default: lint
""")

        # Create project config directory but NO existing files
        project_config_dir = repo_root / ".agents" / "config"
        project_config_dir.mkdir(parents=True)

        menu = ConfigurationMenu(repo_root=repo_root, edison_core=edison_core)

        # Make a change to CI (file doesn't exist yet)
        menu.set_value("ci_lint", "pnpm lint:strict")

        result = menu.save_changes(dry_run=False)
        assert result == 0

        # Verify ci.yml was created
        assert (project_config_dir / "ci.yml").exists(), "New ci.yml file not created"

        ci = yaml.safe_load((project_config_dir / "ci.yml").read_text())
        assert ci["ci"]["commands"]["lint"] == "pnpm lint:strict", "Value not saved in new file"

        print("✓ Configure creates new files when needed")


def test_configure_handles_multiple_changes_across_domains():
    """Test that changes to multiple domains are saved to correct files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        (repo_root / ".git").mkdir()

        edison_core = repo_root / ".edison" / "core"
        config_dir = edison_core / "config"
        config_dir.mkdir(parents=True)

        (config_dir / "setup.yaml").write_text("""
setup:
  basic:
    - id: project_name
      type: string
      default: test
    - id: packs
      type: multiselect
      default: []
    - id: ci_lint
      type: string
      default: lint
    - id: tdd_enforcement
      type: choice
      options: [strict, warn, off]
      default: warn
""")

        project_config_dir = repo_root / ".agents" / "config"
        project_config_dir.mkdir(parents=True)

        # Existing files with custom fields
        (project_config_dir / "defaults.yml").write_text("""
project:
  name: old-name
  custom: keep-me
""")

        (project_config_dir / "tdd.yml").write_text("""
tdd:
  enforcement: off
  custom_tdd_field: preserve
""")

        menu = ConfigurationMenu(repo_root=repo_root, edison_core=edison_core)

        # Make changes across multiple domains
        menu.set_value("project_name", "new-name")  # defaults.yml
        menu.set_value("ci_lint", "pnpm lint")      # ci.yml (new file)
        menu.set_value("tdd_enforcement", "strict") # tdd.yml (existing)

        result = menu.save_changes(dry_run=False)
        assert result == 0

        # Verify defaults.yml
        defaults = yaml.safe_load((project_config_dir / "defaults.yml").read_text())
        assert defaults["project"]["name"] == "new-name"
        assert defaults["project"]["custom"] == "keep-me", "Custom field in defaults lost"

        # Verify ci.yml was created
        ci = yaml.safe_load((project_config_dir / "ci.yml").read_text())
        assert ci["ci"]["commands"]["lint"] == "pnpm lint"

        # Verify tdd.yml was updated but custom field preserved
        tdd = yaml.safe_load((project_config_dir / "tdd.yml").read_text())
        assert tdd["tdd"]["enforcement"] == "strict"
        assert tdd["tdd"]["custom_tdd_field"] == "preserve", "Custom TDD field lost"

        print("✓ Configure handles multiple changes across domains correctly")


if __name__ == "__main__":
    test_configure_merges_with_existing_config()
    test_configure_creates_new_file_when_needed()
    test_configure_handles_multiple_changes_across_domains()
    print("\n✅ All configure merge tests passed")
