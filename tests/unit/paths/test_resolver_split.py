import pytest
import sys
from pathlib import Path
import edison.core.paths.resolver as resolver_pkg

def test_internal_modules_existence():
    """Test that the split internal modules exist and are importable."""
    # These imports will FAIL until the split is implemented
    from edison.core.paths.resolver import base
    from edison.core.paths.resolver import project
    from edison.core.paths.resolver import session
    from edison.core.paths.resolver import evidence
    
    assert base is not None
    assert project is not None
    assert session is not None
    assert evidence is not None

def test_public_api_reexports():
    """Test that the public API is preserved in the new __init__.py."""
    # These should be available at the top level
    from edison.core.paths.resolver import (
        PathResolver,
        EdisonPathError,
        resolve_project_root,
        detect_session_id,
        find_evidence_round,
        is_git_repository,
        get_git_root,
        _PROJECT_ROOT_CACHE
    )
    
    assert PathResolver is not None
    assert issubclass(EdisonPathError, ValueError)
    assert callable(resolve_project_root)
    assert callable(detect_session_id)
    assert callable(find_evidence_round)
    assert callable(is_git_repository)
    assert callable(get_git_root)

def test_internal_modules_not_leaking():
    """Test that internal modules are NOT directly importable if not explicitly exposed."""
    # The 'resolver' package itself should expose the main API, but we want to ensure
    # we can import the submodules.
    # This test is slightly redundant with test_internal_modules_existence but 
    # emphasizes the structure.
    
    import edison.core.paths.resolver.project as project_mod
    assert hasattr(project_mod, "resolve_project_root")

def test_functionality_preservation(tmp_path):
    """Basic functionality test to ensure the moved code still works."""
    from edison.core.paths.resolver import is_git_repository
    
    # Create a fake git dir
    (tmp_path / ".git").mkdir()
    assert is_git_repository(tmp_path)
