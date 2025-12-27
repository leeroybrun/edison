import os
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EDISON_paths__user_config_dir", raising=False)


def test_get_user_config_dir_env_var_absolute(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from edison.core.utils.paths.user import get_user_config_dir

    target = tmp_path / ".edison-user"
    monkeypatch.setenv("EDISON_paths__user_config_dir", str(target))
    assert get_user_config_dir(create=False) == target


def test_get_user_config_dir_env_var_relative(monkeypatch: pytest.MonkeyPatch) -> None:
    from edison.core.utils.paths.user import get_user_config_dir

    monkeypatch.setenv("EDISON_paths__user_config_dir", ".my-edison")
    assert get_user_config_dir(create=False) == Path.home() / ".my-edison"

