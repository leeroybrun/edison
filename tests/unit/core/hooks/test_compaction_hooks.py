from __future__ import annotations

import os
from argparse import Namespace
from pathlib import Path

import yaml

from edison.core.hooks.compaction import CompactionHook
from edison.cli.hooks import compaction as compaction_cli


def _write_compaction_config(tmp_path: Path) -> Path:
    data = {
        "compaction": {
            "hooks": {
                "enabled": True,
                "defaultRole": "agents",
                "defaultSource": "compaction-test",
                "reminder": {
                    "messageTemplate": "⚠️ Context compacted. Re-read your constitution at: constitutions/{ROLE}.md",
                    "notify": True,
                },
                "log": {
                    "enabled": True,
                    "path": "{PROJECT_CONFIG_DIR}/logs/compaction.log",
                    "entryTemplate": "{timestamp} role={role} source={source} message={message}",
                },
            }
        }
    }

    config_dir = tmp_path / ".edison" / "core" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    path = config_dir / "compaction.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    return path


def test_compaction_hook_module_exists(tmp_path: Path) -> None:
    _write_compaction_config(tmp_path)

    hook = CompactionHook(repo_root=tmp_path)

    assert hook is not None
    assert hook.config.get("enabled") is True


def test_trigger_emits_reminder_and_logs(tmp_path: Path, capsys) -> None:
    _write_compaction_config(tmp_path)

    hook = CompactionHook(repo_root=tmp_path)
    message = hook.trigger(role="validators", source="unit-test")

    captured = capsys.readouterr()

    assert "validators" in message
    assert "⚠️ Context compacted" in captured.out

    log_path = tmp_path / ".edison" / "logs" / "compaction.log"
    assert log_path.exists()
    log_content = log_path.read_text(encoding="utf-8")
    assert "validators" in log_content
    assert "unit-test" in log_content


def test_cli_trigger_respects_role(tmp_path: Path, capsys) -> None:
    _write_compaction_config(tmp_path)

    os.environ["AGENTS_PROJECT_ROOT"] = str(tmp_path)
    args = Namespace(role="orchestrator", repo_root=str(tmp_path))

    exit_code = compaction_cli.main(args)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "orchestrator" in captured.out

    del os.environ["AGENTS_PROJECT_ROOT"]
