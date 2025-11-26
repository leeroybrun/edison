import os
import time
import pytest

from edison.core.utils.resilience import retry_with_backoff


def test_retry_with_backoff_uses_config_defaults(tmp_path, monkeypatch):
    """retry_with_backoff should pull defaults from YAML config when args omitted."""
    monkeypatch.setenv("AGENTS_PROJECT_ROOT", str(tmp_path))

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

    attempt_times: list[float] = []

    @retry_with_backoff()
    def flaky_operation():
        attempt_times.append(time.perf_counter())
        if len(attempt_times) < 4:
            raise RuntimeError("transient failure")
        return "ok"

    result = flaky_operation()

    assert result == "ok"
    assert len(attempt_times) == 4

    observed_delays = [attempt_times[i + 1] - attempt_times[i] for i in range(len(attempt_times) - 1)]
    expected_delays = [0.01, 0.02, 0.04]

    for observed, expected in zip(observed_delays, expected_delays):
        assert observed == pytest.approx(expected, rel=0.5, abs=0.02)
    assert max(observed_delays) <= 0.07  # ensure max_delay_seconds respected with margin
