"""Evidence operations manager for Edison framework."""

from .manager import (
    EvidenceError,
    EvidenceManager,
    get_evidence_manager,
)
from .helpers import (
    _task_evidence_root,
    get_evidence_dir,
    get_latest_round,
    get_implementation_report_path,
    list_evidence_files,
)
from .followups import (
    load_impl_followups,
    load_bundle_followups,
)
from .analysis import (
    missing_evidence_blockers,
    read_validator_jsons,
    has_required_evidence,
)

__all__ = [
    "EvidenceError",
    "EvidenceManager",
    "get_evidence_manager",
    "missing_evidence_blockers",
    "read_validator_jsons",
    "load_impl_followups",
    "load_bundle_followups",
    "_task_evidence_root",
    "get_evidence_dir",
    "get_latest_round",
    "get_implementation_report_path",
    "list_evidence_files",
    "has_required_evidence",
]
