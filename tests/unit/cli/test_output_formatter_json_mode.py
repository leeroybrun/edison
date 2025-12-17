from __future__ import annotations

import json

from edison.cli import OutputFormatter


def test_output_formatter_suppresses_text_in_json_mode(capsys) -> None:
    fmt = OutputFormatter(json_mode=True)
    fmt.text("hello")
    out = capsys.readouterr()
    assert out.out == ""


def test_output_formatter_text_kv_suppresses_in_json_mode(capsys) -> None:
    fmt = OutputFormatter(json_mode=True)
    fmt.text_kv("Key", "Value")
    out = capsys.readouterr()
    assert out.out == ""


def test_output_formatter_json_output_still_prints(capsys) -> None:
    fmt = OutputFormatter(json_mode=True)
    fmt.json_output({"ok": True})
    out = capsys.readouterr()
    assert json.loads(out.out) == {"ok": True}

