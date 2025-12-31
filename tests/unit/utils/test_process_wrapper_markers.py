from __future__ import annotations

from dataclasses import dataclass

import pytest

from edison.core.utils.process import inspector


@dataclass
class _FakeProcess:
    pid: int
    _name: str
    _cmdline: list[str]
    _parent: _FakeProcess | None = None

    def name(self) -> str:
        return self._name

    def cmdline(self) -> list[str]:
        return list(self._cmdline)

    def parent(self) -> _FakeProcess | None:
        return self._parent


@pytest.fixture(autouse=True)
def _stable_process_config(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(inspector, "_load_llm_process_names", lambda: ["claude", "codex", "happy"])
    monkeypatch.setattr(inspector, "_load_llm_script_markers", lambda: ["happy", "codex", "claude"])
    monkeypatch.setattr(
        inspector,
        "_load_llm_marker_map",
        lambda: {"happy": "happy", "codex": "codex", "claude": "claude"},
    )
    monkeypatch.setattr(inspector, "_load_edison_process_names", lambda: ["edison", "python"])
    monkeypatch.setattr(inspector, "_load_edison_script_markers", lambda: ["edison"])


def test_marker_detects_wrapper_when_process_name_generic() -> None:
    # current (edison) -> node (happy wrapper) -> zsh
    root = _FakeProcess(pid=10, _name="zsh", _cmdline=["zsh"])
    wrapper = _FakeProcess(pid=20, _name="node", _cmdline=["node", "/path/to/happy"], _parent=root)
    current = _FakeProcess(pid=30, _name="edison", _cmdline=["edison", "session", "status"], _parent=wrapper)

    name, pid = inspector._find_topmost_process_from(current)  # noqa: SLF001
    assert (name, pid) == ("happy", 20)


def test_topmost_of_either_prefers_highest_match_edison_over_llm() -> None:
    # edison1 -> llm -> edison2 (current)
    edison1 = _FakeProcess(pid=100, _name="edison", _cmdline=["edison"], _parent=None)
    llm = _FakeProcess(pid=200, _name="node", _cmdline=["node", "/path/to/claude"], _parent=edison1)
    edison2 = _FakeProcess(pid=300, _name="edison", _cmdline=["edison"], _parent=llm)

    name, pid = inspector._find_topmost_process_from(edison2)  # noqa: SLF001
    assert (name, pid) == ("edison", 100)


def test_topmost_of_either_prefers_highest_match_llm_over_edison() -> None:
    # llm1 -> edison1 -> llm2 -> edison2 (current)
    llm1 = _FakeProcess(pid=100, _name="python", _cmdline=["python", "-m", "codex"], _parent=None)
    edison1 = _FakeProcess(pid=200, _name="edison", _cmdline=["edison"], _parent=llm1)
    llm2 = _FakeProcess(pid=300, _name="node", _cmdline=["node", "/path/to/happy"], _parent=edison1)
    edison2 = _FakeProcess(pid=400, _name="edison", _cmdline=["edison"], _parent=llm2)

    name, pid = inspector._find_topmost_process_from(edison2)  # noqa: SLF001
    assert (name, pid) == ("codex", 100)
