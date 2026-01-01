"""Trusted command evidence helpers (read/write + optional HMAC).

These helpers implement a small, deterministic format for command evidence files
used by the `task ready` gate.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class CommandEvidence:
    runner: str
    cmd: str
    exit_code: int
    started_at: str
    hmac_sha256: str | None = None


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_payload(text: str) -> bytes:
    lines = []
    for raw in (text or "").splitlines():
        if raw.startswith("HMAC:"):
            continue
        lines.append(raw)
    payload = "\n".join(lines).rstrip("\n") + "\n"
    return payload.encode("utf-8")


def compute_hmac_sha256(key: str, text: str) -> str:
    payload = _canonical_payload(text)
    return hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def extract_hmac(text: str) -> str | None:
    for raw in (text or "").splitlines():
        if raw.startswith("HMAC:"):
            val = raw.split(":", 1)[1].strip()
            return val or None
    return None


def parse_exit_code(text: str) -> int | None:
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.upper().startswith("EXIT_CODE:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except Exception:
                return None
        if line.lower().startswith("exit code:"):
            try:
                return int(line.split(":", 1)[1].strip())
            except Exception:
                return None
    return None


def write_command_evidence(
    path: Path,
    *,
    runner: str,
    cmd: str,
    exit_code: int,
    started_at: str | None = None,
    hmac_key: str | None = None,
) -> None:
    started = started_at or _utc_iso_now()
    base = (
        f"RUNNER: {runner}\n"
        f"START: {started}\n"
        f"CMD: {cmd}\n"
        f"EXIT_CODE: {int(exit_code)}\n"
        "END\n"
    )
    if hmac_key:
        digest = compute_hmac_sha256(hmac_key, base)
        base = base + f"HMAC: {digest}\n"
    path.write_text(base, encoding="utf-8")


def verify_command_evidence_hmac(path: Path, *, hmac_key: str) -> tuple[bool, str]:
    """Verify a command evidence file's HMAC signature.

    Returns:
        (ok, message) where message is suitable for user-facing errors.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return False, f"HMAC validation failed: could not read {path}: {e}"

    expected = extract_hmac(text)
    if not expected:
        return False, f"HMAC validation failed: missing HMAC line in {path}"

    actual = compute_hmac_sha256(hmac_key, text)
    if not hmac.compare_digest(expected, actual):
        return False, f"HMAC validation failed: signature mismatch for {path}"

    return True, "ok"


__all__ = [
    "CommandEvidence",
    "compute_hmac_sha256",
    "extract_hmac",
    "parse_exit_code",
    "write_command_evidence",
    "verify_command_evidence_hmac",
]

