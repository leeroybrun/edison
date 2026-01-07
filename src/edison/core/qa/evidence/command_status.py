"""Command evidence status helpers (repo-state snapshots).

This module centralizes the logic used by:
- `edison evidence status`
- `edison evidence capture` (post-run warnings)
- QA preflight checklists (blocking rules before validator execution)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from edison.core.config.domains.qa import QAConfig
from edison.core.qa.policy.resolver import ValidationPolicyResolver
from edison.core.utils.git.fingerprint import compute_repo_fingerprint

from .command_evidence import parse_command_evidence
from .snapshots import current_snapshot_key, snapshot_dir


def _invert_command_evidence_files(evidence_files: dict[str, Any]) -> dict[str, str]:
    """Return mapping of evidence filename -> command name."""
    out: dict[str, str] = {}
    for cmd, filename in (evidence_files or {}).items():
        c = str(cmd or "").strip()
        f = str(filename or "").strip()
        if c and f and f not in out:
            out[f] = c
    return out


def get_command_evidence_status(
    *,
    project_root: Path,
    task_id: str,
    preset_name: str | None = None,
) -> dict[str, Any]:
    """Return preset-aware command evidence status for the current repo fingerprint.

    `preset_name` forces the preset used to resolve required evidence.
    """
    current_fp = compute_repo_fingerprint(project_root)
    key = current_snapshot_key(project_root=project_root)
    snap_dir = snapshot_dir(project_root=project_root, key=key)

    resolver = ValidationPolicyResolver(project_root=project_root)
    policy = resolver.resolve_for_task(task_id, preset_name=str(preset_name).strip() if preset_name else None)
    required_files = [str(x).strip() for x in (policy.required_evidence or []) if str(x).strip()]

    qa_cfg = QAConfig(repo_root=project_root)
    evidence_files = (qa_cfg.validation_config.get("evidence", {}) or {}).get("files", {}) or {}
    if not isinstance(evidence_files, dict):
        evidence_files = {}
    command_evidence_names = {str(v).strip() for v in evidence_files.values() if str(v).strip()}
    filename_to_command = _invert_command_evidence_files(evidence_files)

    command_required = [f for f in required_files if f.startswith("command-") or f in command_evidence_names]

    present: list[str] = []
    missing: list[str] = []
    failed: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []

    for filename in command_required:
        name = str(filename).strip()
        if not name:
            continue
        file_path = snap_dir / name
        if not file_path.exists():
            missing.append(name)
            continue

        present.append(name)
        parsed = parse_command_evidence(file_path)
        if parsed is None:
            invalid.append({"file": name, "reason": "unparseable"})
            continue

        captured = {"gitHead": parsed.get("gitHead"), "gitDirty": parsed.get("gitDirty"), "diffHash": parsed.get("diffHash")}
        missing_fp = [
            k
            for k in ("gitHead", "gitDirty", "diffHash")
            if captured.get(k) is None or (isinstance(captured.get(k), str) and not str(captured.get(k)).strip())
        ]
        if missing_fp:
            stale.append({"file": name, "stale": True, "reason": f"missing_fingerprint:{','.join(missing_fp)}", "captured": captured})
        else:
            is_stale = (
                str(captured.get("gitHead") or "") != str(current_fp.get("gitHead") or "")
                or bool(captured.get("gitDirty")) != bool(current_fp.get("gitDirty"))
                or str(captured.get("diffHash") or "") != str(current_fp.get("diffHash") or "")
            )
            stale.append({"file": name, "stale": bool(is_stale), "reason": "mismatch" if is_stale else "ok", "captured": captured})

        exit_code = parsed.get("exitCode")
        if exit_code is not None:
            try:
                if int(exit_code) != 0:
                    failed.append(
                        {
                            "file": name,
                            "commandName": parsed.get("commandName", filename_to_command.get(name, "unknown")),
                            "exitCode": int(exit_code),
                        }
                    )
            except Exception:
                invalid.append({"file": name, "reason": "invalid_exit_code"})

    any_stale = any(bool(e.get("stale")) for e in stale)
    strict_stale = str(getattr(policy.preset, "stale_evidence", "warn") or "warn").strip().lower() == "block"

    all_present = len(missing) == 0
    all_passed = len(failed) == 0
    all_valid = len(invalid) == 0

    success = all_present and all_passed and all_valid and (not (strict_stale and any_stale))

    missing_commands = sorted(
        {filename_to_command.get(f) for f in missing if filename_to_command.get(f)}
    )

    return {
        "taskId": task_id,
        "preset": policy.preset.name,
        "fingerprint": current_fp,
        "snapshotDir": str(snap_dir.relative_to(project_root)) if snap_dir.exists() else str(snap_dir),
        "requiredCommandEvidence": command_required,
        "present": present,
        "missing": missing,
        "invalid": invalid,
        "failed": failed,
        "staleEvidence": stale,
        "anyStale": any_stale,
        "stalePolicy": "block" if strict_stale else "warn",
        "complete": all_present,
        "passed": all_passed,
        "valid": all_valid,
        "success": success,
        "missingCommands": missing_commands,
    }


__all__ = ["get_command_evidence_status"]

