"""Redaction helpers for vendor URLs and git error output.

This module exists to prevent accidental credential leakage when users provide
credential-bearing Git URLs (e.g., https://token@host/repo.git).
"""
from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

_SCHEME_CRED_RE = re.compile(r"([a-zA-Z][a-zA-Z0-9+.-]*://)([^\s/@]+(:[^\s/@]*)?@)")
_SCP_STYLE_RE = re.compile(r"\b(?!git@)([^\s@]+)@([^\s:]+):")


def redact_url_credentials(url: str) -> str:
    """Return a URL with any embedded credentials removed/redacted."""
    raw = str(url)
    if "://" in raw:
        parts = urlsplit(raw)
        if parts.username is None and parts.password is None:
            return raw
        host = parts.hostname or ""
        port = f":{parts.port}" if parts.port else ""
        netloc = f"{host}{port}"
        return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))

    # SSH "scp style": user@host:path
    m = re.match(r"(?P<user>[^@\s/]+)@(?P<host>[^:\s/]+):(?P<rest>.+)$", raw)
    if m and m.group("user") != "git":
        return f"<redacted>@{m.group('host')}:{m.group('rest')}"

    return raw


def redact_text_credentials(text: str) -> str:
    """Redact credential-bearing URL fragments from arbitrary text."""
    s = str(text)
    s = _SCHEME_CRED_RE.sub(r"\1<redacted>@", s)
    s = _SCP_STYLE_RE.sub(r"<redacted>@\2:", s)
    return s


def redact_git_args(args: list[str]) -> list[str]:
    """Redact credentials from git argv for safe logging."""
    return [redact_url_credentials(a) for a in args]
