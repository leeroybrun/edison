import pytest
import yaml
from pathlib import Path
from edison.core.session import validation
from edison.core.session.config import SessionConfig
from edison.core.exceptions import ValidationError

@pytest.fixture
def project_root(tmp_path, monkeypatch):
    """
    Sets up a temporary project root.
    """
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
    
    # Reload configs
    validation._CONFIG = SessionConfig()
    
    return tmp_path

def test_validate_session_id_format(project_root):
    """Test session ID format validation."""
    # Valid
    assert validation.validate_session_id_format("valid-id") is True
    
    # Invalid chars
    with pytest.raises(ValidationError) as exc:
        validation.validate_session_id_format("Invalid_ID")
    assert "pattern" in str(exc.value)
    
    # Too long
    with pytest.raises(ValidationError) as exc:
        validation.validate_session_id_format("a" * 33)
    assert "length" in str(exc.value)

def test_validate_session_structure(project_root):
    """Test session structure validation (placeholder)."""
    # This might check if required keys exist in a session dict
    sess = {"meta": {"owner": "me"}, "state": "active"}
    assert validation.validate_session_structure(sess) is True
    
    sess_bad = {"meta": {}} # Missing owner?
    # Define what is required.
    # For now, let's say 'state' is required.
    with pytest.raises(ValidationError):
        validation.validate_session_structure({})
