from __future__ import annotations

import sys
from pathlib import Path

# Add tests directory to path so tests can import from helpers.*
TESTS_ROOT = Path(__file__).resolve().parent.parent.parent
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from helpers.test_env import TestProjectDir
from helpers.command_runner import (
    run_script,
    assert_command_success,
    assert_output_contains,
)


def _make_guard_wrappers(tmp_root: Path, repo_root: Path) -> None:
    """Create the strict guard wrappers under <tmp>/scripts/* expected by guards.

    We intentionally mirror the paths used by guard checks:
    - scripts/implementation/validate → wraps Edison Python module
    - scripts/tasks/ensure-followups → wraps Edison Python module

    Note: After migration to Python modules, these wrappers now call Python modules
    instead of legacy shell scripts.
    """
    scripts_dir = tmp_root / "scripts"
    (scripts_dir / "implementation").mkdir(parents=True, exist_ok=True)
    (scripts_dir / "tasks").mkdir(parents=True, exist_ok=True)

    # Update to use Python modules instead of legacy scripts
    impl_validate = scripts_dir / "implementation" / "validate"
    impl_validate.write_text(
        f"#!/usr/bin/env bash\npython3 -m edison.core.task.validation \"$@\"\n"
    )
    impl_validate.chmod(0o755)

    ensure_followups = scripts_dir / "tasks" / "ensure-followups"
    ensure_followups.write_text(
        f"#!/usr/bin/env bash\npython3 -m edison.core.task.manager ensure-followups \"$@\"\n"
    )
    ensure_followups.chmod(0o755)


def test_claim_strict_wrapper_detection(tmp_path):
    """tasks/claim should correctly detect presence of strict guard wrappers.

    - Without wrappers → Strict Wrappers → no
    - With wrappers   → Strict Wrappers → yes
    """
    # Arrange isolated test project
    # Use robust repo root detection (prefer outermost git root when nested)
    def get_repo_root() -> Path:
        current = Path(__file__).resolve()
        last_git_root: Path | None = None
        while current != current.parent:
            if (current / ".git").exists():
                last_git_root = current
            current = current.parent
        if last_git_root is None:
            raise RuntimeError("Could not find repository root")
        return last_git_root

    repo_root = get_repo_root()
    proj = TestProjectDir(tmp_path, repo_root)

    # Create a minimal task to claim
    res_new = run_script(
        "tasks/new",
        ["--id", "901", "--wave", "wave1", "--slug", "strict-check"],
        cwd=proj.tmp_path,
    )
    assert_command_success(res_new)
    task_id = "901-wave1-strict-check"

    # Create a session to satisfy claim's session registration
    res_session = run_script(
        "session",
        ["new", "--owner", "tester", "--session-id", "s-strict", "--mode", "start"],
        cwd=proj.tmp_path,
    )
    assert_command_success(res_session)

    # Act 1: Claim without wrappers; enable debug line
    res_claim1 = run_script(
        "tasks/claim",
        [task_id, "--session", "s-strict"],
        cwd=proj.tmp_path,
        env={"project_DEBUG_WRAPPERS": "1"},
    )
    assert_command_success(res_claim1)
    assert_output_contains(res_claim1, "Strict Wrappers → no")

    # Provide the guard wrappers at the expected strict paths
    _make_guard_wrappers(proj.tmp_path, repo_root)

    # Act 2: Claim again; detection should now be positive
    res_claim2 = run_script(
        "tasks/claim",
        [task_id, "--session", "s-strict"],
        cwd=proj.tmp_path,
        env={"project_DEBUG_WRAPPERS": "1"},
    )
    assert_command_success(res_claim2)
    assert_output_contains(res_claim2, "Strict Wrappers → yes")
