import pytest
import yaml
from pathlib import Path
from edison.core.session import validation
from edison.core.session._config import reset_config_cache
from edison.core.config.cache import clear_all_caches
from edison.core.exceptions import ValidationError
import edison.core.utils.paths.resolver as path_resolver

@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """
    Sets up a temporary project root.
    """
    # Reset ALL caches first
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

    # Setup .edison/core/config
    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True)
    
    defaults_data = {"edison": {"version": "1.0.0"}}
    (config_dir / "defaults.yaml").write_text(yaml.dump(defaults_data))
    
    session_data = {
        "session": {
            "validation": {
                "idRegex": r"^[a-z0-9-]+$",
                "maxLength": 32
            }
        }
    }
    (config_dir / "session.yaml").write_text(yaml.dump(session_data))
    
    # Set env vars
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("project_ROOT", str(tmp_path))
    
    # Reset caches AFTER env vars are set
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()
    
    yield tmp_path

    # Cleanup
    path_resolver._PROJECT_ROOT_CACHE = None
    clear_all_caches()
    reset_config_cache()

def test_validate_session_id_format(project_root):
    """Test session ID format validation."""
    # Valid
    assert validation.validate_session_id_format("valid-id") is True
    
    # Invalid chars (uppercase not allowed by idRegex: ^[a-z0-9-]+$)
    with pytest.raises(ValidationError) as exc:
        validation.validate_session_id_format("Invalid_ID")
    # Check error message mentions pattern or invalid
    error_msg = str(exc.value).lower()
    assert "invalid" in error_msg or "pattern" in error_msg or "characters" in error_msg
    
    # Too long
    with pytest.raises(ValidationError) as exc:
        validation.validate_session_id_format("a" * 33)
    # Check error message mentions length or long
    error_msg = str(exc.value).lower()
    assert "long" in error_msg or "length" in error_msg or "characters" in error_msg

def test_validate_session_structure(project_root):
    """Test session structure validation (placeholder)."""
    # This checks if required keys exist in a session dict
    sess = {"meta": {"owner": "me"}, "state": "active"}
    assert validation.validate_session_structure(sess) is True
    
    # Missing 'state' field should raise error
    with pytest.raises(ValidationError):
        validation.validate_session_structure({})
