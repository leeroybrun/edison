import pytest
import yaml
from pathlib import Path
from edison.core.session.id import validate_session_id, SessionIdError
from edison.core.exceptions import ValidationError


# Wrapper function to match old behavior
def validate_session_id_format(session_id: str) -> bool:
    """Validate session ID format, raising ValidationError on failure."""
    try:
        validate_session_id(session_id)
        return True
    except SessionIdError as e:
        raise ValidationError(str(e)) from e


def validate_session_structure(sess: dict) -> bool:
    """Validate session structure has required fields."""
    if "state" not in sess:
        raise ValidationError("Missing required 'state' field")
    return True


@pytest.fixture(autouse=True)
def setup_session_validation_config(project_root):
    """Setup custom session validation config for these tests."""
    config_dir = project_root / ".edison" / "config"
    session_data = {
        "session": {
            "validation": {
                "idRegex": r"^[a-z0-9-]+$",
                "maxLength": 32
            }
        }
    }
    (config_dir / "session.yml").write_text(yaml.dump(session_data))

    # Clear cache to pick up new config
    from edison.core.config.cache import clear_all_caches
    from edison.core.session._config import reset_config_cache
    clear_all_caches()
    reset_config_cache()

def test_validate_session_id_format(project_root):
    """Test session ID format validation."""
    # Valid
    assert validate_session_id_format("valid-id") is True
    
    # Invalid chars (uppercase not allowed by idRegex: ^[a-z0-9-]+$)
    with pytest.raises(ValidationError) as exc:
        validate_session_id_format("Invalid_ID")
    # Check error message mentions pattern or invalid
    error_msg = str(exc.value).lower()
    assert "invalid" in error_msg or "pattern" in error_msg or "characters" in error_msg
    
    # Too long
    with pytest.raises(ValidationError) as exc:
        validate_session_id_format("a" * 33)
    # Check error message mentions length or long
    error_msg = str(exc.value).lower()
    assert "long" in error_msg or "length" in error_msg or "characters" in error_msg

def test_validate_session_structure(project_root):
    """Test session structure validation (placeholder)."""
    # This checks if required keys exist in a session dict
    sess = {"meta": {"owner": "me"}, "state": "active"}
    assert validate_session_structure(sess) is True

    # Missing 'state' field should raise error
    with pytest.raises(ValidationError):
        validate_session_structure({})
