from __future__ import annotations

from pathlib import Path

from edison.core.composition.engine import TemplateEngine

from tests.helpers.paths import get_repo_root


ROOT = get_repo_root()
DATA_DIR = ROOT / "src/edison/data"


def _render(path: Path) -> str:
    engine = TemplateEngine(project_root=ROOT, source_dir=DATA_DIR)
    content = path.read_text(encoding="utf-8")
    rendered, _ = engine.process(content, entity_name=path.stem)
    return rendered


def test_constitution_base_files_exist() -> None:
    assert (DATA_DIR / "constitutions/agents-base.md").exists()
    assert (DATA_DIR / "constitutions/validators-base.md").exists()


def test_core_agents_do_not_emit_missing_include_errors() -> None:
    agents_dir = DATA_DIR / "agents"
    agent_files = sorted(agents_dir.glob("*.md"))
    assert len(agent_files) == 6

    for path in agent_files:
        rendered = _render(path)
        assert "<!-- ERROR: Include not found:" not in rendered
        assert "<!-- ERROR: Circular include detected:" not in rendered


def test_core_validators_do_not_emit_missing_include_errors() -> None:
    validators_dir = DATA_DIR / "validators"
    validator_files = sorted(validators_dir.rglob("*.md"))
    # __init__.py is excluded by glob
    assert validator_files

    for path in validator_files:
        rendered = _render(path)
        assert "<!-- ERROR: Include not found:" not in rendered
        assert "<!-- ERROR: Circular include detected:" not in rendered
