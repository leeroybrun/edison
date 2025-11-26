"""Evidence manager base class."""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from ...paths import PathResolver
from ...paths.management import get_management_paths
from . import rounds


class EvidenceManagerBase:
    """Base class for EvidenceManager."""

    def __init__(self, task_id: str, project_root: Optional[Path] = None):
        self.task_id = task_id
        root = project_root or PathResolver.resolve_project_root()
        mgmt_paths = get_management_paths(root)
        self.base_dir = mgmt_paths.get_qa_root() / "validation-evidence" / task_id

    def _get_latest_round_dir(self) -> Optional[Path]:
        """Get latest round-N directory."""
        return rounds.find_latest_round_dir(self.base_dir)

    def get_round_number(self, round_dir: Path) -> int:
        """Extract round number from round directory name."""
        return rounds.get_round_number(round_dir)

    def create_next_round_dir(self) -> Path:
        """Create next round-{N+1} directory and return path."""
        return rounds.create_next_round_dir(self.base_dir)

    def list_rounds(self) -> List[Path]:
        """List all round directories for this task."""
        return rounds.list_round_dirs(self.base_dir)

    def _resolve_round_dir(self, round: Optional[int] = None) -> Optional[Path]:
        """Internal helper to resolve round directory."""
        return rounds.resolve_round_dir(self.base_dir, round)
