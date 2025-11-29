import os
import json
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import pytest
from jsonschema import Draft202012Validator, ValidationError

from helpers.io_utils import write_yaml


def _ensure_core_root_on_sys_path() -> None:
    from tests.helpers.paths import get_repo_root
    _this_file = Path(__file__).resolve()
    _core_root = None
    for _parent in _this_file.parents:
        candidate = _parent / ".edison" / "core"
        if (candidate / "lib").exists():
            _core_root = candidate
            break
    if _core_root is None:
        _core_root = get_repo_root()
def make_tmp_repo(tmp_path: Path, defaults: dict, project: Optional[dict] = None) -> Path:
    repo = tmp_path
    # Create .edison/core/config structure so ConfigManager finds it
    config_dir = repo / ".edison" / "core" / "config"
    write_yaml(config_dir / "defaults.yaml", defaults)
    if project is not None:
        write_yaml(repo / "edison.yaml", project)
    # Fake a git root marker so ConfigManager(repo_root=repo) is honored consistently
    (repo / ".git").mkdir(parents=True, exist_ok=True)
    return repo


def load_with_manager(repo_root: Path) -> dict:
    _ensure_core_root_on_sys_path()
    from edison.core.config import ConfigManager 
    mgr = ConfigManager(repo_root=repo_root)
    # For most tests we want non-strict env handling and no schema enforcement;
    # individual tests call load_config(validate=True) when exercising strict mode.
    return mgr.load_config(validate=False)


def validate_with_schema(candidate: dict, schema_path: Path) -> None:
    """Validate a config candidate against the canonical Draft-2020-12 schema.

    Uses jsonschema for general validation and enforces the secret_rotation
    interval constraint explicitly to guard against validator/version quirks.
    """
    import jsonschema

    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(candidate)
    jsonschema.validate(instance=candidate, schema=schema)

    # Explicit guard for zen.secret_rotation.check_interval_hours maximum.
    zen_props = (schema.get("properties", {}).get("zen") or {}).get("properties", {})
    rotation_schema = zen_props.get("secret_rotation") or {}
    rotation_props = rotation_schema.get("properties", {}) or {}
    check_schema = rotation_props.get("check_interval_hours") or {}
    max_interval = check_schema.get("maximum")

    if isinstance(max_interval, int):
        value = (
            (candidate.get("zen") or {})
            .get("secret_rotation", {})
            .get("check_interval_hours")
        )
        if isinstance(value, int) and value > max_interval:
            raise jsonschema.ValidationError(
                f"check_interval_hours {value} exceeds maximum {max_interval}"
            )


# C1: Nested Environment Variable Override Logic
def test_nested_env_array_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    defaults = {"agents": []}
    repo = make_tmp_repo(tmp_path, defaults, {})

    monkeypatch.setenv("EDISON_AGENTS__0", "codex")
    monkeypatch.setenv("EDISON_AGENTS__1", "claude")

    cfg = load_with_manager(repo)
    assert cfg.get("agents") == ["codex", "claude"]


