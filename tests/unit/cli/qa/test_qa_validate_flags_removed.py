from __future__ import annotations

import argparse

import pytest


def _parser() -> argparse.ArgumentParser:
    from edison.cli.qa.validate import register_args

    parser = argparse.ArgumentParser(prog="edison qa validate")
    register_args(parser)
    return parser


@pytest.mark.qa
def test_qa_validate_rejects_new_round_flag() -> None:
    parser = _parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["T-001", "--execute", "--new-round"])


@pytest.mark.qa
def test_qa_validate_rejects_check_only_flag() -> None:
    parser = _parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["T-001", "--check-only"])

