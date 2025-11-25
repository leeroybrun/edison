"""Minimal test environment helpers for QA tests."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class TestProjectDir:
    def __init__(self, tmp_path: Path, repo_root: Path):
        self.tmp_path = tmp_path
        self.repo_root = repo_root
        self.project_root = tmp_path / ".project"
        self.agents_root = tmp_path / ".agents"
        self._setup_directories()
        self._setup_configs()

    def _setup_directories(self) -> None:
        for d in [
            self.project_root / "tasks" / "todo",
            self.project_root / "tasks" / "wip",
            self.project_root / "tasks" / "done",
            self.project_root / "tasks" / "validated",
            self.project_root / "qa" / "waiting",
            self.project_root / "qa" / "todo",
            self.project_root / "qa" / "wip",
            self.project_root / "qa" / "done",
            self.project_root / "qa" / "validation-evidence",
            self.project_root / "sessions" / "wip",
        ]:
            d.mkdir(parents=True, exist_ok=True)
        (self.agents_root / "scripts" / "lib").mkdir(parents=True, exist_ok=True)

    def _setup_configs(self) -> None:
        # Copy templates if present
        src_task_tpl = self.repo_root / ".project" / "tasks" / "TEMPLATE.md"
        if src_task_tpl.exists():
            (self.project_root / "tasks" / "TEMPLATE.md").write_text(src_task_tpl.read_text())
        src_qa_tpl = self.repo_root / ".project" / "qa" / "TEMPLATE.md"
        if src_qa_tpl.exists():
            (self.project_root / "qa" / "TEMPLATE.md").write_text(src_qa_tpl.read_text())

        # Copy lib used by CLIs when run with AGENTS_PROJECT_ROOT
        src_lib = self.repo_root / ".agents" / "scripts" / "lib"
        if src_lib.exists():
            for f in src_lib.glob("*.py"):
                (self.agents_root / "scripts" / "lib" / f.name).write_text(f.read_text())

    # === helpers ===
    def create_task(self, task_id: str, wave: str = "wave1", slug: str = "task", state: str = "todo") -> Path:
        path = self.project_root / "tasks" / state / f"{task_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        content = "\n".join([
            f"# Task {task_id}",
            "",
            "- **Owner:** _unassigned_",
            f"- **Wave:** {wave}",
            f"- **Status:** {state}",
            "",
        ]) + "\n"
        path.write_text(content)
        return path

    def create_session(self, session_id: str, state: str = "wip", **kwargs) -> Path:
        d = self.project_root / "sessions" / state
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{session_id}.json"
        now = datetime.utcnow().isoformat() + "Z"
        data: Dict[str, Any] = {
            "meta": {"sessionId": session_id, "createdAt": now, "lastActive": now},
            "tasks": {},
            "qa": {},
            "activityLog": [],
            **kwargs,
        }
        p.write_text(json.dumps(data, indent=2))
        return p

    # Optional helpers used in some tests
    def get_task_path(self, task_id: str) -> Optional[Path]:
        for state in ("todo", "wip", "done", "validated"):
            p = self.project_root / "tasks" / state / f"{task_id}.md"
            if p.exists():
                return p
        return None


class TestGitRepo:
    def __init__(self, tmp_path: Path):
        self.tmp_path = tmp_path
