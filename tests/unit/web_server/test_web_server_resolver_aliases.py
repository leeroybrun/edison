from __future__ import annotations

from edison.core.web_server.resolver import resolve_web_server_config


def test_resolve_web_server_config_accepts_webServers_and_webServer_defaults() -> None:
    full_config = {
        "validation": {
            "defaults": {
                "webServer": {
                    "probe_timeout_seconds": 1.0,
                }
            },
            "webServers": {
                "browser-e2e": {
                    "url": "http://localhost:3001",
                    "ensure_running": True,
                }
            },
        }
    }

    resolved = resolve_web_server_config(full_config=full_config, validator_web_server="browser-e2e")
    assert resolved is not None
    assert resolved.get("url") == "http://localhost:3001"
    assert resolved.get("ensure_running") is True
    # Defaults should still apply.
    assert resolved.get("probe_timeout_seconds") == 1.0

