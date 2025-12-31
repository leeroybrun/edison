from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from edison.core.audit.logger import audit_event
from edison.core.shims import ShimService


def run_exec(
    *,
    repo_root: Path,
    argv: list[str],
    context: str,
) -> int:
    """Run a subprocess with optional shims and structured audit logging.

    - Always attempts to apply configured shims (no-op if disabled).
    - Streams stdio (no output capture) so behavior matches direct execution.
    """
    if not argv:
        raise ValueError("argv is required")

    env = os.environ.copy()
    env = ShimService(project_root=repo_root).apply_to_env(env, context=context)

    started = time.time()
    try:
        audit_event(
            "subprocess.exec.start",
            repo_root=repo_root,
            argv=argv,
            cwd=str(Path.cwd()),
        )
    except Exception:
        pass

    proc = subprocess.run(argv, env=env)
    code = int(proc.returncode)

    try:
        audit_event(
            "subprocess.exec.end",
            repo_root=repo_root,
            argv=argv,
            cwd=str(Path.cwd()),
            exit_code=code,
            duration_ms=int((time.time() - started) * 1000),
        )
    except Exception:
        pass

    return code

