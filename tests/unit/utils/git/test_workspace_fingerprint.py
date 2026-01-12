from __future__ import annotations

from pathlib import Path

from edison.core.utils.git.fingerprint import compute_workspace_fingerprint


def test_workspace_fingerprint_is_deterministic_for_multiple_roots(tmp_path: Path) -> None:
    r1 = tmp_path / "repo1"
    r2 = tmp_path / "repo2"
    r1.mkdir()
    r2.mkdir()

    fp1 = compute_workspace_fingerprint(git_roots=[r1, r2])
    fp2 = compute_workspace_fingerprint(git_roots=[r1, r2])

    assert fp1["gitHead"].startswith("workspace-")
    assert fp1 == fp2


def test_workspace_fingerprint_changes_when_extra_file_changes(tmp_path: Path) -> None:
    r1 = tmp_path / "repo1"
    r2 = tmp_path / "repo2"
    r1.mkdir()
    r2.mkdir()

    extra = tmp_path / "stack-env"
    extra.write_text("A=1\n", encoding="utf-8")
    fp1 = compute_workspace_fingerprint(git_roots=[r1, r2], extra_files=[extra])

    extra.write_text("A=2\n", encoding="utf-8")
    fp2 = compute_workspace_fingerprint(git_roots=[r1, r2], extra_files=[extra])

    assert fp1["diffHash"] != fp2["diffHash"]

