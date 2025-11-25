from pathlib import Path

from edison.core.tdd_example import slugify


def test_slugify_basic():
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_spaces_and_dashes():
    assert slugify("  multiple   spaces ") == "multiple-spaces"
    assert slugify("Already-slugified") == "already-slugified"
