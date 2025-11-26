"""Tests for output configuration loader.

All tests use isolated tmp folders - NO MOCKS.
"""

from pathlib import Path

import pytest

from edison.core.composition.output_config import (
    OutputConfigLoader,
    get_output_config,
)


def _create_minimal_project(tmp_path: Path) -> Path:
    """Create a minimal project structure for testing."""
    project_config_dir = tmp_path / ".edison"
    project_config_dir.mkdir(parents=True)
    return project_config_dir


def _write_composition_yaml(project_config_dir: Path, content: str) -> Path:
    """Write a composition.yaml file to project config dir."""
    composition_path = project_config_dir / "composition.yaml"
    composition_path.write_text(content, encoding="utf-8")
    return composition_path


# =============================================================================
# Default Configuration Tests
# =============================================================================

def test_output_config_loader_loads_defaults(tmp_path: Path) -> None:
    """OutputConfigLoader should load default configuration from core data."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    
    outputs = loader.get_outputs_config()
    
    assert "canonical_entry" in outputs
    assert "clients" in outputs
    assert "constitutions" in outputs
    assert "agents" in outputs
    assert "validators" in outputs


def test_canonical_entry_config_defaults(tmp_path: Path) -> None:
    """Canonical entry should have sensible defaults from core config."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_canonical_entry_config()
    
    assert cfg.enabled is True
    assert cfg.output_path == "."
    assert cfg.filename == "AGENTS.md"


def test_client_config_claude_defaults(tmp_path: Path) -> None:
    """Claude client should be enabled by default."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_client_config("claude")
    
    assert cfg is not None
    assert cfg.enabled is True
    assert cfg.filename == "CLAUDE.md"
    assert cfg.output_path == ".claude"


def test_client_config_codex_disabled_by_default(tmp_path: Path) -> None:
    """Codex client should be disabled by default."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_client_config("codex")
    
    assert cfg is not None
    assert cfg.enabled is False


def test_agents_config_defaults(tmp_path: Path) -> None:
    """Agents config should have sensible defaults."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_agents_config()
    
    assert cfg.enabled is True
    assert "{{PROJECT_EDISON_DIR}}" in cfg.output_path
    assert cfg.filename_pattern == "{name}.md"


def test_validators_config_defaults(tmp_path: Path) -> None:
    """Validators config should have sensible defaults."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_validators_config()
    
    assert cfg.enabled is True
    assert "{{PROJECT_EDISON_DIR}}" in cfg.output_path
    assert cfg.filename_pattern == "{name}.md"


def test_get_enabled_clients_returns_only_enabled(tmp_path: Path) -> None:
    """get_enabled_clients should only return enabled clients."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    enabled = loader.get_enabled_clients()
    
    # Claude and Zen are enabled by default
    assert "claude" in enabled
    assert "zen" in enabled
    # Codex and Cursor are disabled by default
    assert "codex" not in enabled
    assert "cursor" not in enabled


# =============================================================================
# Project Override Tests
# =============================================================================

def test_project_config_override_disables_client(tmp_path: Path) -> None:
    """Project config should override core defaults - disable client."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    _write_composition_yaml(project_config_dir, """
outputs:
  clients:
    claude:
      enabled: false
      filename: "MY_CLAUDE.md"
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_client_config("claude")
    
    assert cfg is not None
    assert cfg.enabled is False
    assert cfg.filename == "MY_CLAUDE.md"


def test_project_config_override_changes_canonical_entry(tmp_path: Path) -> None:
    """Project config should allow changing canonical entry filename and path."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    _write_composition_yaml(project_config_dir, """
outputs:
  canonical_entry:
    filename: "AGENTS_COMPOSED.md"
    output_path: "docs"
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_canonical_entry_config()
    
    assert cfg.filename == "AGENTS_COMPOSED.md"
    assert cfg.output_path == "docs"


def test_project_config_override_enables_disabled_client(tmp_path: Path) -> None:
    """Project config should allow enabling a disabled client."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    _write_composition_yaml(project_config_dir, """
outputs:
  clients:
    codex:
      enabled: true
      output_path: "~/.codex/prompts"
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_client_config("codex")
    
    assert cfg is not None
    assert cfg.enabled is True
    assert cfg.output_path == "~/.codex/prompts"


