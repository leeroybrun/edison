from __future__ import annotations

import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen

from edison.core.qa.engines.registry import EngineRegistry


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    _host, port = sock.getsockname()
    sock.close()
    return int(port)


def _http_responsive(url: str, *, timeout_seconds: float = 0.5) -> bool:
    req = Request(url, method="GET")
    try:
        with urlopen(req, timeout=timeout_seconds):
            return True
    except URLError:
        return False
    except Exception:
        return False


def _write_validation_config(repo_root: Path, yaml_text: str) -> None:
    cfg_dir = repo_root / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "validation.yaml").write_text(yaml_text, encoding="utf-8")


def _write_test_server(repo_root: Path, *, started_flag: Path) -> Path:
    server_path = repo_root / "test_web_server_guard_app.py"
    server_path.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import argparse",
                "import pathlib",
                "import signal",
                "from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer",
                "",
                "",
                "class Handler(BaseHTTPRequestHandler):",
                "    def do_GET(self):",
                "        body = b\"ok\"",
                "        self.send_response(200)",
                "        self.send_header(\"Content-Type\", \"text/plain\")",
                "        self.send_header(\"Content-Length\", str(len(body)))",
                "        self.end_headers()",
                "        self.wfile.write(body)",
                "",
                "    def log_message(self, format, *args):",
                "        return",
                "",
                "",
                "def main() -> int:",
                "    ap = argparse.ArgumentParser()",
                "    ap.add_argument(\"--port\", type=int, required=True)",
                "    ap.add_argument(\"--started-flag\", required=True)",
                "    args = ap.parse_args()",
                "",
                "    pathlib.Path(args.started_flag).write_text(\"started\", encoding=\"utf-8\")",
                "    httpd = ThreadingHTTPServer((\"127.0.0.1\", args.port), Handler)",
                "",
                "    def _stop(*_):",
                "        try:",
                "            httpd.shutdown()",
                "        except Exception:",
                "            pass",
                "",
                "    signal.signal(signal.SIGTERM, _stop)",
                "    signal.signal(signal.SIGINT, _stop)",
                "    httpd.serve_forever()",
                "    return 0",
                "",
                "",
                "if __name__ == \"__main__\":",
                "    raise SystemExit(main())",
                "",
            ]
        ),
        encoding="utf-8",
    )
    assert server_path.exists()
    assert started_flag.exists() is False
    return server_path


def _write_detached_server_scripts(repo_root: Path, *, pid_file: Path, source_file: Path) -> tuple[Path, Path, Path]:
    launcher = repo_root / "test_web_server_detached_start.py"
    stopper = repo_root / "test_web_server_detached_stop.py"
    verifier = repo_root / "test_web_server_detached_verify.py"

    launcher.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import argparse",
                "import os",
                "import signal",
                "import subprocess",
                "import sys",
                "from pathlib import Path",
                "",
                "",
                "def main() -> int:",
                "    ap = argparse.ArgumentParser()",
                "    ap.add_argument('--port', type=int, required=True)",
                "    ap.add_argument('--pidfile', required=True)",
                "    ap.add_argument('--sourcefile', required=True)",
                "    args = ap.parse_args()",
                "",
                "    # Record the directory the stack is intended to serve from.",
                "    Path(args.sourcefile).write_text(os.getcwd(), encoding='utf-8')",
                "",
                "    proc = subprocess.Popen(",
                "        [sys.executable, '-m', 'http.server', str(args.port), '--bind', '127.0.0.1'],",
                "        stdout=subprocess.DEVNULL,",
                "        stderr=subprocess.DEVNULL,",
                "        text=True,",
                "    )",
                "    Path(args.pidfile).write_text(str(proc.pid), encoding='utf-8')",
                "    return 0",
                "",
                "",
                "if __name__ == '__main__':",
                "    raise SystemExit(main())",
                "",
            ]
        ),
        encoding="utf-8",
    )

    stopper.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import argparse",
                "import os",
                "import signal",
                "import time",
                "from pathlib import Path",
                "",
                "",
                "def main() -> int:",
                "    ap = argparse.ArgumentParser()",
                "    ap.add_argument('--pidfile', required=True)",
                "    args = ap.parse_args()",
                "",
                "    pid_path = Path(args.pidfile)",
                "    if not pid_path.exists():",
                "        return 0",
                "    try:",
                "        pid = int(pid_path.read_text(encoding='utf-8').strip())",
                "    except Exception:",
                "        return 0",
                "",
                "    try:",
                "        os.kill(pid, signal.SIGTERM)",
                "    except Exception:",
                "        pass",
                "",
                "    deadline = time.time() + 3.0",
                "    while time.time() < deadline:",
                "        try:",
                "            os.kill(pid, 0)",
                "        except Exception:",
                "            break",
                "        time.sleep(0.05)",
                "",
                "    try:",
                "        pid_path.unlink(missing_ok=True)",
                "    except Exception:",
                "        pass",
                "    return 0",
                "",
                "",
                "if __name__ == '__main__':",
                "    raise SystemExit(main())",
                "",
            ]
        ),
        encoding="utf-8",
    )

    verifier.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import argparse",
                "import os",
                "import sys",
                "from pathlib import Path",
                "",
                "",
                "def main() -> int:",
                "    ap = argparse.ArgumentParser()",
                "    ap.add_argument('--sourcefile', required=True)",
                "    args = ap.parse_args()",
                "",
                "    expected = os.environ.get('AGENTS_PROJECT_ROOT') or ''",
                "    actual = Path(args.sourcefile).read_text(encoding='utf-8').strip() if Path(args.sourcefile).exists() else ''",
                "    if expected and actual == expected:",
                "        return 0",
                "    sys.stderr.write(f'expected={expected} actual={actual}\\n')",
                "    return 1",
                "",
                "",
                "if __name__ == '__main__':",
                "    raise SystemExit(main())",
                "",
            ]
        ),
        encoding="utf-8",
    )

    assert launcher.exists()
    assert stopper.exists()
    assert verifier.exists()
    assert pid_file.exists() is False
    assert source_file.exists() is False
    return launcher, stopper, verifier


