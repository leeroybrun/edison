"""Minimal MCP stdio client for Edison memory providers.

This is intentionally small and synchronous:
- Memory providers call MCP tools as a boundary integration.
- Calls are best-effort and fail-open in providers.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from edison.core.mcp.config import McpServerConfig, build_mcp_servers


@dataclass(frozen=True)
class McpToolResult:
    content: list[dict[str, Any]]


def _encode_message(obj: dict[str, Any]) -> bytes:
    body = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    header = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii")
    return header + body


def _readline_with_timeout(stream, *, deadline: float) -> bytes:  # type: ignore[no-untyped-def]
    while True:
        if time.time() > deadline:
            raise TimeoutError("Timed out waiting for MCP header line")
        line = stream.readline()
        if line:
            return line
        time.sleep(0.01)


def _read_exact(stream, n: int, *, deadline: float) -> bytes:  # type: ignore[no-untyped-def]
    buf = bytearray()
    while len(buf) < n:
        if time.time() > deadline:
            raise TimeoutError("Timed out waiting for MCP message body")
        chunk = stream.read(n - len(buf))
        if not chunk:
            time.sleep(0.01)
            continue
        buf.extend(chunk)
    return bytes(buf)


def _read_message(stdout, *, timeout_seconds: int) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    deadline = time.time() + max(0.1, float(timeout_seconds))
    headers: dict[str, str] = {}
    while True:
        line = _readline_with_timeout(stdout, deadline=deadline)
        if line in (b"\n", b"\r\n", b""):
            break
        try:
            k, v = line.decode("ascii", errors="ignore").split(":", 1)
            headers[k.strip().lower()] = v.strip()
        except Exception:
            continue

    length_raw = headers.get("content-length")
    if not length_raw:
        raise ValueError("MCP message missing Content-Length header")
    length = int(length_raw)
    body = _read_exact(stdout, length, deadline=deadline)
    return json.loads(body.decode("utf-8", errors="strict"))


def _start_server(server: McpServerConfig, *, timeout_seconds: int) -> subprocess.Popen[bytes]:
    env = os.environ.copy()
    env.update(server.env or {})
    return subprocess.Popen(
        [server.command] + list(server.args),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )


def _initialize(proc: subprocess.Popen[bytes], *, timeout_seconds: int) -> None:
    assert proc.stdin is not None
    assert proc.stdout is not None

    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "clientInfo": {"name": "edison", "version": "0"},
            "capabilities": {},
        },
    }
    proc.stdin.write(_encode_message(init_req))
    proc.stdin.flush()
    _ = _read_message(proc.stdout, timeout_seconds=timeout_seconds)

    notif = {"jsonrpc": "2.0", "method": "initialized", "params": {}}
    proc.stdin.write(_encode_message(notif))
    proc.stdin.flush()


def call_tool(
    *,
    project_root: Path,
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    timeout_seconds: int = 10,
) -> Optional[McpToolResult]:
    """Call an MCP tool by spawning the configured server and making one request."""
    try:
        _, servers, _ = build_mcp_servers(project_root)
        server = servers.get(server_id)
        if server is None:
            return None
    except Exception:
        return None

    proc: subprocess.Popen[bytes] | None = None
    try:
        proc = _start_server(server, timeout_seconds=timeout_seconds)
        if proc.stdin is None or proc.stdout is None:
            return None

        _initialize(proc, timeout_seconds=timeout_seconds)

        req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }
        proc.stdin.write(_encode_message(req))
        proc.stdin.flush()
        msg = _read_message(proc.stdout, timeout_seconds=timeout_seconds)
        res = msg.get("result")
        if not isinstance(res, dict):
            return None
        content = res.get("content")
        if not isinstance(content, list):
            return None
        return McpToolResult(content=[c for c in content if isinstance(c, dict)])
    except Exception:
        return None
    finally:
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                proc.wait(timeout=1)
            except Exception:
                pass


__all__ = ["call_tool", "McpToolResult"]
