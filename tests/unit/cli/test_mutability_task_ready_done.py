from __future__ import annotations

import argparse


def test_task_ready_listing_is_not_mutating() -> None:
    from edison.cli._mutability import is_mutating_invocation

    args = argparse.Namespace(record_id=None, session=None, json=False, repo_root=None)
    assert is_mutating_invocation("task ready", args) is False


def test_task_ready_with_record_id_is_mutating() -> None:
    from edison.cli._mutability import is_mutating_invocation

    args = argparse.Namespace(record_id="T-1", session="sess-1", json=False, repo_root=None)
    assert is_mutating_invocation("task ready", args) is True


def test_task_done_is_mutating() -> None:
    from edison.cli._mutability import is_mutating_invocation

    args = argparse.Namespace(record_id="T-1", session="sess-1", json=False, repo_root=None)
    assert is_mutating_invocation("task done", args) is True

