from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from tests.helpers.paths import get_repo_root


def _load_real_jsonschema():
    """Load jsonschema from site-packages, bypassing the core stub."""
    import importlib

    sys.modules.pop("jsonschema", None)
    core_path = get_repo_root().resolve()
    original_path = list(sys.path)
    try:
        cleaned_path: list[str] = []
        for entry in original_path:
            try:
                if Path(entry).resolve().samefile(core_path):
                    continue
            except (OSError, FileNotFoundError):
                pass
            cleaned_path.append(entry)
        sys.path = cleaned_path
        return importlib.import_module("jsonschema")
    finally:
        sys.path = original_path


def _load_schema() -> dict:
    from edison.core.utils.io import read_yaml
    from edison.data import get_data_path

    schema_path = get_data_path("schemas", "domain/session.schema.yaml")
    return read_yaml(schema_path, default={}, raise_on_error=True)


def _base_session() -> dict:
    return {
        "id": "session-xyz",
        "state": "active",
        "meta": {
            "sessionId": "session-xyz",
            "createdAt": "2025-11-22T00:00:00Z",
            "lastActive": "2025-11-22T00:05:00Z",
            "status": "active",
        },
    }


def _write_session(tmp_path: Path, payload: dict) -> dict:
    session_path = tmp_path / "session.json"
    session_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return json.loads(session_path.read_text(encoding="utf-8"))


def test_session_allows_meta_continuation_object(tmp_path: Path) -> None:
    jsonschema = _load_real_jsonschema()
    schema = _load_schema()
    session = _base_session()
    session["meta"]["continuation"] = {
        "mode": "soft",
        "maxIterations": 3,
        "cooldownSeconds": 10,
        "stopOnBlocked": True,
    }

    payload = _write_session(tmp_path, session)
    jsonschema.validate(instance=payload, schema=schema)


def test_session_continuation_object_rejects_unknown_fields(tmp_path: Path) -> None:
    jsonschema = _load_real_jsonschema()
    schema = _load_schema()
    session = _base_session()
    session["meta"]["continuation"] = {
        "mode": "soft",
        "unknownKey": "nope",
    }

    payload = _write_session(tmp_path, session)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=schema)


def test_session_meta_still_rejects_unknown_fields(tmp_path: Path) -> None:
    jsonschema = _load_real_jsonschema()
    schema = _load_schema()
    session = _base_session()
    session["meta"]["notAllowed"] = True

    payload = _write_session(tmp_path, session)
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=payload, schema=schema)
