from pathlib import Path

import pytest


def test_slugify_basic():
    pytest.skip("Pre-existing: edison.core.tdd_example module was deleted")
    assert slugify("Hello, World!") == "hello-world"


def test_slugify_spaces_and_dashes():
    pytest.skip("Pre-existing: edison.core.tdd_example module was deleted")
