import io
import json
import shutil
import sys
import subprocess
from pathlib import Path

import pytest

# Keep the repository free of Python bytecode and __pycache__ artifacts during tests.
sys.dont_write_bytecode = True


# Ensure standard seek constants exist on the io module for tarfile compatibility
if not hasattr(io, "SEEK_SET"):
    io.SEEK_SET = 0  # type: ignore[attr-defined]
if not hasattr(io, "SEEK_CUR"):
    io.SEEK_CUR = 1  # type: ignore[attr-defined]
if not hasattr(io, "SEEK_END"):
    io.SEEK_END = 2  # type: ignore[attr-defined]

# Some Python runtimes (notably system-provided 3.9 builds) may lack the
# `io.open_code` helper used by runpy/importlib in newer stdlib versions.
# Provide a minimal, backwards-compatible shim so tests exercising
# `runpy.run_path` continue to work without depending on the stdlib patch level.
if not hasattr(io, "open_code"):
    def _open_code(path, *args, **kwargs):  # type: ignore[override]
        # Default to text mode; callers that care about binary/text can pass
        # an explicit mode via *args or **kwargs.
        if "mode" not in kwargs and not args:
            kwargs["mode"] = "r"
        return open(path, *args, **kwargs)

    io.open_code = _open_code  # type: ignore[attr-defined]


# Make Edison core lib importable as `lib.*` from the tests tree

from edison.core.utils.paths.resolver import PathResolver
from edison.core.utils.subprocess import run_with_timeout

# Repository root (resolved via PathResolver for relocatability)
REPO_ROOT = PathResolver.resolve_project_root()


def _reset_all_global_caches() -> None:
    """Reset ALL global caches in Edison modules to ensure test isolation."""
    # Path resolver cache
    try:
        import edison.core.paths.resolver as paths  # type: ignore
        paths._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]
    except Exception:
        pass

    # Task paths caches - CRITICAL for test isolation
    try:
        import edison.core.task.paths as task_paths  # type: ignore
        task_paths._ROOT_CACHE = None  # type: ignore[attr-defined]
        task_paths._SESSION_CONFIG_CACHE = None  # type: ignore[attr-defined]
        task_paths._TASK_CONFIG_CACHE = None  # type: ignore[attr-defined]
        task_paths._TASK_ROOT_CACHE = None  # type: ignore[attr-defined]
        task_paths._QA_ROOT_CACHE = None  # type: ignore[attr-defined]
        task_paths._SESSIONS_ROOT_CACHE = None  # type: ignore[attr-defined]
        task_paths._TASK_DIRS_CACHE = None  # type: ignore[attr-defined]
        task_paths._QA_DIRS_CACHE = None  # type: ignore[attr-defined]
        task_paths._SESSION_DIRS_CACHE = None  # type: ignore[attr-defined]
        task_paths._PREFIX_CACHE = None  # type: ignore[attr-defined]
    except Exception:
        pass

    # State machine caches AND SessionConfig which loads at module import
    try:
        import edison.core.session.state as session_state  # type: ignore
        session_state._STATE_MACHINE = None  # type: ignore[attr-defined]
        # Critical: SessionConfig is created at module load, must be reset
        if hasattr(session_state, '_CONFIG'):
            session_state._CONFIG = None  # type: ignore[attr-defined]
    except Exception:
        pass

    # Clear ALL config caches (central cache.py)
    try:
        from edison.core.config.cache import clear_all_caches
        clear_all_caches()
    except Exception:
        pass

    # Session config cache (centralized in _config.py)
    try:
        from edison.core.session._config import reset_config_cache
        reset_config_cache()
    except Exception:
        pass
    
    # Session store cache
    try:
        from edison.core.session.store import reset_session_store_cache
        reset_session_store_cache()
    except Exception:
        pass

    try:
        import edison.core.task.state as task_state  # type: ignore
        if hasattr(task_state, '_STATE_MACHINE'):
            task_state._STATE_MACHINE = None  # type: ignore[attr-defined]
    except Exception:
        pass

    # Composition module caches - CRITICAL for test isolation
    composition_modules = [
        "edison.core.composition.includes",
        "edison.core.composition.commands",
        "edison.core.composition.composers",
        "edison.core.composition.settings",
        "edison.core.composition.hooks",
    ]
    for mod_name in composition_modules:
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            if hasattr(mod, '_REPO_ROOT_OVERRIDE'):
                mod._REPO_ROOT_OVERRIDE = None  # type: ignore[attr-defined]
        except Exception:
            pass

    # ConfigManager cache
    try:
        import edison.core.config as config_mod  # type: ignore
        if hasattr(config_mod, '_CONFIG_CACHE'):
            config_mod._CONFIG_CACHE = {}  # type: ignore[attr-defined]
    except Exception:
        pass

    try:
        from edison.core.utils import project_config  # type: ignore

        project_config.reset_project_config_cache()
    except Exception:
        pass


