from pathlib import Path
from typing import Dict, Any, Optional

from edison.core.adapters.base import PlatformAdapter


class DummyAdapter(PlatformAdapter):
    """Minimal PlatformAdapter for test components."""

    def __init__(self, project_root: Path, config: Optional[Dict[str, Any]] = None):
        # Allow injecting config override
        self._test_config = config or {}
        super().__init__(project_root=project_root)
        # Override loaded config with test config if provided
        if self._test_config:
            self.config.update(self._test_config)

    @property
    def platform_name(self) -> str:
        return "dummy"

    def sync_all(self) -> Dict[str, Any]:
        return {}
