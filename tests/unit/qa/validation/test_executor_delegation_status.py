from __future__ import annotations

from pathlib import Path

from edison.core.qa.engines.executor import ValidationExecutor


def test_executor_does_not_require_delegation_for_non_blocking_validators(
    isolated_project_env: Path,
) -> None:
    """Non-blocking delegated validators are advisory and must not block the workflow."""
    executor = ValidationExecutor(project_root=isolated_project_env, max_workers=1)

    result = executor.execute(
        task_id="9002-delegated-nonblocking",
        session_id="sess-1",
        wave="critical",
        validators=["coderabbit"],
        parallel=False,
    )

    # Coderabbit is non-blocking; even if it must be delegated, we should not require it.
    assert result.delegated_validators == []
    assert result.to_dict()["status"] == "completed"

