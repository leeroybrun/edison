from __future__ import annotations

from edison.core.qa.engines.base import EngineConfig
from edison.core.qa.engines.cli import CLIEngine


def _engine() -> CLIEngine:
    cfg = EngineConfig.from_dict(
        "codex-cli",
        {
            "type": "cli",
            "command": "codex",
            "subcommand": "exec",
            "response_parser": "codex",
        },
    )
    return CLIEngine(cfg)


def test_verdict_extraction_prefers_explicit_verdict_marker() -> None:
    e = _engine()
    assert e._extract_verdict_from_response("Verdict: reject\nApprove?") == "reject"
    assert e._extract_verdict_from_response("Verdict: approve\nReject?") == "approve"


def test_verdict_extraction_handles_cant_be_approved_variants() -> None:
    e = _engine()
    assert e._extract_verdict_from_response("This can’t be approved.") == "reject"
    assert e._extract_verdict_from_response("This can't be approved.") == "reject"
    assert e._extract_verdict_from_response("This cant be approved.") == "reject"
    assert e._extract_verdict_from_response("Cannot approve this.") == "reject"
    assert e._extract_verdict_from_response("Not approved.") == "reject"


def test_verdict_extraction_does_not_treat_approval_requests_as_approval() -> None:
    e = _engine()
    assert e._extract_verdict_from_response("Please approve exiting plan mode.") is None
