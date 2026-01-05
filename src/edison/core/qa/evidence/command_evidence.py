"""Trusted command evidence helpers (read/write + optional HMAC).

Edison uses command evidence files as *proof* that automation was run and passed.
The evidence format is intentionally machine-parseable so guards can fail-closed
on real command outcomes (exit code), not merely “file exists”.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from edison.core.utils.text.frontmatter import format_frontmatter, parse_frontmatter


@dataclass(frozen=True, slots=True)
class CommandEvidenceV1:
    """Parsed command evidence v1 frontmatter (output is stored separately)."""

    task_id: str
    round: int
    command_name: str
    command: str
    cwd: str
    exit_code: int
    started_at: str
    completed_at: str
    runner: str = "edison"
    shell: str = "bash"
    pipefail: bool = True
    hmac_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidenceVersion": 1,
            "evidenceKind": "command",
            "taskId": self.task_id,
            "round": int(self.round),
            "commandName": self.command_name,
            "command": self.command,
            "cwd": self.cwd,
            "shell": self.shell,
            "pipefail": bool(self.pipefail),
            "startedAt": self.started_at,
            "completedAt": self.completed_at,
            "exitCode": int(self.exit_code),
            "runner": self.runner,
            "hmacSha256": self.hmac_sha256,
        }


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonicalize_for_hmac(text: str) -> bytes:
    """Return canonical bytes for HMAC validation.

    Canonicalization rule: remove `hmacSha256` from YAML frontmatter if present,
    then re-serialize frontmatter and append the remaining body unchanged.
    """
    doc = parse_frontmatter(text or "")
    fm = dict(doc.frontmatter or {})
    fm.pop("hmacSha256", None)
    fm_block = format_frontmatter(fm, exclude_none=True) if fm else ""
    body = doc.content or ""
    payload = (fm_block + body).rstrip("\n") + "\n"
    return payload.encode("utf-8")


def compute_hmac_sha256(key: str, text: str) -> str:
    payload = _canonicalize_for_hmac(text)
    return hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def parse_exit_code(text: str) -> int | None:
    """Best-effort exit code extraction.

    Supports:
    - command evidence v1 YAML frontmatter (`exitCode`)
    - legacy line formats: `EXIT_CODE: <int>` and `exit code: <int>`
    """
    raw = text or ""
    try:
        doc = parse_frontmatter(raw)
        if doc.frontmatter:
            v = doc.frontmatter.get("exitCode")
            if v is not None:
                return int(v)
    except Exception:
        pass

    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.upper().startswith("EXIT_CODE:"):
            try:
                return int(s.split(":", 1)[1].strip())
            except Exception:
                return None
        if s.lower().startswith("exit code:"):
            try:
                return int(s.split(":", 1)[1].strip())
            except Exception:
                return None
    return None


def parse_command_evidence(path: Path) -> dict[str, Any] | None:
    """Parse a command evidence file (v1) into a dict.

    Returns None when the file cannot be parsed as v1 command evidence.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except Exception:
        return None

    try:
        doc = parse_frontmatter(text)
    except Exception:
        return None

    fm = doc.frontmatter or {}
    if not isinstance(fm, dict) or not fm:
        return None
    if fm.get("evidenceKind") != "command":
        return None

    return {
        **fm,
        "output": doc.content or "",
    }


def write_command_evidence(
    *,
    path: Path,
    task_id: str,
    round_num: int,
    command_name: str,
    command: str,
    cwd: str,
    exit_code: int,
    output: str,
    started_at: datetime | str | None = None,
    completed_at: datetime | str | None = None,
    shell: str = "bash",
    pipefail: bool = True,
    runner: str = "edison evidence capture",
    hmac_key: str | None = None,
    fingerprint: dict[str, Any] | None = None,
) -> None:
    """Write command evidence v1 with optional HMAC."""
    started_s: str
    completed_s: str
    if isinstance(started_at, datetime):
        started_s = started_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    else:
        started_s = str(started_at).strip() if started_at else _utc_iso_now()
    if isinstance(completed_at, datetime):
        completed_s = completed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    else:
        completed_s = str(completed_at).strip() if completed_at else _utc_iso_now()

    ev = CommandEvidenceV1(
        task_id=str(task_id),
        round=int(round_num),
        command_name=str(command_name),
        command=str(command),
        cwd=str(cwd),
        exit_code=int(exit_code),
        started_at=started_s,
        completed_at=completed_s,
        runner=str(runner),
        shell=str(shell),
        pipefail=bool(pipefail),
        hmac_sha256=None,
    )

    fm = ev.to_dict()
    fp = fingerprint or {}
    fm["gitHead"] = str(fp.get("gitHead") or "")
    fm["gitDirty"] = bool(fp.get("gitDirty", False))
    fm["diffHash"] = str(fp.get("diffHash") or "")
    fm.pop("hmacSha256", None)
    content = format_frontmatter(fm, exclude_none=True) + (output or "")

    if hmac_key:
        digest = compute_hmac_sha256(hmac_key, content)
        fm["hmacSha256"] = digest
        content = format_frontmatter(fm, exclude_none=True) + (output or "")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def verify_command_evidence_hmac(path: Path, *, hmac_key: str) -> tuple[bool, str]:
    """Verify a command evidence file's HMAC signature (v1 only)."""
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except Exception as e:
        return False, f"HMAC validation failed: could not read {path}: {e}"

    try:
        doc = parse_frontmatter(text)
        fm = doc.frontmatter or {}
    except Exception as e:
        return False, f"HMAC validation failed: could not parse frontmatter in {path}: {e}"

    expected = fm.get("hmacSha256") if isinstance(fm, dict) else None
    if not isinstance(expected, str) or not expected.strip():
        return False, f"HMAC validation failed: missing hmacSha256 in {path}"

    actual = compute_hmac_sha256(hmac_key, text)
    if not hmac.compare_digest(expected.strip(), actual):
        return False, f"HMAC validation failed: signature mismatch for {path}"

    return True, "ok"


__all__ = [
    "CommandEvidenceV1",
    "compute_hmac_sha256",
    "parse_command_evidence",
    "parse_exit_code",
    "write_command_evidence",
    "verify_command_evidence_hmac",
]