def test_project_config_override_custom_agent_pattern(tmp_path: Path) -> None:
    """Project config should allow custom filename patterns for agents."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    _write_composition_yaml(project_config_dir, """
outputs:
  agents:
    output_path: ".ai/agents"
    filename_pattern: "{name}-agent.md"
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_agents_config()
    
    assert cfg.output_path == ".ai/agents"
    assert cfg.filename_pattern == "{name}-agent.md"


# =============================================================================
# Path Resolution Tests
# =============================================================================

def test_resolve_path_with_placeholder(tmp_path: Path) -> None:
    """Path resolver should replace {{PROJECT_EDISON_DIR}} placeholder."""
    project_config_dir = tmp_path / ".custom-edison"
    project_config_dir.mkdir()
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    
    resolved = loader._resolve_path("{{PROJECT_EDISON_DIR}}/_generated/agents")
    
    assert resolved == project_config_dir / "_generated" / "agents"


def test_resolve_path_relative_to_repo_root(tmp_path: Path) -> None:
    """Relative paths should resolve relative to repo root."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    
    resolved = loader._resolve_path(".claude/agents")
    
    assert resolved == tmp_path / ".claude" / "agents"


def test_resolve_path_absolute_unchanged(tmp_path: Path) -> None:
    """Absolute paths should remain unchanged."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    
    resolved = loader._resolve_path("/absolute/path/to/agents")
    
    assert resolved == Path("/absolute/path/to/agents")


def test_get_agent_path_uses_config(tmp_path: Path) -> None:
    """get_agent_path should use config to build full path."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_agent_path("feature-implementer")
    
    assert path is not None
    assert path.name == "feature-implementer.md"
    assert "_generated/agents" in str(path) or "_generated" in str(path)


def test_get_agent_path_with_custom_pattern(tmp_path: Path) -> None:
    """get_agent_path should use custom filename pattern from config."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    _write_composition_yaml(project_config_dir, """
outputs:
  agents:
    filename_pattern: "{name}-prompt.md"
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_agent_path("feature-implementer")
    
    assert path is not None
    assert path.name == "feature-implementer-prompt.md"


def test_get_validator_path_uses_config(tmp_path: Path) -> None:
    """get_validator_path should use config to build full path."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_validator_path("security")
    
    assert path is not None
    assert path.name == "security.md"


def test_get_canonical_entry_path_uses_config(tmp_path: Path) -> None:
    """get_canonical_entry_path should use config to build full path."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_canonical_entry_path()
    
    assert path is not None
    assert path == tmp_path / "AGENTS.md"


def test_get_canonical_entry_path_with_custom_config(tmp_path: Path) -> None:
    """get_canonical_entry_path should respect custom config."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    _write_composition_yaml(project_config_dir, """
outputs:
  canonical_entry:
    output_path: "docs"
    filename: "AI_AGENTS.md"
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_canonical_entry_path()
    
    assert path is not None
    assert path == tmp_path / "docs" / "AI_AGENTS.md"


def test_get_canonical_entry_path_returns_none_when_disabled(tmp_path: Path) -> None:
    """get_canonical_entry_path should return None when disabled."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    _write_composition_yaml(project_config_dir, """
outputs:
  canonical_entry:
    enabled: false
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_canonical_entry_path()
    
    assert path is None


def test_get_client_path_uses_config(tmp_path: Path) -> None:
    """get_client_path should use config to build full path."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_client_path("claude")
    
    assert path is not None
    assert path == tmp_path / ".claude" / "CLAUDE.md"


def test_get_client_path_returns_none_when_disabled(tmp_path: Path) -> None:
    """get_client_path should return None for disabled clients."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_client_path("codex")  # Disabled by default
    
    assert path is None


# =============================================================================
# Sync Configuration Tests
# =============================================================================

def test_sync_config_claude_defaults(tmp_path: Path) -> None:
    """Claude sync config should have sensible defaults."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_sync_config("claude")
    
    assert cfg is not None
    assert cfg.enabled is True
    assert cfg.agents_path == ".claude/agents"
    assert cfg.agents_filename_pattern == "{name}.md"


def test_sync_config_zen_defaults(tmp_path: Path) -> None:
    """Zen sync config should have sensible defaults."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_sync_config("zen")
    
    assert cfg is not None
    assert cfg.enabled is True
    assert cfg.prompts_path == ".zen/conf/systemprompts/clink"


