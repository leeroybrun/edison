"""Edison Framework Resilience Mechanisms.

Provides retry logic, graceful degradation, and lightweight recovery helpers.
"""

from __future__ import annotations

import time
import functools
import shutil
import json
from typing import Callable, Any, Tuple, Type, Optional, Dict
from pathlib import Path
import logging

from edison.core.utils import io as io_utils

logger = logging.getLogger(__name__)


def get_retry_config() -> Dict[str, Any]:
    """Load retry configuration from YAML-driven settings.

    Returns:
        Dict[str, Any]: Mapping containing retry settings with safe fallbacks.
    """
    from edison.core.config import ConfigManager

    mgr = ConfigManager()
    cfg = mgr.load_config()
    retry_cfg = cfg.get("resilience", {}).get("retry", {}) if isinstance(cfg, dict) else {}

    return {
        "max_attempts": retry_cfg.get("max_attempts", 3),
        "initial_delay": retry_cfg.get("initial_delay_seconds", 1.0),
        "backoff_factor": retry_cfg.get("backoff_factor", 2.0),
        "max_delay": retry_cfg.get("max_delay_seconds", 60.0),
    }


def retry_with_backoff(
    max_attempts: Optional[int] = None,
    initial_delay: Optional[float] = None,
    backoff_factor: Optional[float] = None,
    max_delay: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
):
    """
    Decorator that retries a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for each retry
        max_delay: Maximum delay between retries
        exceptions: Tuple of exceptions to catch and retry

    Example:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0)
        def flaky_operation():
            # May fail transiently
            pass
    """
    config = get_retry_config()

    effective_max_attempts = max_attempts if max_attempts is not None else config["max_attempts"]
    effective_initial_delay = initial_delay if initial_delay is not None else config["initial_delay"]
    effective_backoff_factor = backoff_factor if backoff_factor is not None else config["backoff_factor"]
    effective_max_delay = max_delay if max_delay is not None else config["max_delay"]

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = effective_initial_delay
            for attempt in range(1, effective_max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:  # type: ignore[misc]
                    if attempt == effective_max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {effective_max_attempts} attempts"
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{effective_max_attempts} failed: {e}"
                    )
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)

                    # Exponential backoff
                    delay = min(delay * effective_backoff_factor, effective_max_delay)

            raise RuntimeError("Unreachable")  # Should never get here

        return wrapper
    return decorator


def graceful_degradation(fallback_value: Any):
    """
    Decorator that provides graceful degradation on failure.

    Args:
        fallback_value: Value to return if function fails

    Example:
        @graceful_degradation(fallback_value=[])
        def fetch_optional_data():
            # If this fails, return empty list
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:  # noqa: BLE001 - broad by design for graceful fallback
                logger.warning(f"{func.__name__} failed, using fallback: {e}")
                return fallback_value

        return wrapper
    return decorator


def list_recoverable_sessions() -> list[Path]:
    """List all recoverable sessions from the recovery directory.

    Returns a list of session directories in the recovery folder,
    sorted by recovery.json modification time (oldest first).
    Symlinks are followed but not recursed into to prevent cycles.

    Returns:
        List of Path objects representing recoverable session directories
    """
    from edison.core.session._utils import get_sessions_root

    sessions_root = get_sessions_root()
    recovery_root = sessions_root / "recovery"

    if not recovery_root.exists():
        return []

    sessions = []
    for entry in recovery_root.iterdir():
        # Skip symlinks to prevent recursion cycles
        if entry.is_symlink():
            continue

        # Only include directories with recovery.json
        if entry.is_dir() and (entry / "recovery.json").exists():
            sessions.append(entry)

    # Sort by recovery.json modification time (oldest first)
    def get_recovery_mtime(session_dir: Path) -> float:
        recovery_json = session_dir / "recovery.json"
        try:
            return recovery_json.stat().st_mtime
        except (FileNotFoundError, OSError):
            return 0.0

    sessions.sort(key=get_recovery_mtime)
    return sessions


def resume_from_recovery(recovery_dir: Path) -> Path:
    """Resume a session from ``recovery`` back to semantic ``active``.

    This helper is primarily used by tests. It uses the canonical session
    repository + state machine, so directory mapping (e.g., active → wip)
    and state history remain consistent.
    """
    rec_dir = Path(recovery_dir).resolve()
    if not rec_dir.exists():
        raise FileNotFoundError(f"Recovery directory not found: {rec_dir}")

    sid = rec_dir.name
    from edison.core.session.persistence.repository import SessionRepository
    from edison.core.config.domains.workflow import WorkflowConfig

    # Preserve any unknown/extra fields in the raw session JSON. The canonical
    # Session model intentionally enforces a schema and may drop extra keys;
    # recovery should not lose data.
    raw_json_path = rec_dir / "session.json"
    raw_data: Dict[str, Any] = {}
    if raw_json_path.exists():
        try:
            loaded = io_utils.read_json(raw_json_path, default={})
            if isinstance(loaded, dict):
                raw_data = loaded
        except Exception:
            raw_data = {}

    repo = SessionRepository()
    active_state = WorkflowConfig().get_semantic_state("session", "active")
    updated = repo.transition(
        sid,
        active_state,
        context={"session_id": sid, "session": (repo.get(sid).to_dict() if repo.get(sid) else {})},
    )

    session_dir = repo.get_session_json_path(updated.id).parent

    # Best-effort merge raw extras back into the transitioned JSON.
    try:
        updated_json_path = session_dir / "session.json"
        updated_data = io_utils.read_json(updated_json_path, default={})
        if isinstance(updated_data, dict) and raw_data:
            def _deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> Dict[str, Any]:
                out: Dict[str, Any] = dict(base)
                for k, v in overlay.items():
                    if (
                        k in out
                        and isinstance(out.get(k), dict)
                        and isinstance(v, dict)
                    ):
                        out[k] = _deep_merge(out[k], v)  # type: ignore[arg-type]
                    else:
                        out[k] = v
                return out

            merged = _deep_merge(raw_data, updated_data)
            updated_json_path.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    except Exception:
        pass

    # Return the session directory containing session.json.
    return session_dir
