from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[4]
RULES_DIR = ROOT / "src/edison/data/rules"
ALLOWED_SEVERITIES = {"error", "warning", "info"}


def _iter_rule_files():
    for pattern in ("*.yaml", "*.yml"):
        yield from RULES_DIR.rglob(pattern)


def _validate_blocking_and_severity(payload: dict, ctx: str, issues: list) -> None:
    if "blocking" not in payload:
        issues.append(f"{ctx}: missing 'blocking' flag")
    elif not isinstance(payload.get("blocking"), bool):
        issues.append(f"{ctx}: 'blocking' must be a bool")

    if "severity" not in payload:
        issues.append(f"{ctx}: missing 'severity'")
    else:
        severity = payload.get("severity")
        if severity not in ALLOWED_SEVERITIES:
            allowed = ", ".join(sorted(ALLOWED_SEVERITIES))
            issues.append(f"{ctx}: severity '{severity}' not in [{allowed}]")


def test_all_rule_yaml_files_declare_blocking_and_severity() -> None:
    rule_files = list(_iter_rule_files())
    assert rule_files, "No rule YAML files found under src/edison/data/rules"

    issues = []
    for path in rule_files:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data is not None, f"{path} is empty"

        if path.name == "registry.yml":
            rules = data.get("rules")
            assert isinstance(rules, list), f"{path}: 'rules' must be a list"
            for idx, rule in enumerate(rules):
                assert isinstance(rule, dict), f"{path}[{idx}] must be a mapping"
                _validate_blocking_and_severity(rule, f"{path}[{idx}]", issues)
        else:
            assert isinstance(data, dict), f"{path} must parse to a mapping"
            _validate_blocking_and_severity(data, str(path), issues)

    assert not issues, " ; ".join(issues)
