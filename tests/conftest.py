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


@pytest.hookimpl(tryfirst=True)
def pytest_collection_modifyitems(config, items):  # type: ignore[no-untyped-def]
    """Auto-label tests so we can run fast vs slow suites reliably.

    Markers are declared in `pyproject.toml` (`--strict-markers` is enabled), so this
    hook only assigns them based on test location heuristics.
    """
    def _drop_marker(test_item, name: str) -> None:
        try:
            test_item.own_markers = [m for m in test_item.own_markers if m.name != name]
        except Exception:
            pass
        try:
            test_item.keywords.pop(name, None)
        except Exception:
            pass

    for item in items:
        nodeid = str(getattr(item, "nodeid", "")).replace("\\", "/")

        is_e2e = nodeid.startswith("e2e/") or "/e2e/" in nodeid
        is_integration = nodeid.startswith("integration/") or "/integration/" in nodeid
        is_slow = False

        if is_e2e:
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.requires_git)
            item.add_marker(pytest.mark.requires_subprocess)
            is_slow = True

        if is_integration:
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.requires_git)
            item.add_marker(pytest.mark.requires_subprocess)
            is_slow = True

        if "/worktree/" in nodeid:
            item.add_marker(pytest.mark.worktree)
            item.add_marker(pytest.mark.requires_git)
            item.add_marker(pytest.mark.requires_subprocess)

            # Worktree tests run git operations and are a major contributor to
            # runtime. Keep them out of the default "fast" suite.
            is_slow = True

        if "/unit/cli/" in nodeid:
            item.add_marker(pytest.mark.requires_subprocess)
            # CLI tests tend to invoke subprocesses and are a major contributor
            # to suite time. Keep them out of the default "fast" suite.
            is_slow = True

        if "/unit/cli/session/test_session_create_" in nodeid:
            is_slow = True

        if "/unit/cli/session/test_session_create_base_branch_override.py" in nodeid:
            is_slow = True

        if "/unit/core/git/" in nodeid or "/unit/git/" in nodeid:
            item.add_marker(pytest.mark.requires_git)

        if is_slow:
            item.add_marker(pytest.mark.slow)
            _drop_marker(item, "fast")
        elif not is_e2e and not is_integration:
            item.add_marker(pytest.mark.fast)


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
    # Critical: user-layer is enabled by default. Tests must never consult a real
    # developer home directory (~/.edison) which would make tests non-deterministic.
    "EDISON_paths__user_config_dir",
]

# Baseline values for Edison leak-prone env vars at pytest session start.
# We restore only these keys to avoid touching pytest's own env vars like PYTEST_CURRENT_TEST.
_ENV_BASELINE = {k: os.environ.get(k) for k in _LEAK_PRONE_ENV_KEYS}
# Tests must be deterministic regardless of developer environment. This env var
# changes the *name* of the project config directory (e.g. ".edison"), and if it
# is set in a developer shell it will silently break many tests that create
# `.edison/config/*.yaml`. Fail-closed by always clearing it for every test.
_ENV_BASELINE["EDISON_paths__project_config_dir"] = None
_ENV_BASELINE["EDISON_paths__user_config_dir"] = None


def _copy_tree_contents(src: Path, dst: Path) -> None:
    for child in src.iterdir():
        target = dst / child.name
        if child.is_dir():
            shutil.copytree(child, target, dirs_exist_ok=True)
        else:
            shutil.copy2(child, target)


