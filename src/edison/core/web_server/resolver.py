from __future__ import annotations

from typing import Any

from edison.core.utils.merge import deep_merge


def resolve_web_server_config(
    *,
    full_config: dict[str, Any],
    validator_web_server: Any,
) -> dict[str, Any] | None:
    """Resolve a validator's web_server config via defaults + profiles + overrides.

    Supported forms:
    - None: no web server config
    - "<name>": shorthand for {"ref": "<name>"}
    - {"ref": "<name>", ...overrides}
    - {inline_config}
    """
    if validator_web_server is None:
        return None

    raw: dict[str, Any] | None = None
    if isinstance(validator_web_server, str):
        raw = {"ref": validator_web_server}
    elif isinstance(validator_web_server, dict):
        raw = dict(validator_web_server)
    else:
        return None

    validation = full_config.get("validation") or {}
    defaults = {}
    if isinstance(validation, dict):
        defaults_dict = validation.get("defaults") if isinstance(validation.get("defaults"), dict) else {}
        defaults = ((defaults_dict.get("web_server") or defaults_dict.get("webServer") or {}) if isinstance(defaults_dict, dict) else {})
    if not isinstance(defaults, dict):
        defaults = {}

    profiles = {}
    if isinstance(validation, dict):
        profiles = validation.get("web_servers") or validation.get("webServers") or {}
    if not isinstance(profiles, dict):
        profiles = {}

    ref = raw.get("ref")
    base: dict[str, Any] = {}
    if isinstance(ref, str) and ref.strip():
        profile = profiles.get(ref.strip())
        if profile is None:
            raise ValueError(f"Unknown web_server ref: {ref.strip()}")
        if not isinstance(profile, dict):
            raise ValueError(f"web_servers.{ref.strip()} must be a mapping")
        base = deep_merge(base, profile)

    merged = deep_merge(defaults, base)
    overrides = dict(raw)
    overrides.pop("ref", None)
    merged = deep_merge(merged, overrides)
    return merged


__all__ = ["resolve_web_server_config"]
