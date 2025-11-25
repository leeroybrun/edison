import sys
from pathlib import Path

# Add Edison core to path (so `import edison.core.*` works)
_THIS_FILE = Path(__file__).resolve()
_CORE_ROOT = None
for _parent in _THIS_FILE.parents:
    candidate = _parent / ".edison" / "core"
    if (candidate / "lib").exists():
        _CORE_ROOT = candidate
        break

if _CORE_ROOT is None:
    _CORE_ROOT = _THIS_FILE.parents[4]

CORE_ROOT = _CORE_ROOT
from edison.core.config import ConfigManager 
from edison.core.delegationlib import get_role_mapping, map_role 
def test_role_mapping_loaded_from_config():
    """Loads role mapping via ConfigManager and verifies structure is sane.

    Ensures values come from edison.yaml (no hardcoded project-specific names).
    """
    cfg = ConfigManager().load_config()
    mapping_cfg = (cfg.get('delegation') or {}).get('roleMapping') or {}
    mapping = get_role_mapping(cfg)
    assert isinstance(mapping, dict)
    assert mapping == mapping_cfg
    # Ensure at least one generic role exists and maps to a non-empty target
    assert any(k for k in mapping.keys()), 'expected at least one generic role in mapping'
    any_key = next(iter(mapping.keys()))
    assert isinstance(any_key, str) and any_key
    assert isinstance(mapping[any_key], str) and mapping[any_key]


def test_generic_role_names_work():
    """Maps a generic role to a concrete target using config mapping."""
    mapping = get_role_mapping()
    generic = next(iter(mapping.keys()))
    target = map_role(generic)
    # Should resolve to something (may or may not equal generic in generic setups)
    assert isinstance(target, str) and target
    # In typical setups mapping changes the value; do not assert specific brand prefix
    if generic in mapping:
        assert target == mapping[generic]
