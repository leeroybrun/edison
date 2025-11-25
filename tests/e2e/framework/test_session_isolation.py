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

from edison.core.sessionlib import ensure_session, close_session, validate_session 
def test_session_isolation_physical_moves(tmp_path):
    """Verifies physical directory moves across lifecycle: Active -> Closing -> Validated."""
    sid = 'sess-iso-1'
    active_dir = ensure_session(sid)
    scratch = active_dir / 'scratch.tmp'
    scratch.write_text('demo', encoding='utf-8')

    closing_dir = close_session(sid)
    assert not active_dir.exists()
    assert (closing_dir / 'scratch.tmp').exists()

    validated_dir = validate_session(sid)
    assert not closing_dir.exists()
    assert (validated_dir / 'scratch.tmp').exists()
