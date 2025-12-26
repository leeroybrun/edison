"""Tests for composition/adapters write policies (partial managed files).

Following STRICT TDD - tests written FIRST, implementation second.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.helpers.cache_utils import reset_edison_caches
from tests.helpers.fixtures import create_edison_config_structure, create_repo_with_git
from tests.helpers.io_utils import write_yaml


BEGIN = "<!-- EDISON_TEST_AUTOGEN:BEGIN -->"
END = "<!-- EDISON_TEST_AUTOGEN:END -->"


@pytest.fixture
def repo_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = create_repo_with_git(tmp_path)
    create_edison_config_structure(repo)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(repo))
    reset_edison_caches()
    return repo


def test_markers_policy_replaces_only_block_in_roots(repo_env: Path) -> None:
    # Configure a write policy that matches AGENTS.md and uses markers mode.
    write_yaml(
        repo_env / ".edison" / "config" / "composition.yaml",
        {
            "composition": {
                "write_policies": [
                    {
                        "id": "agents-md-block",
                        "globs": ["AGENTS.md"],
                        "mode": "markers",
                        "begin_marker": BEGIN,
                        "end_marker": END,
                        "on_missing": "prepend",
                    }
                ],
            }
        },
    )
    reset_edison_caches()

    agents_path = repo_env / "AGENTS.md"
    agents_path.write_text(
        "\n".join(
            [
                "MANUAL PREFIX",
                BEGIN,
                "OLD BLOCK",
                END,
                "MANUAL SUFFIX",
                "",
            ]
        ),
        encoding="utf-8",
    )

    from edison.core.composition.registries._types_manager import ComposableTypesManager

    manager = ComposableTypesManager(project_root=repo_env)
    written = manager.write_type("roots", packs=[])
    assert agents_path in written

    updated = agents_path.read_text(encoding="utf-8")
    assert "MANUAL PREFIX" in updated
    assert "MANUAL SUFFIX" in updated
    assert "OLD BLOCK" not in updated
    assert BEGIN in updated and END in updated
    assert "# Edison Framework" in updated


def test_markers_policy_inserts_block_when_missing(repo_env: Path) -> None:
    write_yaml(
        repo_env / ".edison" / "config" / "composition.yaml",
        {
            "composition": {
                "write_policies": [
                    {
                        "id": "agents-md-block",
                        "globs": ["AGENTS.md"],
                        "mode": "markers",
                        "begin_marker": BEGIN,
                        "end_marker": END,
                        "on_missing": "prepend",
                    }
                ],
            }
        },
    )
    reset_edison_caches()

    agents_path = repo_env / "AGENTS.md"
    agents_path.write_text("MANUAL ONLY\n", encoding="utf-8")

    from edison.core.composition.registries._types_manager import ComposableTypesManager

    manager = ComposableTypesManager(project_root=repo_env)
    manager.write_type("roots", packs=[])

    updated = agents_path.read_text(encoding="utf-8")
    assert updated.startswith(BEGIN)
    assert "MANUAL ONLY" in updated
    assert END in updated


def test_adapter_default_write_policy_applies_when_no_glob_override(repo_env: Path) -> None:
    # Configure Claude adapter default write_policy to use markers mode.
    write_yaml(
        repo_env / ".edison" / "config" / "composition.yaml",
        {
            "composition": {
                "adapters": {
                    "claude": {
                        "write_policy": {
                            "mode": "markers",
                            "begin_marker": BEGIN,
                            "end_marker": END,
                            "on_missing": "prepend",
                        }
                    }
                }
            }
        },
    )
    reset_edison_caches()

    # Create a generated agent source file (ClaudeAdapter reads from generated agents dir).
    gen_dir = repo_env / ".edison" / "_generated" / "agents"
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "foo.md").write_text("# Foo Agent\nHello\n", encoding="utf-8")

    # Create an existing target file with manual sections + marker block.
    target = repo_env / ".claude" / "agents" / "foo.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(["MANUAL PREFIX", BEGIN, "OLD", END, "MANUAL SUFFIX", ""]),
        encoding="utf-8",
    )

    from edison.core.adapters.platforms.claude import ClaudeAdapter

    adapter = ClaudeAdapter(project_root=repo_env)
    written = adapter.sync_agents()
    assert target in written

    updated = target.read_text(encoding="utf-8")
    assert "MANUAL PREFIX" in updated
    assert "MANUAL SUFFIX" in updated
    assert "OLD" not in updated
    assert BEGIN in updated and END in updated


def test_glob_write_policy_rule_with_nested_policy_overrides_adapter_default(
    repo_env: Path,
) -> None:
    # Adapter default is full replace, but a matching glob rule uses markers mode.
    # The glob rule should win AND nested policy syntax should be supported.
    write_yaml(
        repo_env / ".edison" / "config" / "composition.yaml",
        {
            "composition": {
                "write_policies": [
                    {
                        "id": "claude-agents-managed",
                        "globs": [".claude/agents/foo.md"],
                        "policy": {
                            "mode": "markers",
                            "begin_marker": BEGIN,
                            "end_marker": END,
                            "on_missing": "prepend",
                        },
                    }
                ],
                "adapters": {"claude": {"write_policy": {"mode": "replace"}}},
            }
        },
    )
    reset_edison_caches()

    gen_dir = repo_env / ".edison" / "_generated" / "agents"
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "foo.md").write_text("# Foo Agent\nHello\n", encoding="utf-8")

    target = repo_env / ".claude" / "agents" / "foo.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "\n".join(["MANUAL PREFIX", BEGIN, "OLD", END, "MANUAL SUFFIX", ""]),
        encoding="utf-8",
    )

    from edison.core.adapters.platforms.claude import ClaudeAdapter

    adapter = ClaudeAdapter(project_root=repo_env)
    adapter.sync_agents()

    updated = target.read_text(encoding="utf-8")
    assert "MANUAL PREFIX" in updated
    assert "MANUAL SUFFIX" in updated
    assert "OLD" not in updated
    assert BEGIN in updated and END in updated
