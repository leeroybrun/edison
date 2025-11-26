"""Session journaling atomicity tests.

Ensures begin/finalize/abort use file locks to avoid concurrent partial writes.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
import unittest

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPTS_DIR = REPO_ROOT / ".edison" / "core"

# Import libs after adding to path
import sys
from edison.core import task  # type: ignore  # pylint: disable=wrong-import-position
from edison.data import get_data_path
from edison.core.session import transaction as session_transaction
from edison.core.session import store as session_store
from edison.core.utils.io.locking import LockTimeoutError


class SessionJournalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_root = Path(tempfile.mkdtemp(prefix="project-journal-tests-"))
        self.addCleanup(lambda: shutil.rmtree(self.temp_root, ignore_errors=True))
        os.environ["project_ROOT"] = str(self.temp_root)

        # Minimal sessions structure
        sessions_root = self.temp_root / ".project" / "sessions"
        sessions_root.mkdir(parents=True, exist_ok=True)
        (get_data_path("templates", "session.template.json")).replace(sessions_root / "TEMPLATE.json") if False else shutil.copyfile(
            get_data_path("templates", "session.template.json"),
            sessions_root / "TEMPLATE.json",
        )

    def test_finalize_respects_lock(self) -> None:
        session_id = "journal-1"
        # Create a tx and hold a lock on its file, then attempt finalize
        tx_id = session_transaction.begin_tx(session_id, domain="task", record_id="X", from_status="wip", to_status="done")
        tx_file = (session_transaction._tx_dir(session_store.sanitize_session_id(session_id)) / f"{tx_id}.json")
        self.assertTrue(tx_file.exists())

        with task.file_lock(tx_file):
            with self.assertRaises(LockTimeoutError):
                session_transaction.finalize_tx(session_id, tx_id)

    def test_abort_respects_lock(self) -> None:
        session_id = "journal-2"
        tx_id = session_transaction.begin_tx(session_id, domain="qa", record_id="Y", from_status="todo", to_status="wip")
        tx_file = (session_transaction._tx_dir(session_store.sanitize_session_id(session_id)) / f"{tx_id}.json")
        with task.file_lock(tx_file):
            with self.assertRaises(LockTimeoutError):
                session_transaction.abort_tx(session_id, tx_id, reason="test")


if __name__ == "__main__":
    unittest.main()
