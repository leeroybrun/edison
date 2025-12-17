from __future__ import annotations


from edison.core.qa.engines.parsers import ensure_parsers_loaded, get_parser


def test_core_parsers_load_and_plain_text_parser_works() -> None:
    # No project_root needed for core parser loading.
    ensure_parsers_loaded(project_root=None, active_packs=[])
    parser = get_parser("plain_text")
    assert parser is not None

    result = parser("  hello  ")
    # ParseResult is a TypedDict, so we validate structure instead of isinstance().
    assert isinstance(result, dict)
    assert result.get("response") == "hello"
    assert result.get("error") is None



