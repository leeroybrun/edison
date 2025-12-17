import io
import json
import os
import shutil
import sys
import subprocess
from pathlib import Path

import pytest
import yaml

# Keep the repository free of Python bytecode and __pycache__ artifacts during tests.
sys.dont_write_bytecode = True

TESTS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TESTS_ROOT.parent
SRC_ROOT = REPO_ROOT / "src"

# Make src/ importable as 'edison'
for p in (SRC_ROOT, TESTS_ROOT):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))


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


from edison.core.utils.paths.resolver import PathResolver
from edison.core.utils.subprocess import run_with_timeout
from config import load_states as load_test_states
from helpers.cache_utils import reset_edison_caches


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_teardown(item, nextitem):  # type: ignore[no-untyped-def]
    """Guard pytest's own PYTEST_CURRENT_TEST cleanup.

    Some code paths in this repo mutate os.environ directly; when that happens,
    pytest's internal teardown (which unsets PYTEST_CURRENT_TEST) can crash with
    KeyError if the variable was removed mid-test.
    """
    os.environ.setdefault("PYTEST_CURRENT_TEST", str(getattr(item, "nodeid", "")))


# Some unit tests still mutate os.environ directly (without monkeypatch). To keep
# PathResolver + config loading deterministic, restore only the Edison-related
# env vars that are known to leak, without touching pytest's own env vars such
# as PYTEST_CURRENT_TEST.
_LEAK_PRONE_ENV_KEYS = [
    "AGENTS_PROJECT_ROOT",
    "PROJECT_NAME",
    "PROJECT_TERMS",
    "AGENTS_OWNER",
    "AGENTS_SESSION",
    "TASK_ID",
    # Critical: overrides the location of `.edison/` itself. If this leaks, config loads
    # will silently ignore `.edison/config/*.yml` written by many tests.
    "EDISON_paths__project_config_dir",
]

# Baseline values for Edison leak-prone env vars at pytest session start.
# We restore only these keys to avoid touching pytest's own env vars like PYTEST_CURRENT_TEST.
_ENV_BASELINE = {k: os.environ.get(k) for k in _LEAK_PRONE_ENV_KEYS}
# Tests must be deterministic regardless of developer environment. This env var
# changes the *name* of the project config directory (e.g. ".edison"), and if it
# is set in a developer shell it will silently break many tests that create
# `.edison/config/*.yaml`. Fail-closed by always clearing it for every test.
_ENV_BASELINE["EDISON_paths__project_config_dir"] = None


@pytest.fixture(autouse=True)
def _reset_global_project_root_cache() -> None:
    """Ensure all global caches are fresh for each test."""
    reset_edison_caches()
    yield
    reset_edison_caches()
    for k, v in _ENV_BASELINE.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture
