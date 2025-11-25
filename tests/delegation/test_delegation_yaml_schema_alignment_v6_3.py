from __future__ import annotations

import json
import importlib.util
import site
import sys
from pathlib import Path

import pytest
import yaml

# Use the real jsonschema package from site-packages (avoid local stub at .edison/core/jsonschema.py)
_orig_sys_path = list(sys.path)
real_site_paths = site.getsitepackages()
sys.modules.pop("jsonschema", None)
spec = importlib.util.find_spec("jsonschema", real_site_paths)
if spec is None or spec.loader is None:
    pytest.skip("jsonschema package not available in environment", allow_module_level=True)
if spec.origin and ".edison/core/jsonschema.py" in spec.origin:
    pytest.skip("jsonschema real package not found (local stub detected)", allow_module_level=True)
jsonschema_real = importlib.util.module_from_spec(spec)
spec.loader.exec_module(jsonschema_real)  # type: ignore[arg-type]
Draft202012Validator = jsonschema_real.Draft202012Validator
ValidationError = jsonschema_real.exceptions.ValidationError


CORE_ROOT = Path(__file__).resolve().parents[2]
CONFIG = CORE_ROOT / "config" / "delegation.yaml"
SCHEMA = CORE_ROOT / "schemas" / "delegation.schema.json"


def _load() -> tuple[dict, dict]:
    assert CONFIG.exists(), f"Missing delegation config: {CONFIG}"
    assert SCHEMA.exists(), f"Missing delegation schema: {SCHEMA}"
    cfg = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    return cfg, schema


def test_delegation_yaml_conforms_to_schema():
    cfg, schema = _load()
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(cfg), key=lambda e: list(e.path))
    assert not errors, "; ".join(err.message for err in errors)


def test_delegation_rejects_unknown_fields():
    cfg, schema = _load()
    validator = Draft202012Validator(schema)

    cfg_with_extra = json.loads(json.dumps(cfg))  # deep copy
    cfg_with_extra.setdefault("delegation", {}).setdefault("implementers", {})[
        "unknown"
    ] = "bad"

    with pytest.raises(ValidationError):
        validator.validate(cfg_with_extra)
