"""QA-focused helpers layered on top of Edison core libs."""
from ..legacy_guard import enforce_no_legacy_project_root
from .transaction import ValidationTransaction
from .manager import QAManager

enforce_no_legacy_project_root("lib.qa")

__all__ = ["ValidationTransaction", "QAManager"]
