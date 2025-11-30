from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from tests.helpers.io_utils import write_minimal_compose_config
from tests.helpers.paths import get_repo_root
from tests.helpers.timeouts import SUBPROCESS_TIMEOUT


EDISON_ROOT = get_repo_root()
REPO_ROOT = get_repo_root()

# Skip all tests in this file - setup/init CLI functionality has been moved to core library
# and is now accessed via edison.core.setup module. CLI command for init doesn't exist yet.
pytestmark = pytest.mark.skip(reason="Setup init CLI has been moved to core library (edison.core.setup). No CLI command yet.")


def _run_setup(args: list[str], env: dict[str, str], cwd: Path, input_data: str = "") -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(SCRIPTS_DIR / "setup" / "init.py"), *args]
    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        input=input_data,
        text=True,
        capture_output=True,
        timeout=SUBPROCESS_TIMEOUT,
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _copy_core(dst_root: Path) -> Path:
    """Copy Edison core into the isolated repo so compose/doctor can run."""

    src_core = REPO_ROOT / ".edison" / "core"
    dst_core = dst_root / ".edison" / "core"
    if dst_core.exists():
        return dst_core

    shutil.copytree(
        src_core,
        dst_core,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache", ".mypy_cache"),
    )
    return dst_core


def _seed_pack(root: Path, name: str) -> None:
    """Create a minimal pack with validator/agent configs for discovery."""

    pack_dir = root / ".edison" / "packs" / name
    (pack_dir / "config").mkdir(parents=True, exist_ok=True)
    (pack_dir / "config.yml").write_text("pack: true\n", encoding="utf-8")
    (pack_dir / "config" / "validators.yml").write_text(
        "validators:\n  - id: " + name + "-validator\n",
        encoding="utf-8",
    )
    (pack_dir / "config" / "agents.yml").write_text(
        "agents:\n  - id: " + name + "-agent\n",
        encoding="utf-8",
    )


def _load_config(root: Path, config_dir: str = ".agents") -> dict:
    cfg_path = root / config_dir / "config.yml"
    assert cfg_path.exists(), f"config.yml missing at {cfg_path}"
    return yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}


def _prepare_env(root: Path) -> dict[str, str]:
    env = os.environ.copy()
    env["AGENTS_PROJECT_ROOT"] = str(root)
    return env


def test_already_initialized_blocks_without_reconfigure(isolated_project_env: Path):
    env = _prepare_env(isolated_project_env)

    proc = _run_setup(["--yes"], env, isolated_project_env)

    assert proc.returncode != 0
    assert "already initialized" in (proc.stdout + proc.stderr).lower()


def test_reconfigure_allows_rerun_and_writes_defaults(tmp_path: Path):
    _init_repo(tmp_path)
    _copy_core(tmp_path)
    write_minimal_compose_config(tmp_path, include_hook_type=True)

    # Pretend project was initialized previously
    (tmp_path / ".agents").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".agents" / "config.yml").write_text("existing: true\n", encoding="utf-8")

    env = _prepare_env(tmp_path)

    proc = _run_setup(["--reconfigure", "--yes"], env, tmp_path)
    assert proc.returncode == 0, proc.stderr

    cfg = _load_config(tmp_path)
    assert cfg.get("project", {}).get("name") == tmp_path.name
    assert cfg.get("paths", {}).get("config_dir") == ".agents"
    assert cfg.get("paths", {}).get("management_dir") == ".project"


def test_basic_mode_non_interactive_defaults(tmp_path: Path):
    _init_repo(tmp_path)
    _copy_core(tmp_path)
    write_minimal_compose_config(tmp_path, include_hook_type=True)

    env = _prepare_env(tmp_path)

    proc = _run_setup(["--yes"], env, tmp_path)
    assert proc.returncode == 0, proc.stderr

    cfg = _load_config(tmp_path)
    assert cfg.get("project", {}).get("name") == tmp_path.name
    assert cfg.get("project", {}).get("type") == "Other"
    assert cfg.get("database") == "None"
    assert cfg.get("auth", {}).get("provider") == "None"
    assert cfg.get("orchestrators") == ["claude"]
    assert cfg.get("paths", {}).get("config_dir") == ".agents"
    assert cfg.get("paths", {}).get("management_dir") == ".project"
    assert (tmp_path / ".agents" / "guidelines").is_dir()
    assert (tmp_path / ".project").is_dir()


