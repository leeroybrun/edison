from __future__ import annotations

import pytest

from edison.core.web_server.models import WebServerConfig


def test_web_server_config_rejects_legacy_start_command_key() -> None:
    raw = {
        "url": "http://127.0.0.1:3000",
        "start_command": "pnpm dev",
    }
    with pytest.raises(ValueError, match=r"web_server\.start\.command"):
        WebServerConfig.from_raw(raw)


def test_web_server_config_rejects_legacy_stop_command_key() -> None:
    raw = {
        "url": "http://127.0.0.1:3000",
        "stop_command": "pnpm stop",
    }
    with pytest.raises(ValueError, match=r"web_server\.stop\.command"):
        WebServerConfig.from_raw(raw)


def test_web_server_config_rejects_legacy_base_url_key() -> None:
    raw = {"base_url": "http://127.0.0.1:3000"}
    with pytest.raises(ValueError, match=r"web_server\.url"):
        WebServerConfig.from_raw(raw)


def test_web_server_config_rejects_legacy_camelcase_keys() -> None:
    raw = {
        "url": "http://127.0.0.1:3000",
        "ensureRunning": True,
        "healthcheckUrl": "http://127.0.0.1:3000/health",
        "startupTimeoutSeconds": 5,
    }
    with pytest.raises(ValueError, match=r"ensureRunning|healthcheckUrl|startupTimeoutSeconds"):
        WebServerConfig.from_raw(raw)


def test_web_server_config_rejects_nested_legacy_keys() -> None:
    raw = {
        "url": "http://127.0.0.1:3000",
        "start": {"command": "pnpm dev", "successExitCodes": [0]},
        "stop": {"command": "pnpm stop", "runEvenIfNoProcess": True},
        "lock": {"timeoutSeconds": 1},
        "verify": {"steps": [{"kind": "docker_source", "container": "x", "mountDest": "/app"}]},
    }
    with pytest.raises(ValueError, match=r"successExitCodes|runEvenIfNoProcess|timeoutSeconds|mountDest"):
        WebServerConfig.from_raw(raw)