def test_validator_blocks_when_web_server_required_and_not_running(
    isolated_project_env: Path,
) -> None:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    started_flag = isolated_project_env / "server-started.txt"

    _write_validation_config(
        isolated_project_env,
        f"""
validation:
  validators:
    test-web:
      name: "Test Web Validator"
      engine: pal-mcp
      wave: comprehensive
      blocking: true
      always_run: true
      web_server:
        ensure_running: true
        url: "{base_url}"
""".lstrip(),
    )

    registry = EngineRegistry(project_root=isolated_project_env)
    result = registry.run_validator(
        validator_id="test-web",
        task_id="T001",
        session_id="S001",
        worktree_path=isolated_project_env,
    )

    assert result.verdict == "blocked"
    assert started_flag.exists() is False


def test_validator_starts_and_stops_web_server_when_configured(
    isolated_project_env: Path,
) -> None:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    started_flag = isolated_project_env / "server-started.txt"
    server_script = _write_test_server(isolated_project_env, started_flag=started_flag)

    _write_validation_config(
        isolated_project_env,
        f"""
validation:
  validators:
    test-web:
      name: "Test Web Validator"
      engine: pal-mcp
      wave: comprehensive
      blocking: true
      always_run: true
      web_server:
        ensure_running: true
        url: "{base_url}"
        startup_timeout_seconds: 5
        start_command: "{sys.executable} {server_script} --port {port} --started-flag {started_flag}"
        stop_after: true
""".lstrip(),
    )

    assert _http_responsive(base_url) is False
    assert started_flag.exists() is False

    registry = EngineRegistry(project_root=isolated_project_env)
    result = registry.run_validator(
        validator_id="test-web",
        task_id="T001",
        session_id="S001",
        worktree_path=isolated_project_env,
    )

    assert result.verdict == "pending"  # pal-mcp
    assert started_flag.exists() is True
    assert _http_responsive(base_url) is False


def test_validator_restarts_when_verify_steps_fail_even_if_http_is_responsive(
    isolated_project_env: Path,
) -> None:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    wrong_root = isolated_project_env / "wrong"
    right_root = isolated_project_env / "right"
    wrong_root.mkdir(parents=True)
    right_root.mkdir(parents=True)

    pid_file = isolated_project_env / "server.pid"
    source_file = isolated_project_env / "server.source"
    launcher, stopper, verifier = _write_detached_server_scripts(
        isolated_project_env, pid_file=pid_file, source_file=source_file
    )

    # Start a "wrong" server from the wrong root (detached).
    subprocess.run(
        [sys.executable, str(launcher), "--port", str(port), "--pidfile", str(pid_file), "--sourcefile", str(source_file)],
        cwd=str(wrong_root),
        check=True,
        capture_output=True,
        text=True,
    )
    deadline = time.time() + 3.0
    while time.time() < deadline and _http_responsive(base_url) is False:
        time.sleep(0.05)
    assert _http_responsive(base_url) is True
    assert source_file.read_text(encoding="utf-8").strip() == str(wrong_root.resolve())

    _write_validation_config(
        isolated_project_env,
        f"""
validation:
  defaults:
    web_server:
      startup_timeout_seconds: 5
      shutdown_timeout_seconds: 5
  web_servers:
    e2e:
      url: "{base_url}"
      ensure_running: true
      start:
        command: "{sys.executable} {launcher} --port {port} --pidfile {pid_file} --sourcefile {source_file}"
      stop:
        command: "{sys.executable} {stopper} --pidfile {pid_file}"
      verify:
        steps:
          - kind: command
            command: "{sys.executable} {verifier} --sourcefile {source_file}"
          - kind: http
            url: "{{probe_url}}"
  validators:
    test-web:
      name: "Test Web Validator"
      engine: pal-mcp
      wave: comprehensive
      blocking: true
      always_run: true
      web_server:
        ref: e2e
""".lstrip(),
    )

    registry = EngineRegistry(project_root=isolated_project_env)
    result = registry.run_validator(
        validator_id="test-web",
        task_id="T001",
        session_id="S001",
        worktree_path=right_root,
    )

    assert result.verdict == "pending"  # pal-mcp
    # Restart should have occurred (server was wrong), but the lifecycle should
    # still stop the server after validator run.
    assert source_file.read_text(encoding="utf-8").strip() == str(right_root.resolve())
    assert _http_responsive(base_url) is False


