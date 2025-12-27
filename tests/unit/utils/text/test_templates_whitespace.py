from __future__ import annotations

from edison.core.utils.text.templates import render_template_text


def test_render_template_text_trims_block_only_lines() -> None:
    text = "\n".join(
        [
            "one",
            "{% if enabled %}",
            "two",
            "{% endif %}",
            "three",
            "",
        ]
    )

    rendered = render_template_text(text, {"enabled": True})
    assert rendered.splitlines() == ["one", "two", "three"]

