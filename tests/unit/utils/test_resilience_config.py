import time

import pytest

from edison.core.utils.resilience import retry_with_backoff
from tests.helpers.env_setup import setup_project_root


def test_retry_with_backoff_uses_config_defaults(tmp_path, monkeypatch):
    """retry_with_backoff should pull defaults from YAML config when args omitted."""
    setup_project_root(monkeypatch, tmp_path)

    cfg_dir = tmp_path / ".edison" / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg_path = cfg_dir / "resilience.yml"
    cfg_path.write_text(
        "\n".join(
            [
                "resilience:",
                "  retry:",
                "    max_attempts: 4",
                "    initial_delay_seconds: 0.01",
                "    backoff_factor: 2.0",
                "    max_delay_seconds: 0.05",
            ]
        ),
        encoding="utf-8",
    )

    sleep_calls: list[float] = []

    def _fake_sleep(seconds: float) -> None:
        sleep_calls.append(float(seconds))

    # Assert on requested delays rather than wall-clock sleep timing, which can be
    # noisy across platforms / Python versions.
    monkeypatch.setattr(time, "sleep", _fake_sleep)

    @retry_with_backoff()
    def flaky_operation():
        if len(sleep_calls) < 3:
            raise RuntimeError("transient failure")
        return "ok"

    result = flaky_operation()

    assert result == "ok"
    assert len(sleep_calls) == 3

    expected_delays = [0.01, 0.02, 0.04]

    for observed, expected in zip(sleep_calls, expected_delays, strict=True):
        assert observed == pytest.approx(expected, rel=0.0, abs=1e-6)
    assert max(sleep_calls) <= 0.05
