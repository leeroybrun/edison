import sys
from pathlib import Path

from tests.helpers.paths import get_repo_root

# Add Edison core to path (so `import edison.core.*` works)
_THIS_FILE = Path(__file__).resolve()
_CORE_ROOT = None
for _parent in _THIS_FILE.parents:
    candidate = _parent / ".edison" / "core"
    if (candidate / "lib").exists():
        _CORE_ROOT = candidate
        break

if _CORE_ROOT is None:
    _CORE_ROOT = get_repo_root()

CORE_ROOT = _CORE_ROOT
from edison.core.config import ConfigManager 
def test_role_mapping_loaded_from_config():
    """Delegation config loads and has the expected core shape (no legacy roleMapping)."""
    cfg = ConfigManager().load_config()
    delegation = cfg.get("delegation") or {}

    implementers = delegation.get("implementers") or {}
    assert isinstance(implementers, dict)
    assert isinstance(implementers.get("primary"), str) and implementers.get("primary")
    assert isinstance(implementers.get("fallbackChain"), list)

    # Routing rules are technology/project-specific and are expected to be dicts (often empty in core).
    assert isinstance(delegation.get("filePatternRules", {}), dict)
    assert isinstance(delegation.get("taskTypeRules", {}), dict)


def test_generic_role_names_work():
    """Core delegation config should remain project-agnostic and avoid hardcoded roleMapping."""
    cfg = ConfigManager().load_config()
    delegation = cfg.get("delegation") or {}
    assert "roleMapping" not in delegation, "Legacy delegation.roleMapping should not exist in core config"
