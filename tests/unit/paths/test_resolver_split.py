"""Test that the paths utilities are properly structured after refactoring."""
import pytest
import sys
from pathlib import Path


def test_utils_paths_public_api():
    """Test that the public API is preserved in utils/paths/."""
    from edison.core.utils.paths import (
        PathResolver,
        EdisonPathError,
        resolve_project_root,
        get_management_paths,
        get_project_config_dir,
        find_evidence_round,
        list_evidence_rounds,
        _PROJECT_ROOT_CACHE,
    )
    
    assert PathResolver is not None
    assert issubclass(EdisonPathError, ValueError)
    assert callable(resolve_project_root)
    assert callable(get_management_paths)
    assert callable(get_project_config_dir)
    assert callable(find_evidence_round)
    assert callable(list_evidence_rounds)


def test_utils_git_public_api():
    """Test that git utilities are available in utils/git/."""
    from edison.core.utils.git import (
        is_git_repository,
        get_git_root,
        get_repo_root,
        get_current_branch,
        is_clean_working_tree,
        is_worktree,
        get_worktree_parent,
        get_worktree_info,
        get_changed_files,
    )
    
    assert callable(is_git_repository)
    assert callable(get_git_root)
    assert callable(get_repo_root)
    assert callable(get_current_branch)


def test_session_id_detection_moved():
    """Test that session ID detection is available in session/id.py."""
    from edison.core.session.core.id import (
        validate_session_id,
        detect_session_id,
        SessionIdError,
    )
    
    assert callable(validate_session_id)
    assert callable(detect_session_id)
    assert issubclass(SessionIdError, ValueError)


def test_is_git_repository_functionality(tmp_path):
    """Basic functionality test to ensure git utilities work."""
    from edison.core.utils.git import is_git_repository

    # Create a real git repository
    from tests.helpers.fixtures import create_repo_with_git
    create_repo_with_git(tmp_path)
    assert is_git_repository(tmp_path)
