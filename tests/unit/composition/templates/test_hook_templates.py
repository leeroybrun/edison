import json
import os
import subprocess
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("jinja2")

from jinja2 import Template
from edison.data import get_data_path


def render_hook(template_name: str, **context) -> str:
    template_path = get_data_path("templates", f"hooks/{template_name}")
    template = Template(template_path.read_text())
    # Hook templates expect HookComposer-style context, including global_config.
    context.setdefault("global_config", {"project_management_dir": ".project"})
    return template.render(**context)


def write_script(content: str, tmpdir: Path) -> Path:
    path = tmpdir / "hook.sh"
    path.write_text(content)
    path.chmod(0o755)
    return path


def stub_env(tmpdir: Path, overrides=None) -> dict:
    """Create stub executables for Edison and formatters and return env."""
    overrides = overrides or {}
    env = os.environ.copy()
    env["PATH"] = f"{tmpdir}:{env['PATH']}"

    # Create .project/.session-id file (required by hook templates)
    project_dir = tmpdir / ".project"
    project_dir.mkdir(exist_ok=True)
    session_id_file = project_dir / ".session-id"
    session_id_file.write_text("test-session-123\n")

    # Stub edison CLI
    edison = tmpdir / "edison"
    edison.write_text(
        """#!/usr/bin/env bash
case "$1" in
  session)
    echo "${STUB_SESSION_JSON:-{\"active\":true,\"worktree\":\"/repo\",\"id\":\"sess-1\"}}"
    ;;
  task)
    if [[ "$2" == "allowed-operations" ]]; then
      echo "${STUB_ALLOWED_OPS:-Allowed operations: none}"
      exit 0
    fi
    echo "${STUB_TASK_JSON:-{\"state\":\"doing\",\"id\":\"TASK-1\"}}"
    ;;
  config)
    echo "${STUB_PACKS_JSON:-[\"pack-a\",\"pack-b\"]}"
    ;;
  rules)
    echo "${STUB_RULE_TEXT:-Rule text}"
    ;;
  ci)
    if [[ "$2" == "test" ]]; then
      exit ${STUB_TEST_EXIT:-0}
    fi
    if [[ "$2" == "coverage" ]]; then
      echo "${STUB_COVERAGE_JSON:-{\"overall\":85}}"
      exit 0
    fi
    ;;
  *)
    ;;
esac
"""
    )
    edison.chmod(0o755)

    # Stub git (used in validation hooks)
    git = tmpdir / "git"
    git.write_text(
        """#!/usr/bin/env bash
if [[ "$1" == "diff" ]]; then
  exit ${STUB_GIT_DIFF_EXIT:-0}
fi
exit 0
"""
    )
    git.chmod(0o755)

    # Optional formatter stub
    fmt = tmpdir / "fmtstub"
    fmt.write_text(
        """#!/usr/bin/env bash
if [[ -n "$FMT_LOG" ]]; then
  echo "$@" >> "$FMT_LOG"
fi
exit 0
"""
    )
    fmt.chmod(0o755)

    env.update(
        {
            "STUB_SESSION_JSON": overrides.get(
                "session_json", '{"active":true,"worktree":"/repo","id":"sess-1"}'
            ),
            "STUB_TASK_JSON": overrides.get(
                "task_json", '{"state":"doing","id":"TASK-1"}'),
            "STUB_ALLOWED_OPS": overrides.get("allowed_ops", "Allowed operations: none"),
            "STUB_PACKS_JSON": overrides.get("packs_json", '["pack-a","pack-b"]'),
            "STUB_RULE_TEXT": overrides.get("rule_text", "Rule text"),
            "STUB_COVERAGE_JSON": overrides.get("coverage_json", '{"overall":85}'),
            "STUB_TEST_EXIT": str(overrides.get("test_exit", 0)),
            "STUB_GIT_DIFF_EXIT": str(overrides.get("git_diff_exit", 0)),
        }
    )

    if "FMT_LOG" in overrides:
        env["FMT_LOG"] = str(overrides["FMT_LOG"])

    return env


def test_templates_render_without_config():
    for name in [
        "inject-session-context.sh.template",
        "inject-task-rules.sh.template",
        "remind-tdd.sh.template",
        "remind-state-machine.sh.template",
        "prevent-prod-edits.sh.template",
        "check-tests.sh.template",
        "stop-validate.sh.template",
        "commit-guard.sh.template",
        "auto-format.sh.template",
        "session-init.sh.template",
        "session-cleanup.sh.template",
    ]:
        rendered = render_hook(
            name,
            id="test-hook",
            type="UserPromptSubmit",
            description="Test hook",
        )
        assert "Edison Hook" in rendered


