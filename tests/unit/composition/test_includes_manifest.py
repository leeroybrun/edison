import json
from pathlib import Path
from edison.core.composition import includes
from edison.core.composition.includes import _write_cache


def test_write_cache_updates_manifest(tmp_path):
    """Test cache manifest updates using real file system operations.

    NO MOCKS: Uses real includes module with _REPO_ROOT_OVERRIDE for isolation.
    """
    # Set the repo root override for testing (this is an allowed testing mechanism)
    original_override = includes._REPO_ROOT_OVERRIDE
    try:
        includes._REPO_ROOT_OVERRIDE = tmp_path

        # 1. First write
        deps = [tmp_path / "foo.txt"]
        (tmp_path / "foo.txt").touch()

        # Create the project config directory structure
        project_dir = tmp_path / ".edison"
        project_dir.mkdir(parents=True, exist_ok=True)

        out_path = _write_cache("val1", "content1", deps, "hash1")

        assert out_path.exists()
        assert out_path.read_text(encoding="utf-8") == "content1"

        # Manifest should be in the cache directory
        cache_dir = project_dir / "_generated" / "validators"
        manifest = cache_dir / "manifest.json"
        assert manifest.exists()
        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert data["val1"]["hash"] == "hash1"

        # 2. Second write (update)
        out_path2 = _write_cache("val2", "content2", [], "hash2")

        data = json.loads(manifest.read_text(encoding="utf-8"))
        assert len(data) == 2
        assert data["val1"]["hash"] == "hash1"
        assert data["val2"]["hash"] == "hash2"
    finally:
        includes._REPO_ROOT_OVERRIDE = original_override


# ============================================================================
# T-016 Pattern 2A: NO LEGACY - safe_include() shim removal tests
# ============================================================================


def test_modern_include_optional_syntax_works(tmp_path):
    """Modern {{include-optional:path}} syntax MUST work (baseline test).

    NO MOCKS: Uses real resolve_includes with _REPO_ROOT_OVERRIDE.
    """
    # Setup: Use override for isolation
    original_override = includes._REPO_ROOT_OVERRIDE
    try:
        includes._REPO_ROOT_OVERRIDE = tmp_path

        # Create test file structure
        base_file = tmp_path / "base.md"
        include_file = tmp_path / "fragment.md"
        include_file.write_text("INCLUDED CONTENT", encoding="utf-8")

        # Test modern syntax
        content = "Start {{include-optional:fragment.md}} End"
        result, deps = includes.resolve_includes(content, base_file)

        assert result == "Start INCLUDED CONTENT End"
        assert include_file in deps
    finally:
        includes._REPO_ROOT_OVERRIDE = original_override


def test_modern_include_optional_syntax_with_missing_file(tmp_path):
    """Modern {{include-optional:path}} with missing file MUST return empty (silent skip).

    NO MOCKS: Uses real resolve_includes with _REPO_ROOT_OVERRIDE.
    """
    # Setup: Use override for isolation
    original_override = includes._REPO_ROOT_OVERRIDE
    try:
        includes._REPO_ROOT_OVERRIDE = tmp_path

        base_file = tmp_path / "base.md"

        # Test modern syntax with missing file
        content = "Start {{include-optional:nonexistent.md}} End"
        result, deps = includes.resolve_includes(content, base_file)

        assert result == "Start  End"  # Empty string, silent skip
        assert len(deps) == 0
    finally:
        includes._REPO_ROOT_OVERRIDE = original_override


def test_legacy_safe_include_syntax_is_rejected(tmp_path):
    """Legacy {{safe_include('path', fallback='...')}} syntax MUST be REJECTED (T-016 - NO LEGACY).

    This test will FAIL before implementation (shim converts it).
    After implementation, legacy syntax should remain unchanged (not converted).

    NO MOCKS: Uses real resolve_includes with _REPO_ROOT_OVERRIDE.
    """
    # Setup: Use override for isolation
    original_override = includes._REPO_ROOT_OVERRIDE
    try:
        includes._REPO_ROOT_OVERRIDE = tmp_path

        base_file = tmp_path / "base.md"
        include_file = tmp_path / "fragment.md"
        include_file.write_text("SHOULD NOT BE INCLUDED", encoding="utf-8")

        # Test legacy syntax - should NOT be converted anymore
        legacy_content = "Start {{ safe_include('fragment.md', fallback='FALLBACK') }} End"
        result, deps = includes.resolve_includes(legacy_content, base_file)

        # After removal: Legacy syntax should remain unchanged (NOT converted to include-optional)
        assert "SHOULD NOT BE INCLUDED" not in result, "Legacy syntax was converted (shim still active)"
        assert "safe_include" in result, "Legacy syntax should remain in output (not processed)"
        assert len(deps) == 0, "No dependencies should be resolved for legacy syntax"
    finally:
        includes._REPO_ROOT_OVERRIDE = original_override


