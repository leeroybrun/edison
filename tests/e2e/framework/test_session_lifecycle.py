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
from tests.helpers.session import ensure_session, load_session, close_session, validate_session 
def test_session_lifecycle_active_closing_validated():
    """Checks the logical state transitions in session.json across lifecycle."""
    sid = 'sess-life-1'
    ensure_session(sid)
    assert load_session(sid)['state'] == 'Active'
    close_session(sid)
    assert load_session(sid)['state'] == 'Closing'
    validate_session(sid)
    assert load_session(sid)['state'] == 'Validated'