def isolated_project_env(tmp_path, monkeypatch):
    """
    Isolated project environment for tests.

    CRITICAL: All tests MUST use this fixture to avoid
    creating .edison/.project during tests.
    """
    # Set environment variable and change to tmp directory
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))
    # Ensure config resolves `.edison/` inside this isolated repo.
    # Some developer environments set this override; tests must be deterministic.
    monkeypatch.delenv("EDISON_paths__project_config_dir", raising=False)
    monkeypatch.chdir(tmp_path)

    # Ensure PathResolver uses this isolated root for the duration of the test
    try:
        import edison.core.utils.paths.resolver as paths  # type: ignore
        paths._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]
    except Exception:
        pass

    # Set composition module repo root overrides to use isolated environment
    composition_modules = [
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
        ["git", "init", "-b", "main"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Configure git user for tests (required for commits)
    run_with_timeout(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    run_with_timeout(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Create initial commit so worktrees can be created
    # (worktrees require at least one commit in the repository)
    readme_file = tmp_path / "README.md"
    readme_file.write_text("# Test Project\n", encoding="utf-8")
    run_with_timeout(
        ["git", "add", "README.md"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    run_with_timeout(
        ["git", "commit", "-m", "Initial commit"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Create .edison/config directory for project-level config overrides
    # NOTE: Core config is ALWAYS from bundled edison.data package
    # NO .edison/core/ - that is legacy
    project_config_dir = tmp_path / ".edison" / "config"
    project_config_dir.mkdir(parents=True, exist_ok=True)
    
    # Create project-level directories for overrides (optional)
    # Project can add custom guidelines, validators, rules at:
    # .edison/guidelines/, .edison/validators/, .edison/rules/
    (tmp_path / ".edison" / "guidelines").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".edison" / "validators").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".edison" / "rules").mkdir(parents=True, exist_ok=True)

    # Create necessary project structure mirroring Edison conventions
    project_root = tmp_path / ".project"
    # We map the .agents directory to .edison for tests to verify migration
    agents_root = tmp_path / ".edison"

    # Core .project layout (tasks, QA, sessions) - loaded from canonical config
    states_config = load_test_states()

    # Create task directories
    task_unique_dirs = states_config.get("task", {}).get("unique_dirs", [])
    for dir_name in task_unique_dirs:
        (project_root / "tasks" / dir_name).mkdir(parents=True, exist_ok=True)

    # Create QA directories
    qa_unique_dirs = states_config.get("qa", {}).get("unique_dirs", [])
    for dir_name in qa_unique_dirs:
        (project_root / "qa" / dir_name).mkdir(parents=True, exist_ok=True)

    # Create additional QA paths
    qa_additional = states_config.get("additional_paths", {}).get("qa", [])
    for rel_path in qa_additional:
        (project_root / rel_path).mkdir(parents=True, exist_ok=True)

    # Create session directories
    session_unique_dirs = states_config.get("session", {}).get("unique_dirs", [])
    for dir_name in session_unique_dirs:
        (project_root / "sessions" / dir_name).mkdir(parents=True, exist_ok=True)

    # Core .agents layout (sessions, validators, config overlays)
    for rel in [
        "sessions",
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
        # Load default task state from config (NO hardcoded values)
        from tests.config import get_default_value
        default_task_state = get_default_value("task", "state")

        task_tpl_dst.write_text(
            "# Task Template\n\n"
            "## Metadata\n"
            "- **Task ID:** example-id\n"
            f"- **Status:** {default_task_state}\n",
            encoding="utf-8",
        )

    qa_tpl_src = REPO_ROOT / ".project" / "qa" / "TEMPLATE.md"
    qa_tpl_dst = project_root / "qa" / "TEMPLATE.md"
    qa_tpl_dst.parent.mkdir(parents=True, exist_ok=True)
    if qa_tpl_src.exists():
        qa_tpl_dst.write_text(qa_tpl_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        # Load default QA state from config (NO hardcoded values)
        from tests.config import get_default_value
        default_qa_state = get_default_value("qa", "state")

        qa_tpl_dst.write_text(
            "# QA Template\n\n"
            "## Metadata\n"
            "- **Validator Owner:** _unassigned_\n"
            f"- **Status:** {default_qa_state}\n",
            encoding="utf-8",
        )

    # Session template and workflow spec (minimal but valid for tests)
    # Use bundled template from edison.data
    from edison.data import get_data_path
    from tests.config import get_default_value

    session_tpl_src = get_data_path("templates", "session.template.json")
    session_tpl_dst = agents_root / "sessions" / "TEMPLATE.json"
    session_tpl_dst.parent.mkdir(parents=True, exist_ok=True)
    if session_tpl_src.exists():
        session_tpl_dst.write_text(session_tpl_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        # Load default session state from config (NO hardcoded values)
        default_session_state = get_default_value("session", "state")

        session_tpl_dst.write_text(
            json.dumps(
                {
                    "meta": {
                        "sessionId": "_placeholder_",
                        "owner": "_placeholder_",
                        "mode": "start",
                        "status": default_session_state,
                        "createdAt": "_placeholder_",
                        "lastActive": "_placeholder_",
                    },
                    "state": default_session_state,
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

    # NOTE: Session workflow is now defined in bundled state-machine.yaml
    # and accessed via WorkflowConfig domain config. No need to create
    # legacy session-workflow.json files.

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
        # Fallback: minimal wrapper - tasks/ready functionality is in edison CLI
        ready_wrapper_dst.write_text(
            "#!/usr/bin/env python3\n"
            "# Minimal tasks/ready wrapper for tests\n"
            "# Real implementation is in edison.cli.task.ready\n"
            "from edison.cli.task.ready import main\n"
            "import sys\n"
            "sys.exit(main())\n",
            encoding="utf-8",
        )

    yield tmp_path

    # Reset cache so other tests do not accidentally reuse this root
    try:
        import edison.core.utils.paths.resolver as paths  # type: ignore

        paths._PROJECT_ROOT_CACHE = None  # type: ignore[attr-defined]
    except Exception:
        pass

    # Cleanup is automatic (tmp_path)


# -----------------------------------------------------------------------------
# Consolidated fixtures (moved from tests/task/, tests/unit/qa/, tests/e2e/)
# -----------------------------------------------------------------------------

@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Get repository root path for tests.

    Scope: session (immutable value, no per-test isolation needed)
    """
    return REPO_ROOT


@pytest.fixture
def project_dir(tmp_path: Path, repo_root: Path):
    """Create isolated .project directory for testing.

    This fixture uses TestProjectDir helper for managing test project structure.
    """
    from helpers.env import TestProjectDir
    return TestProjectDir(tmp_path, repo_root)


@pytest.fixture
def git_repo(tmp_path: Path):
    """Create isolated git repository for testing.

    Uses TestGitRepo helper for worktree-capable git operations.
    """
    from helpers.env import TestGitRepo
    return TestGitRepo(tmp_path)


@pytest.fixture
def combined_env(tmp_path: Path, repo_root: Path):
    """Combined fixture with both TestProjectDir and TestGitRepo.

    Useful for tests that need both project structure and git operations.
    """
    from helpers.env import TestProjectDir, TestGitRepo

    git_root = tmp_path / "git"
    proj_root = tmp_path / "proj"
    git_root.mkdir(parents=True, exist_ok=True)
    proj_root.mkdir(parents=True, exist_ok=True)

    git_repo = TestGitRepo(git_root)
    project_dir = TestProjectDir(proj_root, repo_root)
    return project_dir, git_repo


@pytest.fixture
def project_env(isolated_project_env):
    """Alias for isolated_project_env for backward compatibility."""
    return isolated_project_env


@pytest.fixture
def project_root(isolated_project_env):
    """Alias for isolated_project_env for tests expecting project_root fixture."""
    return isolated_project_env