def test_templates_are_valid_bash():
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        hook_dir = get_data_path("templates", "hooks")
        for name in hook_dir.iterdir():
            if name.suffix != ".template":
                continue
            content = render_hook(name.name, id="a", type="t", description="d")
            script = write_script(content, tmpdir)
            # bash -n performs syntax check without executing
            result = subprocess.run(["bash", "-n", str(script)], capture_output=True)
            assert result.returncode == 0, result.stderr.decode()


def test_session_context_injects_sections():
    content = render_hook(
        "inject-session-context.sh.template",
        id="ctx",
        type="UserPromptSubmit",
        description="inject context",
        config={
            "include_worktree": True,
            "include_task_state": True,
            "include_pack_list": True,
        },
    )
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        script = write_script(content, tmpdir)
        env = stub_env(tmpdir)
        result = subprocess.run([str(script)], input=b"{}", env=env, cwd=tmpdir, capture_output=True)
        output = result.stdout.decode()
        assert result.returncode == 0
        assert "Edison Session Context" in output
        assert "Worktree: /repo" in output
        assert "Current Task" in output
        assert "Active Packs" in output


def test_task_rules_injection_for_matching_file():
    content = render_hook(
        "inject-task-rules.sh.template",
        id="rules",
        type="UserPromptSubmit",
        description="inject rules",
        config={
            "file_patterns": ["*.py"],
            "rules_by_state": {"doing": ["rule-one"]},
        },
    )
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        script = write_script(content, tmpdir)
        env = stub_env(tmpdir, {"rule_text": "Rule rule-one text"})
        payload = json.dumps({"file_paths": ["foo.py", "bar.txt"]})
        result = subprocess.run([str(script)], input=payload.encode(), env=env, cwd=tmpdir, capture_output=True)
        output = result.stdout.decode()
        assert result.returncode == 0
        assert "## Edison Rules (doing state)" in output
        assert "### rule-one" in output
        assert "Rule rule-one text" in output


def test_remind_tdd_respects_state_and_files():
    content = render_hook(
        "remind-tdd.sh.template",
        id="tdd",
        type="PreToolUse",
        description="reminder",
        blocking=False,
        config={"only_for_states": ["doing"], "skip_test_files": True},
    )
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        script = write_script(content, tmpdir)
        env = stub_env(tmpdir)

        payload = json.dumps({"tool": "Write", "args": {"file_path": "main.py"}})
        result = subprocess.run([str(script)], input=payload.encode(), env=env, cwd=tmpdir, capture_output=True)
        assert result.returncode == 0
        assert "TDD Reminder" in result.stdout.decode()

        # Test file should be skipped
        test_payload = json.dumps({"tool": "Write", "args": {"file_path": "thing.test.ts"}})
        skipped = subprocess.run([str(script)], input=test_payload.encode(), env=env, cwd=tmpdir, capture_output=True)
        assert skipped.stdout.decode().strip() == ""


def test_commit_guard_blocks_on_low_coverage():
    content = render_hook(
        "commit-guard.sh.template",
        id="commit",
        type="PreToolUse",
        description="guard",
        blocking=True,
        config={"require_coverage": True, "coverage_threshold": 80},
    )
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        script = write_script(content, tmpdir)
        env = stub_env(tmpdir, {"coverage_json": '{"overall":50}'})
        payload = json.dumps({"tool": "Bash", "args": {"command": "git commit -m 'msg'"}})
        result = subprocess.run([str(script)], input=payload.encode(), env=env, cwd=tmpdir, capture_output=True)
        assert result.returncode == 1
        assert "Coverage too low" in result.stdout.decode()


def test_auto_format_runs_formatter():
    log_path = Path(tempfile.mktemp())
    content = render_hook(
        "auto-format.sh.template",
        id="fmt",
        type="PostToolUse",
        description="auto format",
        config={"file_patterns": ["*.js"], "tools": ["fmtstub"]},
    )
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        script = write_script(content, tmpdir)
        env = stub_env(tmpdir, {"FMT_LOG": log_path})
        payload = json.dumps({"tool": "Edit", "args": {"file_path": "app.js"}})
        result = subprocess.run([str(script)], input=payload.encode(), env=env, cwd=tmpdir, capture_output=True)
        assert result.returncode == 0
        assert "Auto-formatting" in result.stdout.decode()

    logged = log_path.read_text().strip()
    assert "--write app.js" in logged


