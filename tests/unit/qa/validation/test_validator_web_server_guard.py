from __future__ import annotations

import socket
import sys
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
