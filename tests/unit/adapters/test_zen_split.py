import pytest
import types
from pathlib import Path
import edison.core.adapters.platforms.zen as zen_pkg
from edison.core.adapters import ZenAdapter, WORKFLOW_HEADING

def test_zen_is_package():
    """Verify that edison.core.adapters.platforms.zen is a package, not a single file."""
    # If it is a package, it must have a __path__ attribute.
    # A single .py module does NOT have __path__.
    assert hasattr(zen_pkg, "__path__"), "edison.core.adapters.platforms.zen should be a package (directory)"

def test_zensync_imports_and_structure():
    """Verify that ZenAdapter is importable and has expected methods."""
    assert WORKFLOW_HEADING == "## Edison Workflow Loop"
    
    # Instantiate ZenAdapter (requires some mocking or dummy args usually, but __init__ creates objects)
    # We can pass None to repo_root and config as they are optional in __init__ signature
    # based on the source code: def __init__(self, repo_root: Optional[Path] = None, config: Optional[Dict[str, Any]] = None) -> None:
    
    # However, __init__ does:
    # root = repo_root.resolve() if repo_root else PathResolver.resolve_project_root()
    # cfg_mgr = ConfigManager(root)
    # ...
    # This might fail if not in a project root or if dependencies are missing.
    # So we might need to mock PathResolver or just check method existence on the class.
    
    assert hasattr(ZenAdapter, "get_applicable_guidelines")
    assert hasattr(ZenAdapter, "get_applicable_rules")
    assert hasattr(ZenAdapter, "compose_zen_prompt")
    assert hasattr(ZenAdapter, "sync_role_prompts")
    assert hasattr(ZenAdapter, "verify_cli_prompts")

def test_zensync_instantiation(tmp_path):
    """Verify basic instantiation works."""
    # We pass a tmp_path as repo_root to avoid it trying to find real project root
    # and to keep it isolated.
    zs = ZenAdapter(project_root=tmp_path, config={})
    assert zs.project_root == tmp_path
    assert isinstance(zs.config, dict)
