from __future__ import annotations

import json
from pathlib import Path

from edison.core.composition import includes, metadata
from edison.core.composition.composers import CompositionEngine


def _write_core_validator(repo_root: Path, validator_id: str = "codex-global") -> Path:
    role = validator_id.split("-", 1)[0]
    core_dir = repo_root / ".edison/core/validators/global"
    core_dir.mkdir(parents=True, exist_ok=True)
    core_file = core_dir / f"{role}-core.md"
    core_file.write_text(
        "# Core Edison Principles\n"  # required marker for validate_composition
        f"Validator content for {validator_id}.\n"
        "Unique guidance to keep DRY checks quiet.\n",
        encoding="utf-8",
    )
    return core_file


def _minimal_config(validator_id: str = "codex-global") -> dict:
    return {
        "validation": {
            "roster": {
                "global": [{"id": validator_id}],
                "critical": [],
                "specialized": [],
            }
        },
        "validators": {"roster": {"global": [], "critical": [], "specialized": []}},
        "packs": {"active": []},
    }


def test_validators_emit_to_generated_validators(tmp_path: Path) -> None:
    """Composed validators write into `_generated/validators` with a manifest."""

    original_root = includes._REPO_ROOT_OVERRIDE
    _write_core_validator(tmp_path)

    try:
        engine = CompositionEngine(config=_minimal_config(), repo_root=tmp_path)
        results = engine.compose_validators(enforce_dry=False)

        project_dir = engine.project_dir
        expected_dir = project_dir / "_generated" / "validators"
        legacy_dir = project_dir / ".cache" / "composed"

        assert results, "compose_validators should return at least one validator"
        assert expected_dir.exists(), "new output directory should be created"
        assert not legacy_dir.exists(), "legacy cache path must not be created"

        for res in results.values():
            assert res.cache_path is not None
            assert res.cache_path.parent == expected_dir
            assert res.cache_path.exists()

        manifest = expected_dir / "manifest.json"
        assert manifest.exists(), "manifest should live alongside generated validators"
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        assert manifest_data, "manifest should record composed artifacts"
    finally:
        includes._REPO_ROOT_OVERRIDE = original_root


def test_cache_dir_helpers_target_generated_validators(tmp_path: Path) -> None:
    """Helper functions must resolve the unified `_generated/validators` path."""

    original_root = includes._REPO_ROOT_OVERRIDE
    _write_core_validator(tmp_path)

    includes._REPO_ROOT_OVERRIDE = tmp_path
    expected_dir = tmp_path / ".edison" / "_generated" / "validators"

    try:
        cache_dir = includes._cache_dir()
        assert cache_dir == expected_dir

        created = includes.get_cache_dir()
        assert created == expected_dir
        assert created.exists()

        legacy_dir = expected_dir.parent.parent / ".cache" / "composed"
        assert not legacy_dir.exists(), "legacy cache directory should never be created"
    finally:
        includes._REPO_ROOT_OVERRIDE = original_root


def test_metadata_ignores_legacy_composed_cache(tmp_path: Path) -> None:
    """Metadata inference should ignore deprecated `.cache/composed` artifacts."""

    project_dir = tmp_path / ".agents"
    legacy_dir = project_dir / ".cache" / "composed"
    legacy_dir.mkdir(parents=True, exist_ok=True)

    legacy_file = legacy_dir / "legacy-only.md"
    legacy_file.write_text(
        "# Should Not Read\n\n"
        "**Model**: gpt-legacy\n\n"
        "**Triggers**: `legacy`\n\n"
        "**Blocks on Fail**: ✅ YES\n",
        encoding="utf-8",
    )

    result = metadata.infer_validator_metadata(
        "legacy-only",
        repo_root=tmp_path,
        project_dir=project_dir,
        packs_dir=tmp_path / ".edison" / "packs",
        active_packs=[],
    )

    assert result["name"] == "Legacy Only"
    assert result["model"] == "codex"
    assert result["blocksOnFail"] is False