def test_validator_blocks_when_verify_steps_fail_and_no_start_command(
    isolated_project_env: Path,
) -> None:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"

    wrong_root = isolated_project_env / "wrong-verify"
    wrong_root.mkdir(parents=True)

    pid_file = isolated_project_env / "server.pid"
    source_file = isolated_project_env / "server.source"
    launcher, stopper, verifier = _write_detached_server_scripts(
        isolated_project_env, pid_file=pid_file, source_file=source_file
    )

    # Start server (detached) so HTTP is responsive.
    subprocess.run(
        [sys.executable, str(launcher), "--port", str(port), "--pidfile", str(pid_file), "--sourcefile", str(source_file)],
        cwd=str(wrong_root),
        check=True,
        capture_output=True,
        text=True,
    )
    deadline = time.time() + 3.0
    while time.time() < deadline and _http_responsive(base_url) is False:
        time.sleep(0.05)
    assert _http_responsive(base_url) is True

    _write_validation_config(
        isolated_project_env,
        f"""
validation:
  validators:
    test-web:
      name: "Test Web Validator"
      engine: pal-mcp
      wave: comprehensive
      blocking: true
      always_run: true
      web_server:
        ensure_running: true
        url: "{base_url}"
        verify:
          steps:
            - kind: command
              command: "{sys.executable} {verifier} --sourcefile {source_file}"
        # No start command configured → cannot restart.
        stop_after: true
        stop_command: "{sys.executable} {stopper} --pidfile {pid_file}"
""".lstrip(),
    )

    registry = EngineRegistry(project_root=isolated_project_env)
    result = registry.run_validator(
        validator_id="test-web",
        task_id="T001",
        session_id="S001",
        worktree_path=isolated_project_env,
    )

    assert result.verdict == "blocked"
    assert "verify" in (result.summary or "").lower()


def test_web_server_lock_blocks_other_runs_until_released(
    isolated_project_env: Path,
) -> None:
    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    lock_key = f"test-lock-{port}"

    started_flag = isolated_project_env / "server-started.txt"
    server_script = _write_test_server(isolated_project_env, started_flag=started_flag)

    _write_validation_config(
        isolated_project_env,
        f"""
validation:
  defaults:
    web_server:
      lock:
        enabled: true
        key: "{lock_key}"
        scope: global
      shutdown_timeout_seconds: 1
      probe_timeout_seconds: 0.2
      poll_interval_seconds: 0.05
  validators:
    test-web:
      name: "Test Web Validator"
      engine: pal-mcp
      wave: comprehensive
      blocking: true
      always_run: true
      web_server:
        ensure_running: true
        url: "{base_url}"
        startup_timeout_seconds: 5
        start_command: "{sys.executable} {server_script} --port {port} --started-flag {started_flag}"
        stop_after: true
""".lstrip(),
    )

    from edison.core.utils.io.locking import acquire_file_lock
    from edison.core.web_server import web_server_lock_path

    lock_path = web_server_lock_path(repo_root=isolated_project_env, key=lock_key, scope="global")

    registry = EngineRegistry(project_root=isolated_project_env)
    done = {"flag": False}

    def _run() -> None:
        registry.run_validator(
            validator_id="test-web",
            task_id="T001",
            session_id="S001",
            worktree_path=isolated_project_env,
        )
        done["flag"] = True

    with acquire_file_lock(lock_path, timeout=3.0, repo_root=isolated_project_env):
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        time.sleep(0.2)
        assert done["flag"] is False

    t.join(timeout=15.0)
    assert done["flag"] is True
