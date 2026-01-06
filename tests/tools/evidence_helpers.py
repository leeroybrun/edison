from __future__ import annotations

from pathlib import Path


def write_minimal_round_implementation_report(*, project_root: Path, task_id: str, round_num: int = 1) -> Path:
    from edison.core.qa.evidence import EvidenceService

    ev = EvidenceService(task_id, project_root=project_root)
    round_dir = ev.get_evidence_root() / f"round-{int(round_num)}"
    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "implementation-report.md").write_text(
        f"""---
taskId: "{task_id}"
round: {int(round_num)}
status: "complete"
summary: "Test implementation"
---
""",
        encoding="utf-8",
    )
    return round_dir


def write_passing_snapshot_command_evidence(
    *,
    project_root: Path,
    task_id: str,
    required_files: list[str],
) -> Path:
    """Create passing command evidence files in the task round evidence directory.

    This writes command evidence v1 (exitCode=0) for each required command-like
    evidence filename, scoped to `round-1`, matching what task guards validate.
    """
    from edison.core.config.domains.qa import QAConfig
    from edison.core.qa.evidence import EvidenceService
    from edison.core.qa.evidence.command_evidence import write_command_evidence
    from edison.core.utils.git.fingerprint import compute_repo_fingerprint

    qa_cfg = QAConfig(repo_root=project_root)
    evidence_files_cfg = (qa_cfg.validation_config.get("evidence", {}) or {}).get("files", {}) or {}
    if not isinstance(evidence_files_cfg, dict):
        evidence_files_cfg = {}
    command_evidence_names = set(str(v).strip() for v in evidence_files_cfg.values() if str(v).strip())

    command_required = [
        str(p).strip()
        for p in (required_files or [])
        if str(p).strip() and (str(p).startswith("command-") or str(p) in command_evidence_names)
    ]

    fingerprint = compute_repo_fingerprint(project_root)
    ev = EvidenceService(task_id, project_root=project_root)
    round_dir = ev.get_evidence_root() / "round-1"
    round_dir.mkdir(parents=True, exist_ok=True)

    for filename in command_required:
        name = str(filename).strip()
        command_name = name
        if command_name.startswith("command-"):
            command_name = command_name[len("command-") :]
        if command_name.endswith(".txt"):
            command_name = command_name[: -len(".txt")]
        write_command_evidence(
            path=round_dir / name,
            task_id=str(task_id),
            round_num=1,
            command_name=command_name or "command",
            command="true",
            cwd=str(project_root),
            exit_code=0,
            output="",
            fingerprint=fingerprint,
        )

    return round_dir
