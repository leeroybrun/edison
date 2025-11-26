import os
import pytest

# List of files to check
FILES_TO_CHECK = [
    "src/edison/data/guidelines/README.md",
    "src/edison/data/guidelines/shared/VALIDATION.md",
    "src/edison/data/guidelines/shared/CONTEXT7.md",
    "src/edison/data/guidelines/shared/TDD.md",
]

# List of placeholders that should be resolved/removed
PLACEHOLDERS = [
    "{{framework}}",
    "{{orm}}",
    "{{test-framework}}",
    "{{component-framework}}",
    "{{web-framework}}",
    "{{library}}",
    "{{task_id}}",
]

def test_no_unresolved_placeholders():
    """
    Validates that specific guidelines files do not contain unresolved placeholders.
    """
    project_root = os.getcwd()
    failures = []

    for relative_path in FILES_TO_CHECK:
        file_path = os.path.join(project_root, relative_path)
        
        # Ensure file exists
        if not os.path.exists(file_path):
            pytest.fail(f"File not found: {relative_path}")
            continue

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        for placeholder in PLACEHOLDERS:
            if placeholder in content:
                failures.append(f"Found '{placeholder}' in {relative_path}")

    if failures:
        pytest.fail("\n".join(failures))

if __name__ == "__main__":
    pytest.main([__file__])
