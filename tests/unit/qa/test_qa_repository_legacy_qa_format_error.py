from __future__ import annotations

from pathlib import Path

import pytest

from edison.core.entity import PersistenceError
from edison.core.qa.workflow.repository import QARepository


def test_qa_repository_raises_on_legacy_html_comment_qa(isolated_project_env: Path) -> None:
    qa_id = "101.1-wave1-fix-dashboard-type-errors-qa"
    qa_path = isolated_project_env / ".project" / "qa" / "waiting" / f"{qa_id}.md"
    qa_path.parent.mkdir(parents=True, exist_ok=True)
    qa_path.write_text(
        "\n".join(
            [
                "<!-- Task: 101.1-wave1-fix-dashboard-type-errors -->",
                "<!-- Status: waiting -->",
                "<!-- Round: 1 -->",
                "",
                f"# {qa_id}",
                "",
                "Legacy QA body",
                "",
            ]
        ),
        encoding="utf-8",
    )

    repo = QARepository(project_root=isolated_project_env)
    with pytest.raises(PersistenceError) as exc:
        repo.get(qa_id)

    msg = str(exc.value)
    assert "YAML frontmatter" in msg or "migrate" in msg




