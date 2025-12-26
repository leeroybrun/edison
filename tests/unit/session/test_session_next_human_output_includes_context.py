from edison.core.session.next.output import format_human_readable


def test_session_next_human_output_includes_context_block():
    payload = {
        "sessionId": "sess-1",
        "context": {
            "isEdisonProject": True,
            "projectRoot": "/tmp/project",
            "sessionId": "sess-1",
            "activePacks": ["python"],
        },
        "actions": [],
        "blockers": [],
        "reportsMissing": [],
        "followUpsPlan": [],
        "rulesEngine": {},
        "rules": [],
        "recommendations": [],
    }

    text = format_human_readable(payload)
    assert "Edison Context" in text
    assert "sess-1" in text
    assert "Constitution (Agent)" in text
