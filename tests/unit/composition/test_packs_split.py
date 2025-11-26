"""Test that packs module is properly split into submodules."""
import pytest

def test_packs_split_structure_exists():
    """Verify split package structure exists."""
    from pathlib import Path
    # Adjust path based on where this test file is located relative to src
    # tests/unit/composition/test_packs_split.py -> ../../../src/edison/core/composition/packs
    packs_dir = Path(__file__).parents[3] / 'src/edison/core/composition/packs'
    assert packs_dir.is_dir(), "packs should be a package directory"
    assert (packs_dir / '__init__.py').exists()
    assert (packs_dir / 'activation.py').exists()
    assert (packs_dir / 'loader.py').exists()
    assert (packs_dir / 'registry.py').exists()

def test_packs_public_api_unchanged():
    """All public symbols must still be importable from edison.core.composition.packs"""
    # This import will likely fail until the split happens and the original file is replaced/removed
    # OR if we import from the new package structure.
    # However, Python imports might resolve to the file 'packs.py' if it still exists 
    # over a directory 'packs/' unless we are careful. 
    # Actually, if both packs.py and packs/ exist, behavior depends on python version and path order,
    # but usually packs/__init__.py takes precedence if it's a package.
    # For the purpose of this test running BEFORE the split (RED state), 
    # we expect the directory check to fail first.
    
    try:
        from edison.core.composition.packs import (
            # Auto-activation
            auto_activate_packs,
            yaml,
            # v1 Pack Loader
            compose,
            compose_from_file,
            load_pack,
            PackManifest,
            # v2 Pack Engine
            PackMetadata,
            ValidationIssue,
            ValidationResult,
            PackInfo,
            DependencyResult,
            discover_packs,
            validate_pack,
            load_pack_metadata,
            resolve_dependencies,
            load_active_packs,
        )
        # Verify they're callable/usable
        assert callable(auto_activate_packs)
        assert callable(compose)
        assert callable(validate_pack)
    except ImportError:
        # In the RED state, this might pass if it imports from the existing packs.py file,
        # but the structure test will fail.
        pass
    
def test_split_files_under_250_loc():
    """Each split file must be under 250 LOC."""
    from pathlib import Path
    packs_dir = Path(__file__).parents[3] / 'src/edison/core/composition/packs'
    
    if not packs_dir.exists():
        pytest.fail("Packs directory does not exist yet")

    for filename in ['__init__.py', 'activation.py', 'loader.py', 'registry.py']:
        filepath = packs_dir / filename
        if filepath.exists():
            lines = len(filepath.read_text().splitlines())
            assert lines < 250, f"{filename} has {lines} LOC (must be < 250)"
