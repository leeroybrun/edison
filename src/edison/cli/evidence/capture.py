"""
Edison evidence capture command.

SUMMARY: Run configured CI commands and capture output as evidence
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from edison.cli import OutputFormatter, add_json_flag, add_repo_root_flag, get_repo_root

SUMMARY = "Run configured CI commands and capture output as evidence"


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier (e.g., 003-validation-presets)")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help="Run only these command(s) (repeatable, or comma-separated). Example: --only test --only lint",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all configured CI commands (ignores preset-required filtering).",
    )
    parser.add_argument(
        "--preset",
        help="Explicit validation preset name to use for required-evidence filtering (default: inferred for the task).",
    )
    parser.add_argument(
        "--session-close",
        action="store_true",
        help="Run only commands needed to satisfy the configured session-close validation preset (validation.sessionClose.preset).",
    )
    parser.add_argument(
        "--command",
        dest="command_name",
        help="Alias for --only <name> (single command).",
    )
    parser.add_argument(
        "--continue",
        dest="continue_on_failure",
        action="store_true",
        help="Continue running commands after failure",
    )
    parser.add_argument(
        "--round",
        type=int,
        dest="round_num",
        help="Explicit round number (default: latest)",
    )
    add_json_flag(parser)
    add_repo_root_flag(parser)


def _split_only(values: Iterable[str]) -> list[str]:
    out: list[str] = []
    for raw in values:
        for part in str(raw).split(","):
            s = part.strip()
            if s:
                out.append(s)
    return out


def _looks_like_placeholder(cmd: str) -> bool:
    v = (cmd or "").strip()
    return bool(v) and v.startswith("<") and v.endswith(">")


def _command_output_filename(command_name: str, *, evidence_files: dict[str, str]) -> str:
    filename = str(evidence_files.get(command_name) or f"command-{command_name}.txt").strip()
    return filename or f"command-{command_name}.txt"


def _run_command(command: str, cwd: Path, *, pipefail: bool = True) -> tuple[int, str, datetime, datetime]:
    """Run a shell command and capture combined stdout+stderr."""
    started_at = datetime.now(tz=timezone.utc)
    wrapped = f"set -o pipefail; {command}" if pipefail else command
    try:
        cp = subprocess.run(
            wrapped,
            shell=True,
            executable="/bin/bash",
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
            env=None,
        )
        exit_code = int(cp.returncode)
        output = (cp.stdout or "") + (cp.stderr or "")
    except Exception as e:
        exit_code = 1
        output = str(e)
    completed_at = datetime.now(tz=timezone.utc)
    return exit_code, output, started_at, completed_at


def main(args: argparse.Namespace) -> int:
    formatter = OutputFormatter(json_mode=getattr(args, "json", False))
    try:
        project_root = get_repo_root(args)
        task_id = str(args.task_id)

        only = _split_only(getattr(args, "only", []) or [])
        if getattr(args, "command_name", None):
            only.append(str(args.command_name))

        run_all = bool(getattr(args, "all", False))
        preset_name = getattr(args, "preset", None)
        session_close = bool(getattr(args, "session_close", False))
        resolved_preset: str | None = None
        continue_on_failure = bool(getattr(args, "continue_on_failure", False))
        round_num = getattr(args, "round_num", None)

        from edison.core.config.domains.ci import CIConfig
        from edison.core.config.domains.qa import QAConfig
        from edison.core.config.domains.tdd import TDDConfig
        from edison.core.qa.evidence import EvidenceService, rounds
        from edison.core.qa.evidence.command_evidence import write_command_evidence
        from edison.core.qa.policy.resolver import ValidationPolicyResolver

        ev = EvidenceService(task_id=task_id, project_root=project_root)

        if round_num is not None:
            round_dir = ev.get_round_dir(int(round_num))
            if not round_dir.exists():
                raise RuntimeError(f"Round {round_num} does not exist. Run `edison evidence init {task_id}` first.")
        else:
            round_dir = ev.get_current_round_dir()
            if round_dir is None:
                raise RuntimeError(f"No evidence round exists. Run `edison evidence init {task_id}` first.")
            round_num = rounds.get_round_number(round_dir)

        ci_commands = CIConfig(repo_root=project_root).commands
        if not ci_commands:
            raise RuntimeError("No CI commands configured (missing `ci.commands` in config).")

        if only:
            missing = [n for n in only if n not in ci_commands]
            if missing:
                raise RuntimeError(f"Unknown CI command(s): {', '.join(missing)} (check `ci.commands`).")
            ci_commands = {k: ci_commands[k] for k in only}
        elif not run_all:
            qa_cfg = QAConfig(repo_root=project_root)
            evidence_files_cfg = (qa_cfg.validation_config.get("evidence", {}) or {}).get("files", {}) or {}
            if not isinstance(evidence_files_cfg, dict):
                evidence_files_cfg = {}

            required_files: list[str] = []
            if session_close:
                from edison.core.qa.policy.session_close import get_session_close_policy

                policy = get_session_close_policy(project_root=project_root)
                resolved_preset = policy.preset.name
                required_files = list(policy.required_evidence or [])
            else:
                resolver = ValidationPolicyResolver(project_root=project_root)
                policy = resolver.resolve_for_task(task_id, preset_name=str(preset_name).strip() if preset_name else None)
                resolved_preset = policy.preset.name
                required_files = list(policy.required_evidence or [])

            required_set = {str(x).strip() for x in required_files if str(x).strip()}
            if not required_set:
                ci_commands = {}
            else:
                runnable: dict[str, Any] = {}
                for cmd_name, cmd_string in ci_commands.items():
                    cmd = str(cmd_string or "").strip()
                    if not cmd or _looks_like_placeholder(cmd):
                        continue
                    filename = _command_output_filename(cmd_name, evidence_files=evidence_files_cfg)
                    if filename in required_set:
                        runnable[cmd_name] = cmd_string
                if not runnable:
                    required_commandish = sorted([f for f in required_set if str(f).startswith("command-")])
                    if required_commandish:
                        raise RuntimeError(
                            "No configured CI commands match the required command evidence files for this run. "
                            "Check `validation.presets.*.required_evidence` (or the preset configured by `validation.sessionClose.preset`) "
                            "and `validation.evidence.files`/`ci.commands` mappings. "
                            f"Missing command evidence targets: {', '.join(required_commandish)}"
                        )
                    # Presets may require non-command artifacts (e.g. reports/markers). In that case,
                    # this command has nothing to run; other workflows are responsible for those files.
                    ci_commands = {}
                    required_set = set()
                ci_commands = runnable

        qa_config = QAConfig(repo_root=project_root)
        evidence_files = (qa_config.validation_config.get("evidence", {}) or {}).get("files", {}) or {}
        if not isinstance(evidence_files, dict):
            evidence_files = {}

        tdd_cfg = TDDConfig(repo_root=project_root)
        hmac_key = ""
        try:
            if tdd_cfg.hmac_key_env_var:
                hmac_key = str(
                    (tdd_cfg.hmac_key_env_var and (os.environ.get(tdd_cfg.hmac_key_env_var) or "")) or ""
                ).strip()
        except Exception:
            hmac_key = ""

        results: list[dict[str, Any]] = []
        passed = 0
        failed = 0

        for cmd_name, cmd_string in ci_commands.items():
            cmd = str(cmd_string).strip()
            if not cmd or _looks_like_placeholder(cmd):
                continue

            filename = str(evidence_files.get(cmd_name) or f"command-{cmd_name}.txt").strip()
            if not filename:
                filename = f"command-{cmd_name}.txt"

            exit_code, output, started_at, completed_at = _run_command(cmd, project_root, pipefail=True)

            evidence_path = round_dir / filename
            write_command_evidence(
                path=evidence_path,
                task_id=task_id,
                round_num=int(round_num or 1),
                command_name=cmd_name,
                command=cmd,
                cwd=str(project_root),
                exit_code=exit_code,
                output=output,
                started_at=started_at,
                completed_at=completed_at,
                shell="bash",
                pipefail=True,
                runner="edison evidence capture",
                hmac_key=hmac_key or None,
            )

            results.append({"name": cmd_name, "command": cmd, "exitCode": exit_code, "file": filename})
            if exit_code == 0:
                passed += 1
            else:
                failed += 1
                if not continue_on_failure:
                    break

        payload: dict[str, Any] = {
            "taskId": task_id,
            "round": int(round_num or 1),
            "commands": results,
            "passed": passed,
            "failed": failed,
            "mode": (
                "only"
                if only
                else ("all" if run_all else ("session-close" if session_close else ("preset" if preset_name else "required")))
            ),
            "preset": resolved_preset,
        }

        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            mode_label = payload.get("mode") or "required"
            preset_label = f", preset={resolved_preset}" if resolved_preset else ""
            formatter.text(f"Captured {len(results)} command(s): {passed} passed, {failed} failed (mode={mode_label}{preset_label})")
            if results:
                formatter.text("Review evidence outputs before proceeding.")

        return 0 if failed == 0 or continue_on_failure else 1

    except Exception as e:
        formatter.error(e, error_code="evidence_capture_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
