
import pytest
from pathlib import Path
from edison.core.ide import settings
from edison.core.file_io import locking
from edison.core.paths import project
from edison.core.utils import resilience
import json
import shutil

def test_ide_settings_mkdir(tmp_path):
    """Test SettingsComposer creates parent directory for settings.json."""
    (tmp_path / ".edison" / "config").mkdir(parents=True)
    composer = settings.SettingsComposer(repo_root=tmp_path)
    
    # Target: .claude/settings.json
    target = tmp_path / ".claude" / "settings.json"
    assert not target.parent.exists()
    
    composer.write_settings_file()
    
    assert target.parent.exists()
    assert target.exists()

def test_locking_mkdir(tmp_path):
    """Test acquire_file_lock creates parent directory."""
    target = tmp_path / "locks" / "myfile"
    assert not target.parent.exists()
    
    # fail_open=True to avoid waiting/locking issues in test
    with locking.acquire_file_lock(target, fail_open=True, nfs_safe=False):
        pass
        
    assert target.parent.exists()

def test_paths_project_mkdir(tmp_path):
    """Test get_project_config_dir creates directory."""
    # Default is .edison
    target = tmp_path / ".edison"
    if target.exists():
        shutil.rmtree(target)
    
    assert not target.exists()
    
    res = project.get_project_config_dir(tmp_path, create=True)
    
    assert res == target
    assert target.exists()

def test_resilience_mkdir(tmp_path):
    """Test resume_from_recovery creates active directory."""
    # Setup recovery dir
    recovery_root = tmp_path / ".project" / "sessions" / "recovery"
    sid = "sess-rec"
    rec_sess_dir = recovery_root / sid
    rec_sess_dir.mkdir(parents=True)
    (rec_sess_dir / "session.json").write_text("{}")
    
    # Target active dir
    active_root = tmp_path / ".project" / "sessions" / "active"
    assert not active_root.exists()
    
    resilience.resume_from_recovery(rec_sess_dir)
    
    assert active_root.exists()
    assert (active_root / sid).exists()
