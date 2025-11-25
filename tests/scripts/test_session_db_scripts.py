from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


EDISON_ROOT = Path(__file__).resolve().parents[2]


def _write_db_config(repo_root: Path, project: str = "demo") -> None:
    cfg_dir = repo_root / ".agents" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_dir.joinpath("database.yml").write_text(
        textwrap.dedent(
            f"""
            project:
              name: {project}
            database:
              enabled: true
            worktrees:
              enableDatabaseIsolation: true
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )


def _fake_psql(tmp_path: Path) -> tuple[Path, Path]:
    """Create a stub psql executable that logs argv to PSQL_LOG."""
    log_path = tmp_path / "psql-log.json"
    script = tmp_path / "psql"
    script.write_text(
        textwrap.dedent(
            """
            #!/usr/bin/env python3
            import json
            import os
            import sys
            from pathlib import Path

            log = Path(os.environ["PSQL_LOG"])
            entries = json.loads(log.read_text()) if log.exists() else []
            entries.append(sys.argv[1:])
            log.write_text(json.dumps(entries))
            print("psql stub")
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script, log_path


@pytest.fixture()
def stubbed_psql(tmp_path, monkeypatch):
    stub, log_path = _fake_psql(tmp_path)
    monkeypatch.setenv("PSQL_LOG", str(log_path))
    monkeypatch.setenv("PATH", f"{stub.parent}:{os.environ.get('PATH', '')}")
    return log_path


def test_create_session_db_invokes_psql_and_prints_name(isolated_project_env, stubbed_psql, monkeypatch):
    _write_db_config(isolated_project_env, project="sample")
    monkeypatch.setenv("DATABASE_URL", "postgres://example")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(isolated_project_env))

    result = subprocess.run(
        [sys.executable, "-m", "edison.cli.session.db.create", "sess-123"],
        capture_output=True,
        text=True,
        cwd=EDISON_ROOT,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "sample_sess_123"

    calls = json.loads(Path(stubbed_psql).read_text())
    assert calls[0][0] == "postgres://example"
    assert any("CREATE DATABASE \"sample_sess_123\"" in arg for arg in calls[0])


def test_drop_session_db_force_terminates_connections(isolated_project_env, stubbed_psql, monkeypatch):
    _write_db_config(isolated_project_env, project="demo")
    monkeypatch.setenv("DATABASE_URL", "postgres://example")
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(isolated_project_env))

    result = subprocess.run(
        [sys.executable, "-m", "edison.cli.session.db.drop", "sess-999", "--force"],
        capture_output=True,
        text=True,
        cwd=EDISON_ROOT,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == "demo_sess_999"

    calls = json.loads(Path(stubbed_psql).read_text())
    # --force should invoke terminate then drop
    assert len(calls) == 2
    terminate_sql = " ".join(calls[0])
    drop_sql = " ".join(calls[1])
    assert "pg_terminate_backend" in terminate_sql
    assert "DROP DATABASE IF EXISTS \"demo_sess_999\"" in drop_sql
