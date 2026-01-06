from __future__ import annotations


def test_git_repo_commit_all_is_noop_when_no_changes(git_repo) -> None:
    """commit_all should not raise when there is nothing to commit."""
    git_repo.commit_all("No changes")