def test_get_sync_agents_dir_uses_config(tmp_path: Path) -> None:
    """get_sync_agents_dir should use config to build path."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_sync_agents_dir("claude")
    
    assert path is not None
    assert path == tmp_path / ".claude" / "agents"


def test_get_sync_agents_dir_with_custom_config(tmp_path: Path) -> None:
    """get_sync_agents_dir should respect custom config."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    _write_composition_yaml(project_config_dir, """
outputs:
  sync:
    claude:
      agents_path: ".ai/claude-agents"
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_sync_agents_dir("claude")
    
    assert path is not None
    assert path == tmp_path / ".ai" / "claude-agents"


# =============================================================================
# Constitution Configuration Tests
# =============================================================================

def test_constitution_path_orchestrators(tmp_path: Path) -> None:
    """get_constitution_path should return correct path for orchestrators."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_constitution_path("orchestrators")
    
    assert path is not None
    assert path.name == "ORCHESTRATORS.md"


def test_constitution_path_agents(tmp_path: Path) -> None:
    """get_constitution_path should return correct path for agents."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_constitution_path("agents")
    
    assert path is not None
    assert path.name == "AGENTS.md"


def test_constitution_path_validators(tmp_path: Path) -> None:
    """get_constitution_path should return correct path for validators."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_constitution_path("validators")
    
    assert path is not None
    assert path.name == "VALIDATORS.md"


def test_constitution_path_returns_none_when_disabled(tmp_path: Path) -> None:
    """get_constitution_path should return None when constitutions disabled."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    _write_composition_yaml(project_config_dir, """
outputs:
  constitutions:
    enabled: false
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_constitution_path("orchestrators")
    
    assert path is None


def test_constitution_path_individual_role_disabled(tmp_path: Path) -> None:
    """get_constitution_path should return None when specific role disabled."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    _write_composition_yaml(project_config_dir, """
outputs:
  constitutions:
    files:
      validators:
        enabled: false
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    
    # Validators disabled
    val_path = loader.get_constitution_path("validators")
    assert val_path is None
    
    # Others still enabled
    orch_path = loader.get_constitution_path("orchestrators")
    assert orch_path is not None


# =============================================================================
# Guidelines Configuration Tests
# =============================================================================

def test_guidelines_config_defaults(tmp_path: Path) -> None:
    """Guidelines config should have sensible defaults."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    cfg = loader.get_guidelines_config()
    
    assert cfg.enabled is True
    assert cfg.preserve_structure is True


def test_get_guidelines_dir_uses_config(tmp_path: Path) -> None:
    """get_guidelines_dir should use config to build path."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_guidelines_dir()
    
    assert path is not None
    assert "_generated/guidelines" in str(path)


def test_get_guidelines_dir_returns_none_when_disabled(tmp_path: Path) -> None:
    """get_guidelines_dir should return None when guidelines disabled."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    _write_composition_yaml(project_config_dir, """
outputs:
  guidelines:
    enabled: false
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    path = loader.get_guidelines_dir()
    
    assert path is None


# =============================================================================
# Convenience Function Tests
# =============================================================================

def test_get_output_config_convenience_function(tmp_path: Path) -> None:
    """get_output_config should return a loader instance."""
    loader = get_output_config(repo_root=tmp_path)
    
    assert isinstance(loader, OutputConfigLoader)
    assert loader.repo_root == tmp_path


# =============================================================================
# Deep Merge Tests
# =============================================================================

def test_deep_merge_preserves_unset_values(tmp_path: Path) -> None:
    """Deep merge should preserve core values not overridden by project."""
    project_config_dir = _create_minimal_project(tmp_path)
    
    # Only override one client, others should remain from core
    _write_composition_yaml(project_config_dir, """
outputs:
  clients:
    claude:
      filename: "CUSTOM_CLAUDE.md"
""")
    
    loader = OutputConfigLoader(repo_root=tmp_path, project_config_dir=project_config_dir)
    
    # Claude filename changed
    claude_cfg = loader.get_client_config("claude")
    assert claude_cfg.filename == "CUSTOM_CLAUDE.md"
    # But claude is still enabled (from core defaults)
    assert claude_cfg.enabled is True
    
    # Zen unchanged (not in project config)
    zen_cfg = loader.get_client_config("zen")
    assert zen_cfg.enabled is True
    assert zen_cfg.filename == "zen.md"
