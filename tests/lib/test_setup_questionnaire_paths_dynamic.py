import pytest
from pathlib import Path
from edison.cli.setup.questionnaire import SetupQuestionnaire
from edison.core.utils.paths.project import DEFAULT_PROJECT_CONFIG_PRIMARY

def test_questionnaire_defaults_to_edison_config_dir(tmp_path):
    """Test that SetupQuestionnaire defaults to .edison, not .agents."""
    # Arrange
    repo = tmp_path / "repo"
    repo.mkdir()
    core = repo / ".edison" / "core"
    core.mkdir(parents=True)

    # Mock a setup.yaml so the questionnaire can load something
    config_dir = core / "config"
    config_dir.mkdir()
    (config_dir / "setup.yaml").write_text("setup: {basic: []}")

    # Act
    q = SetupQuestionnaire(repo_root=repo, edison_core=core)

    # Run with empty answers to trigger defaults
    answers = q.run("basic", provided_answers={})

    # Assert - Check via the public API (render_modular_configs uses context internally)
    # We use the context module's build_context_with_defaults to verify
    from edison.cli.setup.questionnaire.context import build_context_with_defaults
    context = build_context_with_defaults(q, {})

    assert context["project_config_dir"] == DEFAULT_PROJECT_CONFIG_PRIMARY
    assert context["project_config_dir"] != ".agents"

def test_render_modular_configs_uses_correct_default(tmp_path):
    """Test that rendered defaults.yml contains the correct config_dir."""
    # Arrange
    repo = tmp_path / "repo"
    repo.mkdir()
    core = repo / ".edison" / "core"
    core.mkdir(parents=True)
    (core / "config").mkdir()
    (core / "config" / "setup.yaml").write_text("setup: {basic: []}")
    
    q = SetupQuestionnaire(repo_root=repo, edison_core=core)
    
    # Act
    configs = q.render_modular_configs({})
    
    # Assert
    defaults_yml = configs["defaults.yml"]
    assert f"config_dir: {DEFAULT_PROJECT_CONFIG_PRIMARY}" in defaults_yml
    assert "config_dir: .agents" not in defaults_yml
