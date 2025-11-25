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

from edison.core.task import record_tdd_evidence 
def test_tdd_evidence_red_green_refactor(tmp_path):
    """Records TDD evidence across RED→GREEN→REFACTOR phases in a single file."""
    task_id = 'T4001'
    p = record_tdd_evidence(task_id, 'RED', 'initial failing test')
    record_tdd_evidence(task_id, 'GREEN', 'implementation passes')
    record_tdd_evidence(task_id, 'REFACTOR', 'cleanup without behavior change')
    content = p.read_text(encoding='utf-8')
    assert 'RED:' in content and 'GREEN:' in content and 'REFACTOR:' in content
    # Ensure order is preserved (indices increasing)
    assert content.index('RED:') < content.index('GREEN:') < content.index('REFACTOR:')
