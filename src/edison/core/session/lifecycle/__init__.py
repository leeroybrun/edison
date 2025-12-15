"""Session lifecycle management."""
from __future__ import annotations

from .manager import (
    SessionManager,
    create_session,
    get_session,
    list_sessions,
    transition_session,
    get_current_session,
    set_current_session,
    clear_current_session,
)
from .transaction import (
    begin_tx,
    finalize_tx,
    abort_tx,
    commit_tx,
    rollback_tx,
    session_transaction,
    ValidationTransaction,
    validation_transaction,
)
from .recovery import (
    is_session_expired,
    append_session_log,
    cleanup_expired_sessions,
    check_timeout,
    handle_timeout,
    recover_session,
    detect_incomplete_transactions,
    recover_incomplete_validation_transactions,
    restore_records_to_global_transactional,
    clear_session_locks,
    clear_all_locks,
)
from .autostart import (
    SessionAutoStartError,
    SessionAutoStart,
)

# verify_session_health is imported lazily to avoid circular import with qa module
def verify_session_health(session_id: str):
    """Verify session health. Lazy wrapper to avoid circular import."""
    from .verify import verify_session_health as _verify
    return _verify(session_id)

__all__ = [
    # Manager
    "SessionManager",
    "create_session",
    "get_session",
    "list_sessions",
    "transition_session",
    "get_current_session",
    "set_current_session",
    "clear_current_session",
    # Transaction
    "begin_tx",
    "finalize_tx",
    "abort_tx",
    "commit_tx",
    "rollback_tx",
    "session_transaction",
    "ValidationTransaction",
    "validation_transaction",
    # Recovery
    "is_session_expired",
    "append_session_log",
    "cleanup_expired_sessions",
    "check_timeout",
    "handle_timeout",
    "recover_session",
    "detect_incomplete_transactions",
    "recover_incomplete_validation_transactions",
    "restore_records_to_global_transactional",
    "clear_session_locks",
    "clear_all_locks",
    # Autostart
    "SessionAutoStartError",
    "SessionAutoStart",
    # Verify
    "verify_session_health",
]
