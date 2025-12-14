from __future__ import annotations

from tests.helpers.paths import get_repo_root


def test_all_rule_ids_resolve_and_extract() -> None:
    """Rules must compose and anchored extracts must not be empty.

    Canonical: rules are defined in bundled YAML registries under `edison.data/rules/registry.yml`
    and composed via `edison.core.rules.RulesRegistry`.
    """
    from edison.core.rules import RulesRegistry

    repo_root = get_repo_root()
    registry = RulesRegistry(repo_root)
    rules = registry.load_composed_rules()
    assert rules, "No composed rules found"

    failures: list[str] = []
    for r in rules:
        rid = r.get("id") or ""
        if not rid:
            failures.append("rule missing id")
            continue
        try:
            payload = registry.compose_rule(rid)
        except Exception as e:
            failures.append(f"{rid}: compose_rule failed: {e}")
            continue
        content = payload.get("content") or ""
        if not isinstance(content, str) or not content.strip():
            failures.append(f"{rid}: extracted content is empty")

    assert not failures, "Rules registry anchor check failed:\n- " + "\n- ".join(failures)