@pytest.fixture(autouse=True)
def _reset_global_project_root_cache() -> None:
    """Ensure all global caches are fresh for each test."""
    _reset_all_global_caches()
    yield
    _reset_all_global_caches()


@pytest.fixture
def isolated_project_env(tmp_path, monkeypatch):
    """
    Isolated project environment for tests.

    CRITICAL: All tests MUST use this fixture to avoid
    creating .edison/.project during tests.
    """
    # Set environment variable and change to tmp directory
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)

    # Ensure PathResolver uses this isolated root for the duration of the test
    try:
        import edison.core.paths.resolver as paths  # type: ignore
        paths._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]
    except Exception:
        pass

    # Set composition module repo root overrides to use isolated environment
    composition_modules = [
        "edison.core.composition.includes",
        "edison.core.composition.commands",
        "edison.core.composition.composers",
        "edison.core.composition.settings",
        "edison.core.composition.hooks",
    ]
    for mod_name in composition_modules:
        try:
            import importlib
            mod = importlib.import_module(mod_name)
            if hasattr(mod, '_REPO_ROOT_OVERRIDE'):
                mod._REPO_ROOT_OVERRIDE = tmp_path  # type: ignore[attr-defined]
        except Exception:
            pass

    # Initialize a real git repository so path resolution can rely on
    # `git rev-parse --show-toplevel` instead of synthetic .git markers.
    run_with_timeout(
        ["git", "init"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Copy Edison core config files (state-machine.yaml, etc.) for state machine tests
    # In standalone Edison package, config files are bundled in src/edison/data/config/
    edison_bundled_config = Path(__file__).parent.parent / "src" / "edison" / "data" / "config"
    edison_legacy_config = REPO_ROOT / ".edison" / "core" / "config"

    edison_core_config_src = edison_bundled_config if edison_bundled_config.exists() else edison_legacy_config
    edison_core_config_dst = tmp_path / ".edison" / "core" / "config"

    if edison_core_config_src.exists():
        edison_core_config_dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(edison_core_config_src, edison_core_config_dst, dirs_exist_ok=True)

    # Ensure .edison/core/rules and .edison/core/guidelines directories exist for composition tests
    (tmp_path / ".edison" / "core" / "rules").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".edison" / "core" / "guidelines").mkdir(parents=True, exist_ok=True)

    # Create necessary project structure mirroring Edison conventions
    project_root = tmp_path / ".project"
    # We map the .agents directory to .edison for tests to verify migration
    agents_root = tmp_path / ".edison"

    # Core .project layout (tasks, QA, sessions)
    for rel in [
        "tasks/todo",
        "tasks/wip",
        "tasks/done",
        "tasks/validated",
        "tasks/blocked",
        "qa/waiting",
        "qa/todo",
        "qa/wip",
        "qa/done",
        "qa/validated",
        "qa/validation-evidence",
        "sessions/wip",
        "sessions/done",
        "sessions/validated",
    ]:
        (project_root / rel).mkdir(parents=True, exist_ok=True)

    # Core .agents layout (sessions, scripts, validators, config overlays)
    for rel in [
        "sessions",
        "scripts",
        "scripts/lib",
        "validators",
        "config",
    ]:
        (agents_root / rel).mkdir(parents=True, exist_ok=True)

    # Copy task and QA templates from the real repo when available; fall back to
    # minimal templates so tests have a valid structure even in stripped trees.
    task_tpl_src = REPO_ROOT / ".project" / "tasks" / "TEMPLATE.md"
    task_tpl_dst = project_root / "tasks" / "TEMPLATE.md"
    task_tpl_dst.parent.mkdir(parents=True, exist_ok=True)
    if task_tpl_src.exists():
        task_tpl_dst.write_text(task_tpl_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        task_tpl_dst.write_text(
            "# Task Template\n\n"
            "## Metadata\n"
            "- **Task ID:** example-id\n"
            "- **Status:** todo\n",
            encoding="utf-8",
        )

    qa_tpl_src = REPO_ROOT / ".project" / "qa" / "TEMPLATE.md"
    qa_tpl_dst = project_root / "qa" / "TEMPLATE.md"
    qa_tpl_dst.parent.mkdir(parents=True, exist_ok=True)
    if qa_tpl_src.exists():
        qa_tpl_dst.write_text(qa_tpl_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        qa_tpl_dst.write_text(
            "# QA Template\n\n"
            "## Metadata\n"
            "- **Validator Owner:** _unassigned_\n"
            "- **Status:** waiting\n",
            encoding="utf-8",
        )

    # Session template and workflow spec (minimal but valid for tests)
    # Use bundled template from edison.data
    from edison.data import get_data_path
    session_tpl_src = get_data_path("templates", "session.template.json")
    session_tpl_dst = agents_root / "sessions" / "TEMPLATE.json"
    session_tpl_dst.parent.mkdir(parents=True, exist_ok=True)
    if session_tpl_src.exists():
        session_tpl_dst.write_text(session_tpl_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        session_tpl_dst.write_text(
            json.dumps(
                {
                    "meta": {
                        "sessionId": "_placeholder_",
                        "owner": "_placeholder_",
                        "mode": "start",
                        "status": "wip",
                        "createdAt": "_placeholder_",
                        "lastActive": "_placeholder_",
                    },
                    "state": "active",
                    "tasks": {},
                    "qa": {},
                    "git": {
                        "worktreePath": None,
                        "branchName": None,
                        "baseBranch": None,
                    },
                    "activityLog": [
                        {"timestamp": "_placeholder_", "message": "Session created"}
                    ],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    # Session workflow: prefer project overlay, fall back to core template.
    workflow_src_candidates = [
        REPO_ROOT / ".agents" / "session-workflow.json",
        REPO_ROOT / ".edison" / "core" / "templates" / "session-workflow.json",
    ]
    workflow_dst = agents_root / "session-workflow.json"
    for candidate in workflow_src_candidates:
        if candidate.exists():
            workflow_dst.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
            break
    else:
        workflow_dst.write_text(
            json.dumps(
                {
                    "session": {
                        "states": ["active", "closing", "validated"],
                        "directories": {
                            "active": ".project/sessions/wip",
                            "closing": ".project/sessions/done",
                            "validated": ".project/sessions/validated",
                        },
                        "transitions": {},
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    # Mirror Context7 validator config from the real repo when present so tests
    # relying on minimal postTrainingPackages metadata behave consistently.
    validators_src = REPO_ROOT / ".agents" / "validators" / "config.json"
    if validators_src.exists():
        validators_dst_dir = agents_root / "validators"
        validators_dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(validators_src, validators_dst_dir / "config.json")

    # Copy modular .agents/config overlays (canonical YAML configuration)
    config_src_dir = REPO_ROOT / ".agents" / "config"
    if config_src_dir.exists():
        shutil.copytree(config_src_dir, agents_root / "config", dirs_exist_ok=True)

    # Create AGENTS.md for tests that need it (e.g., Zen CLI prompt verification)
    agents_md_src = REPO_ROOT / "AGENTS.md"
    agents_md_dst = tmp_path / "AGENTS.md"
    if agents_md_src.exists():
        agents_md_dst.write_text(agents_md_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        # Minimal AGENTS.md for standalone Edison package
        agents_md_dst.write_text(
            "# Edison Framework\n\n"
            "This is a test project using Edison Framework.\n\n"
            "## Project Overview\n"
            "Test project for Edison Framework unit tests.\n",
            encoding="utf-8",
        )

    # Provide a project-local tasks/ready wrapper so tests that invoke the CLI
    # via AGENTS_PROJECT_ROOT exercise the same implementation as the repo-level
    # edison tasks ready shim.
    ready_wrapper_src = REPO_ROOT / ".agents" / "scripts" / "tasks" / "ready"
    ready_wrapper_dst = agents_root / "scripts" / "tasks" / "ready"
    ready_wrapper_dst.parent.mkdir(parents=True, exist_ok=True)
    if ready_wrapper_src.exists():
        shutil.copyfile(ready_wrapper_src, ready_wrapper_dst)
    else:
        # Fallback: lightweight wrapper that delegates to core tasks/ready script.
        core_ready_path = (REPO_ROOT / ".edison" / "core" / "scripts" / "tasks" / "ready")
        core_ready = (
            "from __future__ import annotations\n"
            "from pathlib import Path\n"
            "import runpy\n\n"
            f"CORE_READY = Path({repr(str(core_ready_path))})\n"
            "globals().update(runpy.run_path(str(CORE_READY)))\n"
        )
        ready_wrapper_dst.write_text(core_ready, encoding="utf-8")

    yield tmp_path

    # Reset cache so other tests do not accidentally reuse this root
    try:
        import edison.core.paths.resolver as paths  # type: ignore

        paths._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]
    except Exception:
        pass

    # Cleanup is automatic (tmp_path)
