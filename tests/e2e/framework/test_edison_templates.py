import subprocess
from pathlib import Path
from edison.core.utils.subprocess import run_with_timeout


def test_agents_md_include_resolves_without_error():
    """Verify .agents/AGENTS.md includes render without 'include missing'"""

    result = run_with_timeout(
        ["./.edison/core/scripts/include/render-md.sh", ".agents/AGENTS.md"],
        capture_output=True,
        text=True,
        cwd=Path.cwd(),
        check=False,
    )

    assert result.returncode == 0, f"Renderer exited non-zero: {result.returncode}\nSTDERR:\n{result.stderr}"

    assert "include missing" not in result.stdout, (
        "Edison AGENTS.md template include failed to resolve. "
        f"Renderer output:\n{result.stdout[:500]}"
    )

    assert "Agent Compliance Checklist" in result.stdout, (
        "Rendered AGENTS.md missing Agent Compliance Checklist section"
    )

    assert "Fail-Closed" in result.stdout or "fail closed" in result.stdout.lower(), (
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
    result = run_with_timeout(
        ["./.edison/core/scripts/include/render-md.sh", ".edison/core/guides/START.SESSION.md"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, f"Renderer exited non-zero: {result.returncode}\nSTDERR:\n{result.stderr}"
    assert "include missing" not in result.stdout, (
        "START.SESSION.md template include failed to resolve"
    )

    # Verify key sections present
    assert "Session Intake Checklist" in result.stdout
    assert ("Task Claiming" in result.stdout) or ("claim" in result.stdout.lower())


def test_rendered_agents_md_is_comprehensive():
    """Verify rendered AGENTS.md contains all critical sections"""
    result = run_with_timeout(
        ["./.edison/core/scripts/include/render-md.sh", ".agents/AGENTS.md"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Renderer exited non-zero: {result.returncode}\nSTDERR:\n{result.stderr}"
    rendered = result.stdout

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
    result = run_with_timeout(
        ["./.edison/core/scripts/include/render-md.sh", ".edison/core/guides/START.SESSION.md"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"Renderer exited non-zero: {result.returncode}\nSTDERR:\n{result.stderr}"
    rendered = result.stdout

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