def test_advanced_mode_supports_custom_directories_and_dynamic_options(tmp_path: Path):
    _init_repo(tmp_path)
    _copy_core(tmp_path)
    write_minimal_compose_config(tmp_path, include_hook_type=True)
    _seed_pack(tmp_path, "demo-pack")

    env = _prepare_env(tmp_path)

    answers = "".join(
        [
            "Acme Advanced\n",           # project_name
            "Fastify API\n",             # project_type
            "demo-pack\n",               # packs
            "claude,codex\n",            # orchestrators
            "PostgreSQL\n",              # database
            "auth0\n",                   # auth_provider
            "y\n",                      # enable_worktrees
            "pnpm lint\n",               # ci_lint
            "pnpm test\n",               # ci_test
            "pnpm build\n",              # ci_build
            "pnpm type-check\n",         # ci_type_check
            ".custom-agents\n",          # project_config_dir
            ".mgmt\n",                  # project_management_dir
            "todo,wip,done\n",           # task_states
            "active,closing\n",          # session_states
            "security,demo-pack-validator\n",  # validators
            "demo-pack-agent\n",         # agents
            "strict\n",                  # tdd_enforcement
            "85\n",                      # coverage_threshold
        ]
    )

    proc = _run_setup(["--advanced"], env, tmp_path, input_data=answers)
    assert proc.returncode == 0, proc.stderr

    cfg = _load_config(tmp_path, ".custom-agents")

    assert cfg.get("paths", {}).get("config_dir") == ".custom-agents"
    assert cfg.get("paths", {}).get("management_dir") == ".mgmt"
    assert cfg.get("project", {}).get("name") == "Acme Advanced"
    assert cfg.get("project", {}).get("type") == "Fastify API"
    assert cfg.get("project", {}).get("packs") == ["demo-pack"]
    assert set(cfg.get("orchestrators", [])) == {"claude", "codex"}
    assert cfg.get("database") == "PostgreSQL"
    assert cfg.get("auth", {}).get("provider") == "auth0"
    assert cfg.get("worktrees", {}).get("enabled") is True
    assert cfg.get("workflow", {}).get("tasks", {}).get("states") == ["todo", "wip", "done"]
    assert cfg.get("workflow", {}).get("sessions", {}).get("states") == ["active", "closing"]
    assert "security" in cfg.get("validators", {}).get("enabled", [])
    assert "demo-pack-validator" in cfg.get("validators", {}).get("enabled", [])
    assert cfg.get("agents", {}).get("enabled") == ["demo-pack-agent"]
    assert cfg.get("tdd", {}).get("enforcement") == "strict"
    assert cfg.get("tdd", {}).get("coverage_threshold") == 85

    # Ensure directories were created
    assert (tmp_path / ".custom-agents" / "guidelines").is_dir()
    assert (tmp_path / ".mgmt").is_dir()


def test_advanced_mode_non_interactive_defaults(tmp_path: Path):
    _init_repo(tmp_path)
    _copy_core(tmp_path)
    write_minimal_compose_config(tmp_path, include_hook_type=True)

    env = _prepare_env(tmp_path)

    proc = _run_setup(["--advanced", "--yes"], env, tmp_path)
    assert proc.returncode == 0, proc.stderr

    cfg = _load_config(tmp_path)

    assert cfg.get("paths", {}).get("config_dir") == ".agents"
    assert cfg.get("paths", {}).get("management_dir") == ".project"
    assert cfg.get("workflow", {}).get("tasks", {}).get("states") == [
        "todo",
        "wip",
        "blocked",
        "done",
        "validated",
    ]
    assert cfg.get("workflow", {}).get("sessions", {}).get("states") == [
        "active",
        "closing",
        "recovery",
        "waiting",
        "wip",
    ]
    assert cfg.get("tdd", {}).get("enforcement") == "warn"
    assert cfg.get("tdd", {}).get("coverage_threshold") == 90


def test_already_initialized_custom_directory(tmp_path: Path):
    _init_repo(tmp_path)
    _copy_core(tmp_path)
    write_minimal_compose_config(tmp_path, include_hook_type=True)

    env = _prepare_env(tmp_path)

    # First run writes to a custom directory
    first_answers = "".join(
        [
            f"{tmp_path.name}\n",  # project_name
            "Other\n",
            "\n",  # packs
            "claude\n",
            "None\n",
            "None\n",
            "n\n",
            "npm run lint\n",
            "npm test\n",
            "npm run build\n",
            "npm run type-check\n",
            ".alt-agents\n",
            ".alt-project\n",
            "\n",  # task_states default
            "\n",  # session_states default
            "\n",  # validators default
            "\n",  # agents default
            "\n",  # tdd enforcement default
            "\n",  # coverage default
        ]
    )
    first = _run_setup(["--advanced"], env, tmp_path, input_data=first_answers)
    assert first.returncode == 0, first.stderr

    # Second run without --reconfigure should abort
    second = _run_setup(["--advanced"], env, tmp_path, input_data=first_answers)
    assert second.returncode != 0
    assert "already initialized" in (second.stdout + second.stderr).lower()