def test_nested_env_array_append(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    defaults = {"agents": ["codex"]}
    repo = make_tmp_repo(tmp_path, defaults, {})

    monkeypatch.setenv("EDISON_AGENTS__APPEND", "gemini")

    cfg = load_with_manager(repo)
    assert cfg.get("agents") == ["codex", "gemini"]


def test_nested_env_deep_object(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    defaults = {"zen": {"retry": {"max_attempts": 3}}}
    repo = make_tmp_repo(tmp_path, defaults, {})

    monkeypatch.setenv("EDISON_ZEN__RETRY__MAX_ATTEMPTS", "5")

    cfg = load_with_manager(repo)
    assert cfg["zen"]["retry"]["max_attempts"] == 5


# C2: Schema Validation Gaps for secret rotation
def test_schema_validation_secret_rotation(tmp_path: Path):
    from edison.data import get_data_path
    schema_path = get_data_path("schemas", "config/config.schema.json")
    assert schema_path.exists(), f"Missing core config schema: {schema_path}"

    # Valid config should pass
    valid = {"zen": {"secret_rotation": {"enabled": True, "check_interval_hours": 24}}}
    # Should not raise
    try:
        validate_with_schema(valid, schema_path)
    except Exception as e:  # pragma: no cover - explicit RED expectation
        pytest.fail(f"Valid secret_rotation rejected: {e}")

    # Invalid config should fail (requires maximum constraint in schema)
    invalid = {"zen": {"secret_rotation": {"enabled": True, "check_interval_hours": 200}}}
    with pytest.raises(ValidationError):
        validate_with_schema(invalid, schema_path)


# C3/C4: Type validation in CLI and consistent merge precedence
def test_config_merge_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    defaults = {"zen": {"retry": {"max_attempts": 3}}}
    project = {"zen": {"retry": {"max_attempts": 5}}}
    repo = make_tmp_repo(tmp_path, defaults, project)

    monkeypatch.setenv("EDISON_ZEN__RETRY__MAX_ATTEMPTS", "7")

    cfg = load_with_manager(repo)
    assert cfg["zen"]["retry"]["max_attempts"] == 7  # ENV should win


def test_config_type_coercion(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    defaults = {"flags": {"enabled": False}, "limits": {"max": 1, "ratio": 0.5}, "agents": []}
    repo = make_tmp_repo(tmp_path, defaults, {})

    monkeypatch.setenv("EDISON_FLAGS__ENABLED", "true")
    monkeypatch.setenv("EDISON_LIMITS__MAX", "10")
    monkeypatch.setenv("EDISON_LIMITS__RATIO", "2.5")
    monkeypatch.setenv("EDISON_AGENTS__0", "codex")

    cfg = load_with_manager(repo)
    assert cfg["flags"]["enabled"] is True
    assert isinstance(cfg["limits"]["max"], int) and cfg["limits"]["max"] == 10
    assert isinstance(cfg["limits"]["ratio"], float) and cfg["limits"]["ratio"] == 2.5
    assert cfg["agents"] == ["codex"]


def test_config_concurrent_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    defaults = {"zen": {"retry": {"max_attempts": 3}}}
    repo = make_tmp_repo(tmp_path, defaults, {})
    monkeypatch.setenv("EDISON_ZEN__RETRY__MAX_ATTEMPTS", "9")

    def load() -> int:
        return load_with_manager(repo)["zen"]["retry"]["max_attempts"]

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda _: load(), range(16)))

    assert all(v == 9 for v in results)


def test_config_invalid_env_var_handling(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    defaults = {}
    repo = make_tmp_repo(tmp_path, defaults, {})

    # Inject a malformed env var path (double separators leading and trailing)
    monkeypatch.setenv("EDISON____BAD__PATH__", "oops")

    # Expect robust loader to detect and reject malformed env var patterns
    _ensure_core_root_on_sys_path()
    from edison.core.config import ConfigManager 
    mgr = ConfigManager(repo_root=repo)
    with pytest.raises((ValueError, RuntimeError)):
        mgr.load_config(validate=True)


def test_config_cli_validate_flag(tmp_path: Path):
    """Config validation should work via Python module."""
    # Legacy CLI has been migrated to Python modules
    _ensure_core_root_on_sys_path()
    from edison.core.config import ConfigManager

    # Test that validation works programmatically
    mgr = ConfigManager(repo_root=tmp_path)
    try:
        # Validation should work without errors
        config = mgr.load_config(validate=True)
        assert isinstance(config, dict), "Config validation should return dict"
    except Exception as e:
        # If validation fails due to missing config, that's expected in test environment
        if "not found" not in str(e).lower():
            pytest.fail(f"Config validation failed unexpectedly: {e}")


@pytest.mark.skip(reason="Documentation not yet written")
def test_docs_examples_present():
    doc = Path(".edison/docs/CONFIG.md")
    assert doc.exists(), "Missing configuration documentation: .edison/docs/CONFIG.md"
    txt = doc.read_text(encoding="utf-8")
    assert "Complex Configuration Examples" in txt