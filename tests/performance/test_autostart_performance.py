"""Performance benchmark for session auto-start."""
from __future__ import annotations

import sys
import time
from pathlib import Path


from tests.integration.test_session_autostart import AutoStartEnv
from edison.core.session.lifecycle.autostart import SessionAutoStart


def test_autostart_performance_benchmark(tmp_path: Path, monkeypatch) -> None:
    """Benchmark session auto-start flow; should stay under 5s average."""
    env = AutoStartEnv(tmp_path, monkeypatch)
    env.write_defaults()
    env.write_session_config()
    script, _ = env.make_orchestrator_script("mock")
    env.write_orchestrator_config(
        {
            "mock": {
                "command": str(script),
                "cwd": "{session_worktree}",
                "initial_prompt": {"enabled": False},
            }
        },
        default="mock",
    )
    autostart = env.build_autostart()

    durations: list[float] = []
    for i in range(5):
        start_ts = time.perf_counter()
        autostart.start(
            process=f"perf-{i}",
            orchestrator_profile="mock",
            dry_run=True,
            launch_orchestrator=False,
            persist_dry_run=True,
        )
        durations.append(time.perf_counter() - start_ts)

    avg_time = sum(durations) / len(durations)
    print(f"Average auto-start time: {avg_time:.4f}s")
    assert avg_time < 5.0, f"Auto-start average {avg_time:.2f}s exceeds budget"
