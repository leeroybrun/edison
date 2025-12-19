from __future__ import annotations

from edison.core.utils.merge import deep_merge, merge_arrays


def test_merge_arrays_empty_override_replaces_base() -> None:
    assert merge_arrays([1, 2], []) == []


def test_deep_merge_empty_list_overrides_base_list() -> None:
    base = {"validators": {"global-auggie": {"triggers": ["*"]}}}
    override = {"validators": {"global-auggie": {"triggers": []}}}

    merged = deep_merge(base, override)
    assert merged["validators"]["global-auggie"]["triggers"] == []

