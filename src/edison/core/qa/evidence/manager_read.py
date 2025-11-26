"""Evidence manager read mixin."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol

from . import io as evidence_io


class EvidenceManagerProtocol(Protocol):
    """Protocol for mixin dependencies."""
    def _resolve_round_dir(self, round: Optional[int] = None) -> Optional[Path]: ...


class EvidenceManagerReadMixin:
    """Read operations for EvidenceManager."""

    def _read_bundle_summary(self: EvidenceManagerProtocol, round: Optional[int] = None) -> Dict[str, Any]:
        """Read bundle-approved.json from specified round (or latest)."""
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            return {}
        return evidence_io.read_bundle_summary(round_dir)

    def _read_implementation_report(self: EvidenceManagerProtocol, round: Optional[int] = None) -> Dict[str, Any]:
        """Read implementation-report.json."""
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            return {}
        return evidence_io.read_implementation_report(round_dir)

    def read_validator_report(
        self: EvidenceManagerProtocol,
        validator_name: str,
        round: Optional[int] = None
    ) -> Dict[str, Any]:
        """Read validator-{name}-report.json."""
        round_dir = self._resolve_round_dir(round)
        if round_dir is None:
            return {}
        return evidence_io.read_validator_report(round_dir, validator_name)

    def list_validator_reports(self: EvidenceManagerProtocol, round: Optional[int] = None) -> List[Path]:
        """List all validator-*-report.json files in round directory."""
        round_dir = self._resolve_round_dir(round)
        if round_dir is None or not round_dir.exists():
            return []
        return evidence_io.list_validator_reports(round_dir)
