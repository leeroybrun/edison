from __future__ import annotations

from pathlib import Path

from edison.core.context.files import FileContextService


def test_file_context_service_extracts_files_from_implementation_report_body(
    isolated_project_env: Path,
) -> None:
    repo = isolated_project_env
    report_dir = repo / ".project" / "qa" / "validation-reports" / "T001" / "round-1"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "implementation-report.md"
    report_path.write_text(
        "---\n"
        "taskId: T001\n"
        "round: 1\n"
        "implementationApproach: test\n"
        "primaryModel: codex\n"
        "completionStatus: complete\n"
        "tracking:\n"
        "  processId: 1\n"
        "  startedAt: '2025-12-15T00:00:00Z'\n"
        "  completedAt: '2025-12-15T00:00:00Z'\n"
        "---\n\n"
        "## Summary\n"
        "- ok\n\n"
        "## Changed files\n"
        "- `apps/api/src/server.ts`\n"
        "- `apps/api/test/integration/server.test.ts`\n",
        encoding="utf-8",
    )

    ctx = FileContextService(project_root=repo).get_for_task("T001", session_id=None)
    assert ctx.source == "implementation_report"
    assert ctx.all_files == [
        "apps/api/src/server.ts",
        "apps/api/test/integration/server.test.ts",
    ]

