
import pytest
from pathlib import Path
from edison.core.composition import formatting, state_machine, constitution, rosters, composers
from edison.core.config import ConfigManager

class MockConfigManager:
    def __init__(self, repo_root):
        self.repo_root = repo_root
        self.core_config_dir = repo_root / ".edison" / "config"
        self.project_config_dir = repo_root / ".edison" / "config" # simplified
        self.config = {"packs": {"active": []}}

    def load_config(self, validate=False):
        return self.config
    
    def load_yaml(self, path):
        if "state-machine" in str(path):
            return {"statemachine": {"core": {"states": {"init": {"initial": True}}}}}
        if "constitution" in str(path):
            return {}
        return {}

    def deep_merge(self, a, b):
        return a
    
    def validate_schema(self, *args):
        pass

class MockEngine:
    def __init__(self, repo_root):
        self.repo_root = repo_root
        self.config = {}
        self.project_dir = repo_root
        self.core_dir = repo_root / ".edison" / "core"
        self.active_packs = []
    
    def _active_packs(self):
        return []
    
    def resolve_includes(self, text, path):
        return text
        
    def _overlay_path_for_role(self, role):
        return None

@pytest.fixture
def mock_env(tmp_path):
    (tmp_path / ".edison" / "config").mkdir(parents=True)
    (tmp_path / "src" / "edison" / "data").mkdir(parents=True)
    (tmp_path / "constitutions").mkdir(parents=True)
    return tmp_path

def test_formatting_compose_zen_prompts(mock_env):
    engine = MockEngine(mock_env)
    out_dir = mock_env / "zen_prompts"
    
    # Mocking resolve_project_dir_placeholders to avoid external dependencies if needed
    # But looking at the code, it imports it. 
    # formatting.py uses it.
    
    # We need to ensure base templates exist or mock them
    # formatting.compose_for_role reads files.
    # We can mock compose_for_role
    
    original_compose = formatting.compose_for_role
    formatting.compose_for_role = lambda engine, role: f"Content for {role}"
    
    try:
        formatting.compose_zen_prompts(engine, out_dir)
        assert out_dir.exists()
        assert out_dir.is_dir()
        assert (out_dir / "codex.txt").exists()
    finally:
        formatting.compose_for_role = original_compose

def test_state_machine_mkdir(mock_env):
    out_path = mock_env / "docs" / "STATE.md"
    # Needs config manager with state machine
    cfg_mgr = MockConfigManager(mock_env)
    
    # Ensure core config exists
    (mock_env / ".edison" / "config" / "state-machine.yaml").write_text("statemachine: {}")
    
    # Mocking _load_state_machine to return data directly to avoid file IO issues
    original_load = state_machine._load_state_machine
    state_machine._load_state_machine = lambda c: {"core": {"states": {}}}
    
    try:
        state_machine.generate_state_machine_doc(out_path, repo_root=mock_env)
        assert out_path.parent.exists()
        assert out_path.exists()
    finally:
        state_machine._load_state_machine = original_load

def test_constitution_mkdir(mock_env):
    out_dir = mock_env / "generated"
    cfg_mgr = MockConfigManager(mock_env)
    
    # Mock compose_constitution
    orig_compose = constitution.compose_constitution
    constitution.compose_constitution = lambda role, config: "Constituion Content"
    
    try:
        constitution.generate_all_constitutions(cfg_mgr, out_dir)
        assert (out_dir / "constitutions").exists()
        assert (out_dir / "constitutions" / "ORCHESTRATORS.md").exists()
    finally:
        constitution.compose_constitution = orig_compose

def test_rosters_mkdir(mock_env):
    out_path_agents = mock_env / "docs" / "AGENTS.md"
    out_path_validators = mock_env / "docs" / "VALIDATORS.md"
    
    # Mock Registries
    orig_agent_reg = rosters.AgentRegistry
    orig_val_reg = rosters.ValidatorRegistry
    
    class MockReg:
        def __init__(self, repo_root=None):
            self.repo_root = repo_root
        def get_all(self):
            return {}
        def get(self, name):
            return {}

    rosters.AgentRegistry = MockReg
    rosters.ValidatorRegistry = MockReg
    
    try:
        rosters.generate_available_agents(out_path_agents, repo_root=mock_env)
        assert out_path_agents.parent.exists()
        
        rosters.generate_available_validators(out_path_validators, repo_root=mock_env)
        assert out_path_validators.parent.exists()
    finally:
        rosters.AgentRegistry = orig_agent_reg
        rosters.ValidatorRegistry = orig_val_reg

