import pytest
from pathlib import Path
from edison.core.file_io.utils import ensure_dir

def test_ensure_dir_creates_new_directory(tmp_path):
    # Test creating a new directory
    target = tmp_path / "new_dir"
    assert not target.exists()
    
    result = ensure_dir(target)
    
    assert target.exists()
    assert target.is_dir()
    assert result == target

def test_ensure_dir_is_idempotent(tmp_path):
    # Test calling twice doesn't fail
    target = tmp_path / "existing_dir"
    target.mkdir()
    
    result1 = ensure_dir(target)
    result2 = ensure_dir(target)
    
    assert target.exists()
    assert result1 == target
    assert result2 == target

def test_ensure_dir_creates_parent_directories(tmp_path):
    # Test nested/deep/path creation
    target = tmp_path / "deep" / "nested" / "dir"
    assert not target.exists()
    
    result = ensure_dir(target)
    
    assert target.exists()
    assert target.is_dir()
    assert result == target

def test_ensure_dir_returns_path_for_chaining(tmp_path):
    # Test return value is the path
    target = tmp_path / "chain_test"
    
    returned = ensure_dir(target)
    assert isinstance(returned, Path)
    assert returned == target
