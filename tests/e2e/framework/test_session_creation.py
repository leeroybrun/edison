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
if str(CORE_ROOT) not in sys.path:

from edison.core.sessionlib import ensure_session, load_session, _get_worktree_base 
def test_session_initialization_and_json(tmp_path):
    """Creates a session and verifies session.json content and computed paths.

    Ensures worktree base respects configuration and no hardcoded project names
    are present in the test itself.
    """
    sid = 'sess-create-1'
    d = ensure_session(sid)
    assert d.exists()
    meta = load_session(sid)
    assert meta['id'] == sid
    assert meta['state'] == 'Active'
    # worktree base is computed via config
    assert Path(meta['worktreeBase']).resolve() == _get_worktree_base().resolve()
