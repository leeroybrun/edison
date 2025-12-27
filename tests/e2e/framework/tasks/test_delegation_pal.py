import sys
from pathlib import Path

from tests.helpers.paths import get_repo_root

# Add Edison core to path
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
from tests.helpers.delegation import route_task


def test_route_task_pal_clink_env(monkeypatch):
    """Routes a task with a Pal MCP clink target provided by env variable.

    Verifies that `continuation_id` is surfaced unchanged and `clink` is taken
    from `PAL_MCP_CLINK` when present.
    """
    monkeypatch.setenv('PAL_MCP_CLINK', 'pal-mcp://local')
    env = route_task('validator-global-codex', continuation_id='abc123')
    assert env['continuation_id'] == 'abc123'
    assert env['clink'] == 'pal-mcp://local'


def test_continuation_id_propagation_without_clink(monkeypatch):
    """Ensures continuation_id is preserved when no clink target is configured."""
    monkeypatch.delenv('PAL_MCP_CLINK', raising=False)
    monkeypatch.delenv('EDISON_DELEGATION_CLINK', raising=False)
    env = route_task('validator-global-claude', continuation_id='cid-789')
    assert env['continuation_id'] == 'cid-789'
    assert env['clink'] is None
