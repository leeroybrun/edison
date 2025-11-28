"""QA-focused helpers layered on top of Edison core libs."""
from ..config.domains import qa as config
from ..legacy_guard import enforce_no_legacy_project_root
from .manager import QAManager
from .models import QARecord
from .repository import QARepository

enforce_no_legacy_project_root("lib.qa")

__all__ = [
    "QAManager",
    "QARecord",
    "QARepository",
    "config",
]
