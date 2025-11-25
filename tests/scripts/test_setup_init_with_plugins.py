from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import yaml
import pytest

# Skip all tests in this file - setup/init CLI functionality has been moved to core library
pytestmark = pytest.mark.skip(reason="Setup init CLI has been moved to core library (edison.core.setup). No CLI command yet.")

from .test_setup_init import (
    _copy_core,
    _init_repo,
    _load_config,
    _prepare_env,
    _run_setup,
    _write_minimal_compose_config,
)


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _seed_pack_with_setup(root: Path, name: str, setup_data: dict) -> None:
    pack_dir = root / ".edison" / "packs" / name
    (pack_dir / "config").mkdir(parents=True, exist_ok=True)
    (pack_dir / "config.yml").write_text(f"name: {name}\n", encoding="utf-8")
    _write_yaml(pack_dir / "config" / "setup.yml", setup_data)


def test_setup_init_runs_pack_questions_and_writes_config(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _copy_core(tmp_path)
    _write_minimal_compose_config(tmp_path)

    ts_setup = {
        "setup": {
            "questions": [
                {
                    "id": "typescript_strict",
                    "prompt": "Enable TypeScript strict mode?",
                    "type": "boolean",
                    "default": True,
                    "mode": "basic",
                    "depends_on": [{"pack": "typescript", "enabled": True}],
                },
                {
                    "id": "typescript_target",
                    "prompt": "TypeScript compilation target",
                    "type": "choice",
                    "source": "static",
                    "options": ["ES2020", "ES2021", "ES2022", "ESNext"],
                    "default": "ES2022",
                    "mode": "advanced",
                    "depends_on": [{"pack": "typescript", "enabled": True}],
                },
                {
                    "id": "typescript_module",
                    "prompt": "Module system",
                    "type": "choice",
                    "source": "static",
                    "options": ["commonjs", "es2020", "esnext", "node16"],
                    "default": "esnext",
                    "mode": "advanced",
                },
            ],
            "config_template": {
                "typescript": {
                    "strict": "{{ typescript_strict }}",
                    "target": "{{ typescript_target }}",
                    "module": "{{ typescript_module }}",
                }
            },
        }
    }

    react_setup = {
        "setup": {
            "questions": [
                {
                    "id": "react_version",
                    "prompt": "React version",
                    "type": "choice",
                    "source": "static",
                    "options": ["18", "19-rc"],
                    "default": "18",
                    "mode": "advanced",
                },
                {
                    "id": "react_strict_mode",
                    "prompt": "Enable React StrictMode?",
                    "type": "boolean",
                    "default": True,
                    "mode": "basic",
                },
            ],
            "config_template": {
                "react": {
                    "version": "{{ react_version }}",
                    "strict_mode": "{{ react_strict_mode }}",
                }
            },
        }
    }

    _seed_pack_with_setup(tmp_path, "typescript", ts_setup)
    _seed_pack_with_setup(tmp_path, "react", react_setup)

    env = _prepare_env(tmp_path)

    answers = "".join(
        [
            "Plugin Project\n",  # project_name
            "React App\n",  # project_type
            "typescript,react\n",  # packs
            "y\n",  # typescript_strict
            "ES2021\n",  # typescript_target
            "node16\n",  # typescript_module
            "19-rc\n",  # react_version
            "y\n",  # react_strict_mode
            "claude\n",  # orchestrators
            "PostgreSQL\n",  # database
            "auth0\n",  # auth_provider
            "y\n",  # enable_worktrees
            "pnpm lint\n",  # ci_lint
            "pnpm test\n",  # ci_test
            "pnpm build\n",  # ci_build
            "pnpm type-check\n",  # ci_type_check
            ".agents\n",  # project_config_dir
            ".project\n",  # project_management_dir
            "\n",  # task_states (accept default)
            "\n",  # session_states (accept default)
            "\n",  # task_states_config
            "\n",  # session_states_config
            "\n",  # validators
            "\n",  # agents
            "strict\n",  # tdd_enforcement
            "88\n",  # coverage_threshold
        ]
    )

    proc = _run_setup(["--advanced"], env, tmp_path, input_data=answers)
    assert proc.returncode == 0, proc.stderr

    cfg = _load_config(tmp_path)
    pack_cfg = cfg.get("pack_config") or {}

    assert pack_cfg["typescript"]["strict"] is True
    assert pack_cfg["typescript"]["target"] == "ES2021"
    assert pack_cfg["typescript"]["module"] == "node16"
    assert pack_cfg["react"]["version"] == "19-rc"
    assert pack_cfg["react"]["strict_mode"] is True


def test_setup_init_skips_packs_without_setup_files(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    _copy_core(tmp_path)
    _write_minimal_compose_config(tmp_path)

    # Pack present for discovery but without config/setup.yml
    empty_pack = tmp_path / ".edison" / "packs" / "empty"
    (empty_pack / "config").mkdir(parents=True, exist_ok=True)
    (empty_pack / "config.yml").write_text("name: empty\n", encoding="utf-8")

    env = _prepare_env(tmp_path)

    answers = "".join(
        [
            "NoPack\n",  # project_name
            "Other\n",  # project_type
            "empty\n",  # packs selection
            "claude\n",  # orchestrators
            "None\n",  # database
            "None\n",  # auth_provider
            "n\n",  # enable_worktrees
            "npm run lint\n",
            "npm test\n",
            "npm run build\n",
            "npm run type-check\n",
        ]
    )

    proc = _run_setup([], env, tmp_path, input_data=answers)
    assert proc.returncode == 0, proc.stderr

    cfg = _load_config(tmp_path)
    assert "pack_config" not in cfg or cfg.get("pack_config") == {}
