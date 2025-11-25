import os
import re
import pytest
from pathlib import Path


def test_validator_templates_directory_exists():
    """Verify templates directory created"""
    templates_dir = Path(".edison/core/validators/templates")
    assert templates_dir.exists(), "Validator templates directory must exist"
    assert templates_dir.is_dir(), "templates path must be a directory"


def test_validator_templates_are_project_agnostic():
    """Verify validator templates have no project-specific content"""
    templates_dir = Path(".edison/core/validators/templates")

    # Patterns that indicate project-specific content
    project_name = os.environ.get("PROJECT_NAME", "").strip()

    forbidden_patterns = [
        (r"\bproject\b", "project name 'project'"),
        (r"\bproject\b", "capitalized project name 'project'"),
        (r"\bexample-app\b", "specific app name 'example-app'"),
        (r"\bExampleApp\b", "capitalized app name 'ExampleApp'"),
        (r"Next\.js 16", "specific version number"),
        (r"React 19", "specific version number"),
        (r"uistyles.*4", "specific version number"),
    ]

    if project_name:
        forbidden_patterns.append((re.escape(project_name), "repository name"))

    violations = []

    if not templates_dir.exists():
        pytest.skip("templates directory not created yet")

    for template_file in templates_dir.glob("*.md"):
        content = template_file.read_text()

        for pattern, description in forbidden_patterns:
            matches = list(re.finditer(pattern, content, re.IGNORECASE))
            if matches:
                violations.append({
                    "file": template_file.name,
                    "pattern": description,
                    "count": len(matches),
                    "examples": [content[m.start():m.end()] for m in matches[:3]]
                })

    assert len(violations) == 0, (
        f"Found {len(violations)} project-specific content violations:\n" +
        "\n".join(
            f"  {v['file']}: {v['count']}x {v['pattern']} - {v['examples']}"
            for v in violations
        )
    )


def test_validator_templates_use_placeholders():
    """Verify templates use {PROJECT_NAME} and other placeholders"""
    templates_dir = Path(".edison/core/validators/templates")

    required_placeholders = {
        "global-comprehensive.md": ["{PROJECT_NAME}", "{MODEL_ID}", "{INTERFACE}"],
        "critical-security.md": ["{PROJECT_NAME}"],
        "critical-performance.md": ["{PROJECT_NAME}"],
    }

    if not templates_dir.exists():
        pytest.skip("templates directory not created yet")

    for template_name, placeholders in required_placeholders.items():
        template_path = templates_dir / template_name
        if not template_path.exists():
            continue  # Skip if not created yet

        content = template_path.read_text()

        missing = [p for p in placeholders if p not in content]
        assert len(missing) == 0, (
            f"{template_name} missing placeholders: {missing}"
        )


def test_global_template_has_all_validation_dimensions():
    """Verify global template covers all validation dimensions"""
    template_path = Path(".edison/core/validators/templates/global-comprehensive.md")

    if not template_path.exists():
        pytest.skip("Template not created yet")

    content = template_path.read_text()

    required_dimensions = [
        "Architecture",
        "Code Quality",
        "Testing",
        "TDD",
        "Documentation",
        "Error Handling",
        "Performance",
        "Security",
    ]

    missing = [dim for dim in required_dimensions if dim not in content]
    assert len(missing) == 0, (
        f"Global template missing validation dimensions: {missing}"
    )


def test_all_three_templates_created_and_valid():
    """Verify all three validator templates exist and are well-formed"""
    templates_dir = Path(".edison/core/validators/templates")

    if not templates_dir.exists():
        pytest.skip("templates directory not created yet")

    expected_templates = [
        "global-comprehensive.md",
        "critical-security.md",
        "critical-performance.md",
    ]

    for template_name in expected_templates:
        template_path = templates_dir / template_name

        assert template_path.exists(), f"Template missing: {template_name}"

        content = template_path.read_text()

        # Minimum length check (should be substantial)
        min_length = 3000 if "global" in template_name else 2000
        assert len(content) > min_length, (
            f"{template_name} too short: {len(content)} chars (expected >{min_length})"
        )

        # Should have structure (headers)
        assert content.count("#") >= 5, (
            f"{template_name} lacks structure (needs more headers)"
        )

        # Should have validation guidance
        assert ("Check" in content) or ("Verify" in content), (
            f"{template_name} missing validation instructions"
        )
