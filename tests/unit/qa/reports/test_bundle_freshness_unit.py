from __future__ import annotations

import os
import time
from pathlib import Path

from edison.core.qa import promoter
from tests.helpers.timeouts import SHORT_SLEEP
def test_should_revalidate_bundle_fresh(tmp_path: Path):
    # Create fake evidence structure
    evidence = tmp_path / ".project" / "qa" / "validation-evidence" / "t-1" / "round-1"
    evidence.mkdir(parents=True)
    summary = evidence / "bundle-approved.md"
    summary.write_text("---\napproved: true\n---\n")
    report = evidence / "validator-security-report.md"
    report.write_text("---\nvalidatorId: security\nverdict: approve\n---\n")

    # Make summary newer than reports
    os.utime(report, (summary.stat().st_atime - 5, summary.stat().st_mtime - 5))

    # Task file older than bundle
    task_file = tmp_path / ".project" / "tasks" / "done" / "t-1.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("---\nid: t-1\ntitle: t-1\n---\n")
    os.utime(task_file, (summary.stat().st_atime - 5, summary.stat().st_mtime - 5))

    need = promoter.should_revalidate_bundle(summary, [report], [task_file])
    assert need is False


def test_should_revalidate_bundle_stale_by_report(tmp_path: Path):
    evidence = tmp_path / ".project" / "qa" / "validation-evidence" / "t-1" / "round-1"
    evidence.mkdir(parents=True)
    summary = evidence / "bundle-approved.md"
    summary.write_text("---\napproved: true\n---\n")
    report = evidence / "validator-security-report.md"
    report.write_text("---\nvalidatorId: security\nverdict: approve\n---\n")
    # Make report newer than summary
    time.sleep(SHORT_SLEEP)
    os.utime(report, None)

    need = promoter.should_revalidate_bundle(summary, [report], [])
    assert need is True


def test_should_revalidate_bundle_stale_by_task_file(tmp_path: Path):
    evidence = tmp_path / ".project" / "qa" / "validation-evidence" / "t-1" / "round-1"
    evidence.mkdir(parents=True)
    summary = evidence / "bundle-approved.md"
    summary.write_text("---\napproved: true\n---\n")
    report = evidence / "validator-security-report.md"
    report.write_text("---\nvalidatorId: security\nverdict: approve\n---\n")
    task_file = tmp_path / ".project" / "tasks" / "done" / "t-1.md"
    task_file.parent.mkdir(parents=True, exist_ok=True)
    task_file.write_text("---\nid: t-1\ntitle: t-1\n---\n")
    # Make task file newer than summary
    time.sleep(SHORT_SLEEP)
    os.utime(task_file, None)

    need = promoter.should_revalidate_bundle(summary, [report], [task_file])
    assert need is True
