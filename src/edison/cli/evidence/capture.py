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
from edison.cli._utils import resolve_existing_task_id

SUMMARY = "Run configured CI commands and capture output as evidence"

from edison.core.utils.text import parse_frontmatter


def register_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("task_id", help="Task identifier (e.g., 003-validation-presets)")
    parser.add_argument(
        "--only",
        action="append",
        default=[],
        help=(
            "Run only these command(s) (repeatable, or comma-separated). Intended for targeted reruns; it may NOT "
            "satisfy the task's preset-required evidence. Verify with `edison evidence status <task-id>`. "
            "Example: --only test --only lint"
        ),
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
        "--force",
        action="store_true",
        help="Force re-run commands even if a complete snapshot exists for the current repo fingerprint.",
    )
    parser.add_argument(
        "--no-lock",
        action="store_true",
        help="Bypass evidence capture locking (dangerous when multiple agents run in parallel).",
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
        raw_task_id = str(args.task_id)
        task_id = resolve_existing_task_id(project_root=project_root, raw_task_id=raw_task_id)

        only = _split_only(getattr(args, "only", []) or [])
        if getattr(args, "command_name", None):
            only.append(str(args.command_name))

        run_all = bool(getattr(args, "all", False))
        preset_name = getattr(args, "preset", None)
        session_close = bool(getattr(args, "session_close", False))
        resolved_preset: str | None = None
        continue_on_failure = bool(getattr(args, "continue_on_failure", False))
        force = bool(getattr(args, "force", False))
        no_lock = bool(getattr(args, "no_lock", False))

        from edison.core.config.domains.ci import CIConfig
        from edison.core.config.domains.qa import QAConfig
        from edison.core.config.domains.tdd import TDDConfig
        from edison.core.task.repository import TaskRepository
        from edison.core.qa.evidence.command_evidence import write_command_evidence
        from edison.core.qa.evidence.command_status import get_command_evidence_status
        from edison.core.qa.evidence.snapshots import current_snapshot_key, snapshot_dir, snapshot_status
        from edison.core.qa.policy.resolver import ValidationPolicyResolver
        from edison.core.qa.evidence.snapshots import current_snapshot_fingerprint
        from edison.core.utils.text import render_template_text

        fingerprint = current_snapshot_fingerprint(project_root=project_root)
        key = current_snapshot_key(project_root=project_root)
        snap_dir = snapshot_dir(project_root=project_root, key=key)
        snap_dir.mkdir(parents=True, exist_ok=True)

        # Build a lightweight task frontmatter context for templating CI command strings.
        # Project-specific keys (e.g. stack/components) should be defined in task templates/overrides,
        # not as first-class fields in Edison core models.
        task_repo = TaskRepository(project_root=project_root)
        task_path = task_repo.get_path(task_id)
        task_doc = parse_frontmatter(task_path.read_text(encoding="utf-8", errors="strict"))
        task_fm = task_doc.frontmatter if isinstance(task_doc.frontmatter, dict) else {}

        # Flatten frontmatter keys for the regex-based template engine fallback:
        # - allow exact keys when they are identifier-like
        # - also provide a snake_case variant for keys containing hyphens
        flat: dict[str, Any] = {}
        for k, v in (task_fm or {}).items():
            if not isinstance(k, str):
                continue
            fm_key = k.strip()
            if not fm_key:
                continue
            if fm_key.replace("_", "").isalnum():
                flat[fm_key] = v
            if "-" in fm_key:
                snake = fm_key.replace("-", "_")
                if snake.replace("_", "").isalnum() and snake not in flat:
                    flat[snake] = v

        components_val = flat.get("components")
        components: list[str] = []
        if isinstance(components_val, list):
            components = [str(x).strip() for x in components_val if str(x).strip()]
        elif isinstance(components_val, str):
            components = [p.strip() for p in components_val.split(",") if p.strip()]

        command_ctx: dict[str, Any] = {
            "task_id": task_id,
            "task": task_fm,
            **flat,
            "components_csv": ",".join(components),
            "component": components[0] if components else "",
        }

        ci_commands = CIConfig(repo_root=project_root).commands
        if not ci_commands:
            raise RuntimeError("No CI commands configured (missing `ci.commands` in config).")
        # Render any {{var}} placeholders in configured commands using task context.
        ci_commands = {k: render_template_text(str(v), command_ctx) for k, v in ci_commands.items()}

        # Resolve the validation policy up front so output is stable even when
        # the operator uses `--only` for targeted reruns.
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

        if only:
            missing = [n for n in only if n not in ci_commands]
            if missing:
                raise RuntimeError(f"Unknown CI command(s): {', '.join(missing)} (check `ci.commands`).")
            ci_commands = {k: ci_commands[k] for k in only}
        elif not run_all:
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

        evidence_files = evidence_files_cfg

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

        session_id = str(os.environ.get("AGENTS_SESSION") or "").strip() or None
        if no_lock and not formatter.json_mode:
            print("Warning: --no-lock bypasses evidence capture locking.", file=sys.stderr)

        required_files_for_run = [
            _command_output_filename(cmd_name, evidence_files=evidence_files)
            for cmd_name in ci_commands.keys()
        ]
        snap = snapshot_status(project_root=project_root, key=key, required_files=required_files_for_run)
        reuse_ok = bool(snap.get("complete")) and bool(snap.get("passed")) and bool(snap.get("valid"))
        if reuse_ok and not force:
            payload: dict[str, Any] = {
                "taskId": task_id,
                "preset": resolved_preset,
                "fingerprint": fingerprint,
                "snapshotDir": str(snap_dir.relative_to(project_root)),
                "reusedSnapshot": True,
                "requiredFiles": required_files_for_run,
                "status": snap,
                "commands": [],
                "mode": (
                    "only"
                    if only
                    else ("all" if run_all else ("session-close" if session_close else ("preset" if preset_name else "required")))
                ),
            }

            preset_status: dict[str, Any] | None = None
            try:
                preset_status = get_command_evidence_status(
                    project_root=project_root,
                    task_id=task_id,
                    preset_name=resolved_preset,
                )
            except Exception:
                preset_status = None
            if preset_status is not None:
                payload["presetEvidenceStatus"] = preset_status

            if formatter.json_mode:
                formatter.json_output(payload)
            else:
                mode_label = payload.get("mode") or "required"
                preset_label = f", preset={resolved_preset}" if resolved_preset else ""
                formatter.text(
                    f"Reused existing evidence snapshot for current repo fingerprint: {snap_dir.relative_to(project_root)}"
                )
                formatter.text(f"(mode={mode_label}{preset_label})")
                formatter.text("To force re-run: edison evidence capture <task> --force")

                if preset_status is not None and not bool(preset_status.get("success", False)):
                    missing_files = preset_status.get("missing") or []
                    missing_cmds = preset_status.get("missingCommands") or []
                    if missing_files:
                        formatter.text("")
                        formatter.text("Note: the current snapshot still does NOT satisfy the preset's required command evidence.")
                        formatter.text(f"- Missing: {', '.join([str(x) for x in missing_files])}")
                        if missing_cmds:
                            formatter.text(
                                "- Fix: "
                                + " ".join(
                                    ["edison evidence capture", task_id, "--only", ",".join([str(c) for c in missing_cmds])]
                                )
                            )
                        else:
                            formatter.text(f"- Fix: edison evidence capture {task_id}")

            return 0

        for cmd_name, cmd_string in ci_commands.items():
            cmd = str(cmd_string).strip()
            if not cmd or _looks_like_placeholder(cmd):
                continue

            filename = str(evidence_files.get(cmd_name) or f"command-{cmd_name}.txt").strip()
            if not filename:
                filename = f"command-{cmd_name}.txt"

            lock_info: dict[str, Any]
            if no_lock:
                lock_info = {
                    "lockKey": f"evidence-capture:{cmd_name}",
                    "lockPath": "",
                    "waitedMs": 0,
                    "lockBypassed": True,
                }
                exit_code, output, started_at, completed_at = _run_command(cmd, project_root, pipefail=True)
            else:
                from edison.core.utils.locks.evidence_capture import acquire_evidence_capture_lock

                with acquire_evidence_capture_lock(
                    project_root=project_root,
                    command_group=cmd_name,
                    session_id=session_id,
                ) as acquired:
                    lock_info = {**acquired, "lockBypassed": False}
                    if not formatter.json_mode:
                        formatter.text(
                            f"Lock acquired for '{cmd_name}' (waited {int(acquired.get('waitedMs') or 0)}ms): "
                            f"{acquired.get('lockPath')}"
                        )
                    exit_code, output, started_at, completed_at = _run_command(cmd, project_root, pipefail=True)

            evidence_path = snap_dir / filename
            write_command_evidence(
                path=evidence_path,
                task_id=task_id,
                round_num=0,
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
                fingerprint=fingerprint,
            )

            results.append(
                {
                    "name": cmd_name,
                    "command": cmd,
                    "exitCode": exit_code,
                    "file": filename,
                    "path": str(evidence_path.relative_to(project_root)),
                    "lock": lock_info,
                }
            )
            if exit_code == 0:
                passed += 1
            else:
                failed += 1
                if not formatter.json_mode:
                    display_path = str(evidence_path)
                    try:
                        display_path = str(evidence_path.relative_to(project_root))
                    except Exception:
                        display_path = str(evidence_path)

                    print(
                        f"Command '{cmd_name}' failed (exitCode={exit_code}). Evidence: {display_path}",
                        file=sys.stderr,
                    )
                    print(
                        "Hint: if this is due to missing environment variables, configure them in `.edison/config/ci.yaml` "
                        f"under `ci.commands.{cmd_name}` (or prefix env vars when running `edison evidence capture`).",
                        file=sys.stderr,
                    )
                if not continue_on_failure:
                    break

        payload: dict[str, Any] = {
            "taskId": task_id,
            "fingerprint": fingerprint,
            "snapshotDir": str(snap_dir.relative_to(project_root)),
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

        # Always include the preset-aware status for the current repo fingerprint so
        # agents running a targeted `--only` capture don't mistakenly assume they
        # satisfied the preset requirements.
        preset_status: dict[str, Any] | None = None
        try:
            preset_status = get_command_evidence_status(project_root=project_root, task_id=task_id, preset_name=resolved_preset)
        except Exception:
            preset_status = None
        if preset_status is not None:
            payload["presetEvidenceStatus"] = preset_status

        if formatter.json_mode:
            formatter.json_output(payload)
        else:
            mode_label = payload.get("mode") or "required"
            preset_label = f", preset={resolved_preset}" if resolved_preset else ""
            formatter.text(f"Captured {len(results)} command(s): {passed} passed, {failed} failed (mode={mode_label}{preset_label})")
            if results:
                formatter.text("Review evidence outputs before proceeding.")
            if preset_status is not None and not bool(preset_status.get("success", False)):
                missing_files = preset_status.get("missing") or []
                missing_cmds = preset_status.get("missingCommands") or []
                if missing_files:
                    formatter.text("")
                    formatter.text(
                        "Note: this capture does NOT satisfy the preset's required command evidence yet."
                    )
                    formatter.text(f"- Missing: {', '.join([str(x) for x in missing_files])}")
                    if missing_cmds:
                        formatter.text(
                            "- Fix: "
                            + " ".join(["edison evidence capture", task_id, "--only", ",".join([str(c) for c in missing_cmds])])
                        )
                    else:
                        formatter.text(f"- Fix: edison evidence capture {task_id}")

        return 0 if failed == 0 or continue_on_failure else 1

    except Exception as e:
        formatter.error(e, error_code="evidence_capture_error")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    register_args(parser)
    cli_args = parser.parse_args()
    sys.exit(main(cli_args))