def _init_isolated_project_root(root: Path) -> None:
    """Initialize a minimal Edison project root (git + .edison + .project)."""
    run_with_timeout(
        ["git", "init", "-b", "main"],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    run_with_timeout(
        ["git", "config", "user.email", "test@example.com"],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    run_with_timeout(
        ["git", "config", "user.name", "Test User"],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    readme_file = root / "README.md"
    readme_file.write_text("# Test Project\n", encoding="utf-8")
    run_with_timeout(
        ["git", "add", "README.md"],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    run_with_timeout(
        ["git", "commit", "-m", "Initial commit"],
        cwd=root,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    project_config_dir = root / ".edison" / "config"
    project_config_dir.mkdir(parents=True, exist_ok=True)

    (root / ".edison" / "guidelines").mkdir(parents=True, exist_ok=True)
    (root / ".edison" / "validators").mkdir(parents=True, exist_ok=True)
    (root / ".edison" / "rules").mkdir(parents=True, exist_ok=True)

    project_root = root / ".project"
    agents_root = root / ".edison"

    states_config = load_test_states()

    task_unique_dirs = states_config.get("task", {}).get("unique_dirs", [])
    for dir_name in task_unique_dirs:
        (project_root / "tasks" / dir_name).mkdir(parents=True, exist_ok=True)

    qa_unique_dirs = states_config.get("qa", {}).get("unique_dirs", [])
    for dir_name in qa_unique_dirs:
        (project_root / "qa" / dir_name).mkdir(parents=True, exist_ok=True)

    qa_additional = states_config.get("additional_paths", {}).get("qa", [])
    for rel_path in qa_additional:
        (project_root / rel_path).mkdir(parents=True, exist_ok=True)

    session_unique_dirs = states_config.get("session", {}).get("unique_dirs", [])
    for dir_name in session_unique_dirs:
        (project_root / "sessions" / dir_name).mkdir(parents=True, exist_ok=True)

    for rel in [
        "sessions",
        "validators",
        "config",
    ]:
        (agents_root / rel).mkdir(parents=True, exist_ok=True)

    task_tpl_src = REPO_ROOT / ".project" / "tasks" / "TEMPLATE.md"
    task_tpl_dst = project_root / "tasks" / "TEMPLATE.md"
    task_tpl_dst.parent.mkdir(parents=True, exist_ok=True)
    if task_tpl_src.exists():
        task_tpl_dst.write_text(task_tpl_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
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
        from tests.config import get_default_value

        default_qa_state = get_default_value("qa", "state")
        qa_tpl_dst.write_text(
            "# QA Template\n\n"
            "## Metadata\n"
            "- **Validator Owner:** _unassigned_\n"
            f"- **Status:** {default_qa_state}\n",
            encoding="utf-8",
        )

    from edison.data import get_data_path
    from tests.config import get_default_value

    session_tpl_src = get_data_path("templates", "session.template.json")
    session_tpl_dst = agents_root / "sessions" / "TEMPLATE.json"
    session_tpl_dst.parent.mkdir(parents=True, exist_ok=True)
    if session_tpl_src.exists():
        session_tpl_dst.write_text(session_tpl_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
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

    validators_src = REPO_ROOT / ".agents" / "validators" / "config.json"
    if validators_src.exists():
        validators_dst_dir = agents_root / "validators"
        validators_dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(validators_src, validators_dst_dir / "config.json")

    config_src_dir = REPO_ROOT / ".agents" / "config"
    if config_src_dir.exists():
        shutil.copytree(config_src_dir, agents_root / "config", dirs_exist_ok=True)

    agents_md_src = REPO_ROOT / "AGENTS.md"
    agents_md_dst = root / "AGENTS.md"
    if agents_md_src.exists():
        agents_md_dst.write_text(agents_md_src.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        agents_md_dst.write_text(
            "# Edison Framework\n\n"
            "This is a test project using Edison Framework.\n\n"
            "## Project Overview\n"
            "Test project for Edison Framework unit tests.\n",
            encoding="utf-8",
        )

    ready_wrapper_src = REPO_ROOT / ".agents" / "scripts" / "tasks" / "ready"
    ready_wrapper_dst = agents_root / "scripts" / "tasks" / "ready"
    ready_wrapper_dst.parent.mkdir(parents=True, exist_ok=True)
    if ready_wrapper_src.exists():
        shutil.copyfile(ready_wrapper_src, ready_wrapper_dst)
    else:
        ready_wrapper_dst.write_text(
            "#!/usr/bin/env python3\n"
            "# Minimal tasks/ready wrapper for tests\n"
            "# Real implementation is in edison.cli.task.ready\n"
            "from edison.cli.task.ready import main\n"
            "import sys\n"
            "sys.exit(main())\n",
            encoding="utf-8",
        )


@pytest.fixture(scope="session")
def _isolated_project_template_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    template_root = tmp_path_factory.mktemp("edison-project-template")
    _init_isolated_project_root(template_root)
    return template_root


@pytest.fixture(scope="session")
def _git_repo_template_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Session-scoped initialized git repo used as a fast copy template for E2E tests."""
    from helpers.env import TestGitRepo

    template_root = tmp_path_factory.mktemp("edison-git-template")
    TestGitRepo(template_root, init_repo=True)
    return template_root


@pytest.fixture(autouse=True)
def _reset_global_project_root_cache(tmp_path: Path) -> None:
    """Ensure all global caches are fresh for each test."""
    # Tests must never read a real ~/.edison user layer. Force an isolated
    # per-test user config directory unless a test explicitly overrides it.
    os.environ["EDISON_paths__user_config_dir"] = str(tmp_path / ".edison-user")
    reset_edison_caches()
    yield
    reset_edison_caches()
    for k, v in _ENV_BASELINE.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


@pytest.fixture
def isolated_project_env(tmp_path, monkeypatch, _isolated_project_template_dir: Path):
    """
    Isolated project environment for tests.

    CRITICAL: All tests MUST use this fixture to avoid
    creating .edison/.project during tests.
    """
    # Keep the "repo root" separate from the per-test temp root so auxiliary
    # paths (like the forced user config dir) do not pollute the git working tree.
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _copy_tree_contents(_isolated_project_template_dir, repo_root)
    # Set environment variable and change to tmp directory
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo_root))
    # Ensure config resolves `.edison/` inside this isolated repo.
    # Some developer environments set this override; tests must be deterministic.
    monkeypatch.delenv("EDISON_paths__project_config_dir", raising=False)
    monkeypatch.chdir(repo_root)

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
                mod._REPO_ROOT_OVERRIDE = repo_root  # type: ignore[attr-defined]
        except Exception:
            pass

    yield repo_root

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
def combined_env(tmp_path: Path, repo_root: Path, _git_repo_template_dir: Path):
    """Combined fixture with both TestProjectDir and TestGitRepo.

    Useful for tests that need both project structure and git operations.
    """
    from helpers.env import TestProjectDir, TestGitRepo

    git_root = tmp_path / "git"
    proj_root = tmp_path / "proj"
    git_root.mkdir(parents=True, exist_ok=True)
    proj_root.mkdir(parents=True, exist_ok=True)

    # Copy a session-scoped initialized git repo template (git init + initial commit)
    # instead of re-initializing for every test.
    _copy_tree_contents(_git_repo_template_dir, git_root)
    git_repo = TestGitRepo(git_root, init_repo=False)
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
