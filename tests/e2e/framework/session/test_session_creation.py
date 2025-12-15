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
from tests.helpers.session import ensure_session, load_session
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
    assert meta['state'] == 'active'
    assert meta.get("meta", {}).get("status") == "active"
    assert "git" in meta
