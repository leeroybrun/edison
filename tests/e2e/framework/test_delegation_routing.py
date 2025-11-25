import sys
from pathlib import Path

# Add Edison core to path
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
from edison.core.delegationlib import map_role, route_task, get_role_mapping 
def test_route_task_maps_role_correctly():
    """Routes a generic role and verifies target_role equals mapping result."""
    mapping = get_role_mapping()
    generic = next(iter(mapping.keys()))
    expected = map_role(generic)
    env = route_task(generic)
    assert env['target_role'] == expected


def test_route_task_unknown_role_passthrough():
    """Unknown generic roles should pass through unchanged (no mapping)."""
    generic = 'unknown-role-x'
    env = route_task(generic)
    assert env['target_role'] == generic
