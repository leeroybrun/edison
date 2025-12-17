from __future__ import annotations


from edison.cli._utils import detect_record_type


def test_detect_record_type_task_when_id_contains_qa_in_slug() -> None:
    # Task IDs may legitimately contain "qa" in the slug; only the *QA record* suffix
    # should imply qa record type.
    assert detect_record_type("170-wave1-qa-promote") == "task"


def test_detect_record_type_qa_when_suffix_is_dash_qa() -> None:
    assert detect_record_type("170-wave1-qa-promote-qa") == "qa"


def test_detect_record_type_qa_when_suffix_is_dot_qa() -> None:
    assert detect_record_type("170-wave1-qa-promote.qa") == "qa"



