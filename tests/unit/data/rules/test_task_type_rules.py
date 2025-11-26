from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[4]
RULES_DIR = ROOT / "src/edison/data/rules/task_types"
TASK_TYPES = [
    "feature",
    "bugfix",
    "refactor",
    "test",
    "docs",
    "chore",
    "hotfix",
]
REQUIRED_SECTIONS = [
    "applies_when",
    "validation_criteria",
    "delegation_guidance",
    "definition_of_done",
]


def test_task_type_rules_exist_and_are_complete() -> None:
    assert RULES_DIR.exists(), "Task type rules directory is missing"

    for task_type in TASK_TYPES:
        rule_path = RULES_DIR / f"{task_type}.yaml"
        assert rule_path.exists(), f"Missing rule file for task type: {task_type}"

        data = yaml.safe_load(rule_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"Rule file {rule_path} must parse to a mapping"
        assert data.get("task_type") == task_type, f"{rule_path} must declare task_type '{task_type}'"

        for section in REQUIRED_SECTIONS:
            assert section in data, f"{rule_path} missing required section: {section}"
            section_value = data[section]
            assert isinstance(section_value, list), f"{rule_path}:{section} must be a list"
            assert section_value, f"{rule_path}:{section} must not be empty"
            assert all(isinstance(item, str) and item.strip() for item in section_value), (
                f"{rule_path}:{section} entries must be non-empty strings"
            )
