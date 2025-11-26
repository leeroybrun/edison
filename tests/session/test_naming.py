"""
Tests for PID-based session naming.

WAVE 1-4 used timestamp-based naming (DEPRECATED).
WAVE 5 uses PID-based naming via process tree inspection.

Note: Session IDs now include a sequence number for uniqueness when
multiple sessions are created in the same process (e.g., python-pid-123-seq-1).
"""

import pytest

from edison.core.session.naming import (
    SessionNamingError,
    reset_session_naming_counter,
    generate_session_id,
)
from edison.core.utils.process.inspector import infer_session_id


@pytest.fixture(autouse=True)
def reset_naming_counter():
    """Reset the session naming counter before each test."""
    reset_session_naming_counter()
    yield
    reset_session_naming_counter()











class TestGenerateSessionIdFunction:
    """Test generate_session_id() replacement function."""

    def test_generate_session_id_first_call_no_suffix(self):
        """First call should return base ID without sequence suffix."""
        session_id = generate_session_id()
        assert "-pid-" in session_id
        assert "-seq-" not in session_id

    def test_generate_session_id_second_call_has_suffix(self):
        """Second call should return ID with -seq-1 suffix."""
        generate_session_id()  # Burn first call
        session_id = generate_session_id()
        assert "-seq-1" in session_id

    def test_generate_session_id_third_call_increments(self):
        """Third call should return ID with -seq-2 suffix."""
        generate_session_id()
        generate_session_id()
        session_id = generate_session_id()
        assert "-seq-2" in session_id

    def test_generate_session_id_uses_process_inspector(self):
        """Should match infer_session_id() output for first call."""
        # infer_session_id is already imported at module level
        
        gen_id = generate_session_id()
        infer_id = infer_session_id()
        
        # infer_session_id returns {name}-pid-{pid}
        assert gen_id == infer_id

    def test_generate_session_id_thread_safe(self):
        """Should be thread-safe (concurrent calls get unique IDs)."""
        import threading
        
        ids = set()
        lock = threading.Lock()
        
        def worker():
            # Generate a few IDs per thread
            for _ in range(10):
                sid = generate_session_id()
                with lock:
                    ids.add(sid)
                    
        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
            
        # 5 threads * 10 calls = 50 unique IDs
        assert len(ids) == 50

    def test_generate_session_id_raises_on_error(self, monkeypatch):
        """Should raise SessionNamingError if inspector fails."""
        from edison.core.utils.process import inspector
        
        def broken_find():
            raise RuntimeError("Process inspection failed")
            
        monkeypatch.setattr(inspector, "find_topmost_process", broken_find)
        
        with pytest.raises(SessionNamingError):
            generate_session_id()

