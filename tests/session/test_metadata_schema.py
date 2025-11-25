from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


def _load_real_jsonschema():
    """Load jsonschema from site-packages, bypassing the core stub."""
    sys.modules.pop("jsonschema", None)
    core_path = Path(__file__).resolve().parents[2]
    original_path = list(sys.path)
    cleaned_path = []
    for entry in sys.path:
        try:
            if Path(entry).resolve().samefile(core_path):
                continue
        except Exception:
            pass
        cleaned_path.append(entry)
    sys.path = cleaned_path

    import importlib
    import io

    # Defensive: ensure stdlib io module is loaded with StringIO/TextIOWrapper
    sys.modules.pop("io", None)
    io = importlib.import_module("io")  # type: ignore[assignment]
    sys.modules["io"] = io
    # Reset any path hints that could shadow stdlib io
    if hasattr(io, "__path__"):
        try:
            del io.__path__  # type: ignore[attr-defined]
        except Exception:
            io.__path__ = []  # type: ignore[attr-defined]
    spec = getattr(io, "__spec__", None)
    if spec and hasattr(spec, "submodule_search_locations"):
        spec.submodule_search_locations = []  # type: ignore[attr-defined]

    module = importlib.import_module("jsonschema")
    sys.path = original_path
    return module


_jsonschema = _load_real_jsonschema()
validate = _jsonschema.validate  # type: ignore[attr-defined]
ValidationError = _jsonschema.exceptions.ValidationError  # type: ignore[attr-defined]


SCHEMA_PATH = Path(".edison/core/schemas/session.schema.json")


def _load_schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _base_session() -> dict:
    return {
        "id": "session-xyz",
        "state": "Active",
        "createdAt": "2025-11-22T00:00:00Z",
        "lastActiveAt": "2025-11-22T00:05:00Z",
    }


def _write_session(tmp_path: Path, payload: dict) -> dict:
    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return json.loads(session_path.read_text(encoding="utf-8"))


def test_session_allows_auto_start_metadata(tmp_path: Path) -> None:
    schema = _load_schema()
    session = _base_session()
    session["meta"] = {
        "sessionId": "session-xyz",
        "owner": "owner-123",
        "mode": "start",
        "status": "wip",
        "createdAt": "2025-11-22T00:00:00Z",
        "lastActive": "2025-11-22T00:05:00Z",
        "createdBy": "edison",
        "orchestratorProfile": "claude",
        "autoStarted": True,
        "promptPath": "prompts/auto/start.md",
        "namingStrategy": "edison",
    }

    payload = _write_session(tmp_path, session)
    validate(instance=payload, schema=schema)


def test_session_rejects_invalid_auto_start_values(tmp_path: Path) -> None:
    schema = _load_schema()
    session = _base_session()
    session["meta"] = {
        "sessionId": "session-xyz",
        "owner": "owner-123",
        "createdBy": "system",  # invalid enum
        "namingStrategy": "random",  # invalid enum
    }

    payload = _write_session(tmp_path, session)
    with pytest.raises(ValidationError):
        validate(instance=payload, schema=schema)


def test_session_without_auto_start_fields_still_valid(tmp_path: Path) -> None:
    schema = _load_schema()
    session = _base_session()
    session["meta"] = {
        "sessionId": "session-xyz",
        "owner": "owner-123",
        "mode": "start",
        "status": "wip",
    }

    payload = _write_session(tmp_path, session)
    validate(instance=payload, schema=schema)