def test_session_hooks_echo_messages():
    init_content = render_hook(
        "session-init.sh.template",
        id="sess-start",
        type="SessionStart",
        description="start",
    )
    cleanup_content = render_hook(
        "session-cleanup.sh.template",
        id="sess-end",
        type="SessionEnd",
        description="end",
        config={"save_logs": False},
    )
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        env = stub_env(tmpdir)
        init_script = write_script(init_content, tmpdir)
        cleanup_script = write_script(cleanup_content, tmpdir)

        start = subprocess.run([str(init_script)], env=env, cwd=tmpdir, capture_output=True)
        end = subprocess.run([str(cleanup_script)], env=env, cwd=tmpdir, capture_output=True)

        assert start.returncode == 0
        assert "Session" in start.stdout.decode()
        assert end.returncode == 0
        assert "Session Ending" in end.stdout.decode()


def test_remind_state_machine_template_renders():
    content = render_hook(
        "remind-state-machine.sh.template",
        id="state-remind",
        type="PreToolUse",
        description="remind state machine",
        blocking=False,
        config={"only_for_states": ["doing"]},
    )
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        script = write_script(content, tmpdir)
        env = stub_env(tmpdir, {"allowed_ops": "Allowed: merge, deploy"})

        payload = json.dumps({"tool": "Write"})
        result = subprocess.run([str(script)], input=payload.encode(), env=env, cwd=tmpdir, capture_output=True)
        output = result.stdout.decode()
        assert result.returncode == 0
        assert "State Machine Reminder" in output
        assert "Allowed: merge, deploy" in output

        # Non-matching state should be silent
        quiet_env = stub_env(
            tmpdir,
            {
                "task_json": '{"state":"review","id":"TASK-1"}',
                "allowed_ops": "",
            },
        )
        quiet = subprocess.run([str(script)], input=payload.encode(), env=quiet_env, cwd=tmpdir, capture_output=True)
        assert quiet.stdout.decode().strip() == ""


def test_prevent_prod_edits_template_renders():
    content = render_hook(
        "prevent-prod-edits.sh.template",
        id="prod-guard",
        type="PreToolUse",
        description="prevent prod edits",
        blocking=True,
        config={"protected_patterns": ["^prod/", "secrets\\.env"]},
    )
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        script = write_script(content, tmpdir)
        env = stub_env(tmpdir)

        payload = json.dumps({"args": {"file_path": "prod/config.yml"}})
        result = subprocess.run([str(script)], input=payload.encode(), env=env, cwd=tmpdir, capture_output=True)
        output = result.stdout.decode()
        assert result.returncode == 1
        assert "Edit blocked" in output
        assert "^prod/" in output

        ok_payload = json.dumps({"args": {"file_path": "src/app.js"}})
        ok = subprocess.run([str(script)], input=ok_payload.encode(), env=env, cwd=tmpdir, capture_output=True)
        assert ok.returncode == 0
        assert ok.stdout.decode().strip() == ""


def test_check_tests_template_renders():
    content = render_hook(
        "check-tests.sh.template",
        id="check-tests",
        type="PreToolUse",
        description="check for tests",
        blocking=False,
        config={"warn_if_missing": True, "skip_test_files": True},
    )
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        script = write_script(content, tmpdir)
        env = stub_env(tmpdir)
        payload = json.dumps({"args": {"file_path": "src/foo.py"}})

        missing = subprocess.run(
            [str(script)], input=payload.encode(), env=env, cwd=tmpdir, capture_output=True
        )
        assert "No test file found for: src/foo.py" in missing.stdout.decode()

        (tmpdir / "src").mkdir(parents=True, exist_ok=True)
        (tmpdir / "src" / "foo_test.py").write_text("# test")

        present = subprocess.run(
            [str(script)], input=payload.encode(), env=env, cwd=tmpdir, capture_output=True
        )
        assert present.stdout.decode().strip() == ""


def test_stop_validate_template_renders():
    content = render_hook(
        "stop-validate.sh.template",
        id="stop-validate",
        type="SessionEnd",
        description="validate stop",
        blocking=False,
        config={"run_quick_validation": True},
    )
    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        script = write_script(content, tmpdir)
        env = stub_env(
            tmpdir,
            {
                "task_json": '{"state":"wip","id":"TASK-1"}',
                "test_exit": 1,
                "git_diff_exit": 1,
            },
        )

        result = subprocess.run([str(script)], input=b"{}", env=env, cwd=tmpdir, capture_output=True)
        output = result.stdout.decode()
        assert result.returncode == 0
        assert "Stop Validation" in output
        assert "wip state" in output
        assert "Uncommitted changes" in output
        assert "Quick tests failing" in output
        assert "Found 3 issues" in output
