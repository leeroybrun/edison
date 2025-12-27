from __future__ import annotations

from edison.core.utils.merge import deep_merge, merge_arrays


def test_merge_arrays_empty_override_replaces_base() -> None:
    assert merge_arrays([1, 2], []) == []


def test_deep_merge_empty_list_overrides_base_list() -> None:
    base = {"validators": {"global-auggie": {"triggers": ["*"]}}}
    override = {"validators": {"global-auggie": {"triggers": []}}}

    merged = deep_merge(base, override)
    assert merged["validators"]["global-auggie"]["triggers"] == []


def test_merge_arrays_list_of_dicts_with_id_merges_by_id_by_default() -> None:
    """Extensibility arrays (list of dicts with `id`) should merge-by-id by default.

    This prevents packs/projects from accidentally replacing core definitions when they
    forget to use the explicit `+` array marker.
    """
    base = [
        {"id": "session-next", "domain": "session", "short_desc": "core"},
        {"id": "task-claim", "domain": "task", "short_desc": "core"},
    ]
    override = [
        {"id": "typescript-check", "domain": "typescript", "short_desc": "pack"},
        {"id": "task-claim", "domain": "task", "short_desc": "pack override"},
    ]
    merged = merge_arrays(base, override)

    by_id = {d["id"]: d for d in merged}
    assert set(by_id.keys()) == {"session-next", "task-claim", "typescript-check"}
    assert by_id["task-claim"]["short_desc"] == "pack override"


def test_merge_arrays_list_of_dicts_with_id_can_explicitly_replace() -> None:
    base = [{"id": "a"}, {"id": "b"}]
    override = ["=", {"id": "only"}]
    assert merge_arrays(base, override) == [{"id": "only"}]


def test_merge_arrays_list_of_dicts_with_id_can_disable_item() -> None:
    """Higher-priority layers can disable (remove) a specific id."""
    base = [
        {"id": "session-next", "domain": "session"},
        {"id": "task-claim", "domain": "task"},
    ]
    override = [
        {"id": "task-claim", "enabled": False},
    ]
    merged = merge_arrays(base, override)
    ids = [d["id"] for d in merged]
    assert ids == ["session-next"]


def test_merge_arrays_list_of_dicts_with_id_disable_then_readd_last_wins() -> None:
    base = [{"id": "a", "x": 1}, {"id": "b", "x": 1}]
    override = [
        {"id": "b", "enabled": False},
        {"id": "b", "x": 2},
    ]
    merged = merge_arrays(base, override)
    by_id = {d["id"]: d for d in merged}
    assert set(by_id.keys()) == {"a", "b"}
    assert by_id["b"]["x"] == 2


def test_merge_arrays_scalar_remove_marker() -> None:
    """Scalar lists can remove items using the '-' marker."""
    assert merge_arrays([1, 2, 3], ["-", 2]) == [1, 3]
    assert merge_arrays(["a", "b", "c"], ["-", "b", "missing"]) == ["a", "c"]

