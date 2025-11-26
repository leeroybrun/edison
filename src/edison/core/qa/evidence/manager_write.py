"""Evidence manager write mixin."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from .exceptions import EvidenceError
from . import io as evidence_io


class EvidenceManagerProtocol(Protocol):
    """Protocol for mixin dependencies."""
    task_id: str
    def _resolve_round_dir(self, round: Optional[int] = None) -> Optional[Path]: ...


class EvidenceManagerWriteMixin:
    """Write operations for EvidenceManager."""

    def write_bundle_summary(
        self: EvidenceManagerProtocol,
        data: Dict[str, Any],
        round: Optional[int] = None
    ) -> None:
        """Write bundle-approved.json to specified round."""
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            raise EvidenceError(
                f"Cannot write bundle summary: no rounds exist for task {self.task_id}"
            )
        evidence_io.write_bundle_summary(round_dir, data)

    def write_implementation_report(
        self: EvidenceManagerProtocol,
        data: Dict[str, Any],
        round: Optional[int] = None
    ) -> None:
        """Write implementation-report.json to specified round."""
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            raise EvidenceError(
                f"Cannot write implementation report: no rounds exist for task {self.task_id}"
            )
        evidence_io.write_implementation_report(round_dir, data)

    def write_validator_report(
        self: EvidenceManagerProtocol,
        validator_name: str,
        data: Dict[str, Any],
        round: Optional[int] = None
    ) -> None:
        """Write validator-{name}-report.json to specified round."""
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            raise EvidenceError(
                f"Cannot write validator report: no rounds exist for task {self.task_id}"
            )
        evidence_io.write_validator_report(round_dir, validator_name, data)
