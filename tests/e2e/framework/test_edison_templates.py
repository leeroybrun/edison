from pathlib import Path
import pytest

pytestmark = pytest.mark.skip(reason="Template tests need update for new src/edison/data/ layout")


def test_agents_md_include_resolves_without_error():
    """Verify .agents/AGENTS.md includes render without 'include missing'"""
    from edison.core.composition.includes import resolve_includes

    agents_md = Path(".agents/AGENTS.md")
    if not agents_md.exists():
        pytest.skip(".agents/AGENTS.md not found")

    content = agents_md.read_text(encoding="utf-8")
    try:
        rendered, _ = resolve_includes(content, agents_md)
    except Exception as e:
        pytest.fail(f"Include resolution failed: {e}")

    assert "include missing" not in rendered.lower(), (
        "Edison AGENTS.md template include failed to resolve. "
        f"Renderer output:\n{rendered[:500]}"
    )

    assert "Agent Compliance Checklist" in rendered, (
        "Rendered AGENTS.md missing Agent Compliance Checklist section"
    )

    assert "Fail-Closed" in rendered or "fail closed" in rendered.lower(), (
        "Rendered AGENTS.md missing fail-closed enforcement language"
    )


def test_agents_md_has_all_13_checklist_items():
    """Verify all 13 Agent Compliance Checklist items present in template"""
    template_path = Path(".edison/core/templates/AGENTS.md")
    assert template_path.exists(), "AGENTS.md template must exist"

    content = template_path.read_text()

    # Check for checklist header
    assert "Agent Compliance Checklist" in content
    assert "Fail-Closed" in content or "fail closed" in content.lower()

    # Check for all 13 numbered items
    for i in range(1, 14):
        pattern = f"{i}. **"
        assert pattern in content, f"Missing checklist item {i}"

    # Verify key items by content (sampling)
    assert "Mandatory preload" in content, "Missing item 1: Mandatory preload"
    assert "TDD is law" in content, "Missing item 5: TDD is law"
    assert "Delegate, don't do" in content, "Missing item 6: Delegation"
    assert "Context7 first" in content, "Missing item 7: Context7"
    assert "Validator waves" in content, "Missing item 9: Validator waves"
    assert "Honest status" in content, "Missing item 10: Honest status"
    assert "Fail closed" in content or "fail-closed" in content.lower(), "Missing item 13: Fail closed"


def test_start_session_include_resolves():
    """Verify START.SESSION.md include resolves without error"""
    from edison.core.composition.includes import resolve_includes

    start_session = Path(".edison/core/guides/START.SESSION.md")
    if not start_session.exists():
        pytest.skip("START.SESSION.md not found")

    content = start_session.read_text(encoding="utf-8")
    try:
        rendered, _ = resolve_includes(content, start_session)
    except Exception as e:
        pytest.fail(f"Include resolution failed: {e}")

    assert "include missing" not in rendered.lower(), (
        "START.SESSION.md template include failed to resolve"
    )

    # Verify key sections present
    assert "Session Intake Checklist" in rendered
    assert ("Task Claiming" in rendered) or ("claim" in rendered.lower())


def test_rendered_agents_md_is_comprehensive():
    """Verify rendered AGENTS.md contains all critical sections"""
    from edison.core.composition.includes import resolve_includes

    agents_md = Path(".agents/AGENTS.md")
    if not agents_md.exists():
        pytest.skip(".agents/AGENTS.md not found")

    content = agents_md.read_text(encoding="utf-8")
    try:
        rendered, _ = resolve_includes(content, agents_md)
    except Exception as e:
        pytest.fail(f"Include resolution failed: {e}")

    # Critical sections that MUST be present
    required_sections = [
        "Agent Compliance Checklist",
        "Mandatory Preload",
        "Quick Navigation",
        "Rule Registry",
        "Session Workflow",
        "Task, QA, and Session Directory",
        "Orchestration Model",
        "Session Isolation",
        "Parallel Implementation Pattern",
        "Fail-Closed",
    ]

    missing = [section for section in required_sections if section not in rendered]

    assert len(missing) == 0, (
        f"Rendered AGENTS.md missing {len(missing)} critical sections:\n" +
        "\n".join(f"  - {s}" for s in missing)
    )

    # Verify substantial content (not just headers)
    assert len(rendered) > 8000, (
        f"Rendered AGENTS.md too short: {len(rendered)} chars (expected >8000)"
    )


def test_rendered_start_session_is_comprehensive():
    """Verify rendered START.SESSION.md contains all critical sections"""
    from edison.core.composition.includes import resolve_includes

    start_session = Path(".edison/core/guides/START.SESSION.md")
    if not start_session.exists():
        pytest.skip("START.SESSION.md not found")

    content = start_session.read_text(encoding="utf-8")
    try:
        rendered, _ = resolve_includes(content, start_session)
    except Exception as e:
        pytest.fail(f"Include resolution failed: {e}")

    required_sections = [
        "Session Intake Checklist",
        "Task Claiming Workflow",
        "TDD",
        "Automated Checks",
        "QA",
        "Validation",
        "Session Isolation",
        "Session Timeout",
    ]

    missing = [section for section in required_sections if section not in rendered]

    assert len(missing) == 0, (
        f"Rendered START.SESSION.md missing {len(missing)} sections:\n" +
        "\n".join(f"  - {s}" for s in missing)
    )

    assert len(rendered) > 3000, (
        f"Rendered START.SESSION.md too short: {len(rendered)} chars (expected >3000)"
    )