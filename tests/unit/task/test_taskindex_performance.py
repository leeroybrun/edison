"""Performance tests for TaskIndex.

These tests verify that TaskIndex operations complete within acceptable time limits.
Target: <100ms for typical session operations.
"""
import time
from pathlib import Path

from edison.core.task.index import TaskIndex


class TestTaskIndexPerformance:
    """Performance verification tests for TaskIndex."""

    def test_empty_project_scan_is_fast(self, tmp_path: Path):
        """Verify scanning an empty project is fast (<200ms)."""
        # Create minimal project structure matching TaskConfig expectations
        (tmp_path / ".project" / "sessions").mkdir(parents=True)
        (tmp_path / ".project" / "tasks").mkdir(parents=True)
        (tmp_path / ".project" / "qa").mkdir(parents=True)

        index = TaskIndex(project_root=tmp_path)

        start = time.perf_counter()
        results = index.scan_all_task_files()
        elapsed = time.perf_counter() - start

        assert elapsed < 0.2, f"Empty scan took {elapsed:.3f}s, expected <200ms"
        assert results == []

    def test_small_project_scan_performance(self, tmp_path: Path):
        """Verify scanning a small project (10 tasks) is fast (<300ms)."""
        # Create project structure matching TaskConfig (.project/tasks)
        tasks_dir = tmp_path / ".project" / "tasks" / "wip"
        tasks_dir.mkdir(parents=True)
        (tmp_path / ".project" / "sessions").mkdir(parents=True)
        (tmp_path / ".project" / "qa").mkdir(parents=True)

        # Create 10 task files with frontmatter
        for i in range(10):
            task_file = tasks_dir / f"TASK-{i:03d}.md"
            task_file.write_text(f"""---
id: TASK-{i:03d}
title: Test Task {i}
session_id: test-session
---

# TASK-{i:03d}

Task content here.
""")

        index = TaskIndex(project_root=tmp_path)

        # Measure scan time
        start = time.perf_counter()
        results = index.scan_all_task_files()
        elapsed = time.perf_counter() - start

        assert elapsed < 0.3, f"Small project scan took {elapsed:.3f}s, expected <300ms"
        assert len(results) == 10

    def test_session_query_performance(self, tmp_path: Path):
        """Verify session query is fast (<300ms)."""
        # Create project structure matching TaskConfig (.project/tasks)
        tasks_dir = tmp_path / ".project" / "tasks" / "wip"
        tasks_dir.mkdir(parents=True)
        (tmp_path / ".project" / "sessions").mkdir(parents=True)
        (tmp_path / ".project" / "qa").mkdir(parents=True)

        # Create 20 tasks, 10 for each session
        for i in range(20):
            session = "session-1" if i < 10 else "session-2"
            task_file = tasks_dir / f"TASK-{i:03d}.md"
            task_file.write_text(f"""---
id: TASK-{i:03d}
title: Test Task {i}
session_id: {session}
---

# TASK-{i:03d}
""")

        index = TaskIndex(project_root=tmp_path)

        # Measure session query time
        start = time.perf_counter()
        tasks = index.list_tasks_in_session("session-1")
        elapsed = time.perf_counter() - start

        assert elapsed < 0.3, f"Session query took {elapsed:.3f}s, expected <300ms"
        assert len(tasks) == 10

    def test_task_graph_build_performance(self, tmp_path: Path):
        """Verify building task graph is fast (<600ms for 50 tasks)."""
        # Create project structure matching TaskConfig (.project/tasks)
        tasks_dir = tmp_path / ".project" / "tasks"
        for state in ["todo", "wip", "done"]:
            (tasks_dir / state).mkdir(parents=True)
        (tmp_path / ".project" / "sessions").mkdir(parents=True)
        (tmp_path / ".project" / "qa").mkdir(parents=True)

        # Create 50 tasks with dependencies
        for i in range(50):
            state = ["todo", "wip", "done"][i % 3]
            task_file = tasks_dir / state / f"TASK-{i:03d}.md"
            relationships = (
                "relationships:\n"
                f"  - type: depends_on\n    target: TASK-{i-1:03d}\n"
                if i > 0
                else ""
            )
            task_file.write_text(f"""---
id: TASK-{i:03d}
title: Test Task {i}
session_id: test-session
{relationships}
---

# TASK-{i:03d}
""")

        index = TaskIndex(project_root=tmp_path)

        # Measure graph build time
        start = time.perf_counter()
        graph = index.get_task_graph()
        elapsed = time.perf_counter() - start

        assert elapsed < 0.6, f"Graph build took {elapsed:.3f}s, expected <600ms"
        assert len(graph.tasks) == 50


class TestTaskIndexCachingRecommendation:
    """Tests documenting the caching recommendation.

    The current TaskIndex implementation has NO caching. Every query
    performs a full filesystem scan. This is acceptable for small projects
    but may become slow for larger projects (100+ tasks).

    RECOMMENDATION: Consider adding optional caching with TTL for:
    1. scan_all_task_files() results
    2. scan_all_qa_files() results

    Caching should be invalidated on:
    - Task file creation/deletion
    - Task file modification
    - Session creation/closure
    """

    def test_multiple_queries_repeat_scan(self, tmp_path: Path):
        """Document that multiple queries rescan the filesystem.

        This test documents current behavior - not a bug, just noting
        that caching would improve performance for repeated queries.
        """
        tasks_dir = tmp_path / ".project" / "tasks" / "wip"
        tasks_dir.mkdir(parents=True)
        (tmp_path / ".project" / "sessions").mkdir(parents=True)
        (tmp_path / ".project" / "qa").mkdir(parents=True)

        # Create 5 tasks
        for i in range(5):
            task_file = tasks_dir / f"TASK-{i:03d}.md"
            task_file.write_text(f"""---
id: TASK-{i:03d}
session_id: test-session
---
# TASK-{i:03d}
""")

        index = TaskIndex(project_root=tmp_path)

        # Multiple queries each rescan the filesystem
        times = []
        for _ in range(5):
            start = time.perf_counter()
            index.list_tasks_in_session("test-session")
            times.append(time.perf_counter() - start)

        # All times should be similar (no caching benefit)
        # Document: with caching, subsequent queries would be faster
        # For now, accept that all queries take similar time (within 0.5s each)
        assert all(t < 0.5 for t in times), f"All queries should complete quickly, got: {times}"











