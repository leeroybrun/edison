from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[4]
RULES_DIR = ROOT / "src/edison/data/rules/file_patterns"

REQUIRED_RULES = {
    "testing": {
        "patterns": ["**/*.test.ts", "**/*.spec.ts"],
        "validators": ["testing"],
    },
    "api": {
        "patterns": ["**/*.api.ts", "**/route.ts"],
        "validators": ["api"],
    },
    "database": {
        "patterns": ["**/schema.prisma"],
        "validators": ["database"],
    },
    "react": {
        "patterns": ["**/components/**/*.tsx"],
        "validators": ["react"],
    },
    "nextjs": {
        "patterns": ["**/page.tsx", "**/layout.tsx"],
        "validators": ["nextjs"],
    },
    "tailwind": {
        "patterns": ["**/tailwind.config.*"],
        "validators": ["tailwind"],
    },
}

REQUIRED_KEYS = ["id", "title", "patterns", "validators", "rationale"]


def test_file_pattern_rules_exist_and_cover_required_patterns() -> None:
    assert RULES_DIR.exists(), "File pattern rules directory is missing"

    rule_files = {path.stem: path for path in RULES_DIR.glob("*.yaml")}
    assert rule_files, "No file pattern rules found"
    assert set(rule_files.keys()) == set(REQUIRED_RULES.keys()), (
        "File pattern rules must match expected set"
    )

    for name, path in rule_files.items():
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), f"{path} must parse to a mapping"

        for key in REQUIRED_KEYS:
            assert key in data, f"{path} missing required field: {key}"

        patterns = data.get("patterns")
        validators = data.get("validators")
        rationale = data.get("rationale")

        assert isinstance(patterns, list) and patterns, f"{path}:patterns must be a non-empty list"
        assert all(isinstance(p, str) and p.strip() for p in patterns), (
            f"{path}:patterns entries must be non-empty strings"
        )

        assert isinstance(validators, list) and validators, f"{path}:validators must be a non-empty list"
        assert all(isinstance(v, str) and v.strip() for v in validators), (
            f"{path}:validators entries must be non-empty strings"
        )

        assert isinstance(rationale, str) and rationale.strip(), (
            f"{path}:rationale must be a non-empty string"
        )

        expected = REQUIRED_RULES[name]
        for pattern in expected["patterns"]:
            assert pattern in patterns, f"{path} missing required pattern: {pattern}"
        for validator in expected["validators"]:
            assert validator in validators, (
                f"{path} missing required validator trigger: {validator}"
            )
