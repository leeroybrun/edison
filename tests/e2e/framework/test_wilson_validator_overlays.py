import pytest
from pathlib import Path


def test_project_overlays_directory_exists():
    """Verify overlays directory created in project-specific .agents"""
    overlays_dir = Path(".agents/validators/overlays")
    assert overlays_dir.exists(), "project validator overlays directory must exist"
    assert overlays_dir.is_dir(), "overlays path must be a directory"


def test_project_overlays_contain_project_specific_content():
    """Verify overlays have project-specific context (not generic)"""
    overlays_dir = Path(".agents/validators/overlays")

    global_overlay = overlays_dir / "global-project-context.md"
    if not global_overlay.exists():
        pytest.skip("Overlay not created yet")

    content = global_overlay.read_text()

    # MUST contain project-specific content (case insensitive)
    project_indicators = [
        "project",
        "app",
    ]

    found = [indicator for indicator in project_indicators if indicator.lower() in content.lower()]
    assert len(found) >= 1, (
        f"Overlay missing project-specific content. Expected project or ExampleApp mentions, found none."
    )

    # Should reference project tech stack
    tech_stack_items = ["nextjs", "React", "prisma", "sqldb", "uistyles"]
    found_tech = [item for item in tech_stack_items if item in content]
    assert len(found_tech) >= 2, (
        f"Overlay should mention project tech stack. Found {len(found_tech)}/5 items: {found_tech}"
    )


def test_global_overlay_has_post_training_packages():
    """Verify global overlay lists project's post-training packages"""
    overlay_path = Path(".agents/validators/overlays/global-project-context.md")

    if not overlay_path.exists():
        pytest.skip("Overlay not created yet")

    content = overlay_path.read_text()

    # project uses several post-training packages
    post_training = [
        "nextjs",  # or "Next" or "next"
        "React",
        "uistyles",
        "prisma",
    ]

    found = [pkg for pkg in post_training if pkg in content]
    assert len(found) >= 3, (
        f"Overlay should list project's post-training packages. Found {len(found)}/4: {found}"
    )


def test_overlays_have_reasonable_size():
    """Verify overlays have substantial content (not just stubs)"""
    overlays_dir = Path(".agents/validators/overlays")

    for overlay_file in overlays_dir.glob("*.md"):
        content = overlay_file.read_text()

        min_length = 1000  # Should be at least 1000 chars
        assert len(content) >= min_length, (
            f"{overlay_file.name} too short: {len(content)} chars (expected >={min_length})"
        )


def test_security_overlay_mentions_project_security_requirements():
    """Verify security overlay has project-specific security context"""
    overlay_path = Path(".agents/validators/overlays/security-project-requirements.md")

    if not overlay_path.exists():
        pytest.skip("Overlay not created yet")

    content = overlay_path.read_text()

    # Should reference project-specific security considerations
    assert "project" in content.lower() or "app" in content.lower()

    # Should mention tech-specific security
    tech_security = ["nextjs", "API", "Database", "Authentication"]
    found = [term for term in tech_security if term in content]
    assert len(found) >= 2, f"Security overlay should mention project tech security. Found: {found}"


def test_performance_overlay_mentions_project_performance():
    """Verify performance overlay includes project-specific performance guidance"""
    overlay_path = Path(".agents/validators/overlays/performance-project-benchmarks.md")

    if not overlay_path.exists():
        pytest.skip("Overlay not created yet")

    content = overlay_path.read_text()

    # Should reference project or ExampleApp
    assert "project" in content.lower() or "app" in content.lower()

    # Should mention performance patterns relevant to project
    perf_terms = ["prisma", "nextjs", "N+1", "revalidate"]
    found = [term for term in perf_terms if term in content]
    assert len(found) >= 2, f"Performance overlay missing key project performance terms. Found: {found}"