def test_legacy_safe_include_with_fallback_is_not_converted(tmp_path):
    """Legacy {{safe_include('path', fallback='text')}} with fallback MUST NOT be converted.

    This test will FAIL before implementation (shim converts it).
    After removal, the legacy syntax should be left as-is in the output.

    NO MOCKS: Uses real resolve_includes with _REPO_ROOT_OVERRIDE.
    """
    # Setup: Use override for isolation
    original_override = includes._REPO_ROOT_OVERRIDE
    try:
        includes._REPO_ROOT_OVERRIDE = tmp_path

        base_file = tmp_path / "base.md"

        # Test legacy syntax with missing file and fallback
        legacy_content = "{{ safe_include('nonexistent.md', fallback='<!-- Missing -->') }}"
        result, deps = includes.resolve_includes(legacy_content, base_file)

        # After removal: Legacy syntax should remain unchanged (entire syntax string preserved)
        assert "safe_include" in result, "Legacy syntax should remain in output"
        assert result == legacy_content, "Entire legacy syntax should be unchanged (not processed)"
        assert len(deps) == 0
    finally:
        includes._REPO_ROOT_OVERRIDE = original_override


def test_mixed_modern_and_legacy_syntax(tmp_path):
    """Content with BOTH modern and legacy syntax: only modern should be processed.

    This test verifies that after shim removal:
    - Modern {{include-optional:path}} is processed correctly
    - Legacy {{safe_include(...)}} is left unchanged

    NO MOCKS: Uses real resolve_includes with _REPO_ROOT_OVERRIDE.
    """
    # Setup: Use override for isolation
    original_override = includes._REPO_ROOT_OVERRIDE
    try:
        includes._REPO_ROOT_OVERRIDE = tmp_path

        base_file = tmp_path / "base.md"
        modern_file = tmp_path / "modern.md"
        legacy_file = tmp_path / "legacy.md"

        modern_file.write_text("MODERN CONTENT", encoding="utf-8")
        legacy_file.write_text("LEGACY CONTENT", encoding="utf-8")

        # Content with both syntaxes
        content = (
            "Modern: {{include-optional:modern.md}}\n"
            "Legacy: {{ safe_include('legacy.md', fallback='FALLBACK') }}"
        )
        result, deps = includes.resolve_includes(content, base_file)

        # Modern syntax processed
        assert "MODERN CONTENT" in result
        assert modern_file in deps

        # Legacy syntax NOT processed (remains as-is)
        assert "safe_include" in result
        assert "LEGACY CONTENT" not in result
        assert legacy_file not in deps
    finally:
        includes._REPO_ROOT_OVERRIDE = original_override


def test_no_safe_include_regex_pattern_defined(tmp_path):
    """Legacy safe_include() syntax is no longer supported.

    This test verifies that the old safe_include() regex has been removed
    and that resolve_includes() does not process this legacy syntax.

    NO MOCKS: Uses real resolve_includes with _REPO_ROOT_OVERRIDE.
    """
    # Setup: Use override for isolation
    original_override = includes._REPO_ROOT_OVERRIDE
    try:
        includes._REPO_ROOT_OVERRIDE = tmp_path

        base_file = tmp_path / "base.md"

        # Verify regex pattern no longer exists (backward compat removed)
        assert not hasattr(includes, "_SAFE_INCLUDE_RE")

        # Legacy syntax should NOT be processed
        legacy_content = "{{ safe_include('test.md', fallback='FB') }}"
        result, _ = includes.resolve_includes(legacy_content, base_file)

        # Legacy syntax should remain unchanged (not processed)
        assert "safe_include" in result
    finally:
        includes._REPO_ROOT_OVERRIDE = original_override
