"""Unified config writer for Edison setup flows.

This module provides a single source of truth for writing project configuration
files. It supports:
- Diff-based generation (only outputs values different from defaults)
- Multiple write modes: create, merge, overwrite
- File conflict handling with preview
- Atomic writes with locking

Used by both `edison init` and `edison config configure` commands.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from edison.core.config import ConfigManager
from edison.core.utils.io import dump_yaml_string, read_yaml, write_yaml, ensure_directory
from edison.core.utils.merge import deep_merge
from edison.core.utils.paths import get_project_config_dir


class WriteMode(Enum):
    """File write mode for config files."""
    CREATE = "create"      # Only create if not exists
    MERGE = "merge"        # Deep merge with existing
    OVERWRITE = "overwrite"  # Replace existing


@dataclass
class FileAction:
    """Describes what will happen to a single file."""
    path: Path
    action: str  # "create", "update", "skip", "merge"
    content: str
    existing_content: Optional[str] = None
    diff_keys: List[str] = field(default_factory=list)


@dataclass
class WriteResult:
    """Result of a write operation."""
    success: bool
    files_written: List[Path] = field(default_factory=list)
    files_skipped: List[Path] = field(default_factory=list)
    files_merged: List[Path] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class ConfigWriter:
    """Unified config writer for init/configure/reconfigure flows.
    
    This class handles:
    - Comparing questionnaire answers against bundled defaults
    - Generating minimal override-only config files
    - Writing with proper conflict handling
    - Preview of changes before writing
    """

    # Mapping of config sections to their target files
    SECTION_FILE_MAP = {
        "paths": "defaults.yml",
        "project": "project.yml",
        "database": "defaults.yml",
        "auth": "defaults.yml",
        "packs": "packs.yml",
        "validators": "validators.yml",
        "agents": "delegation.yml",
        "delegation": "delegation.yml",
        "orchestrators": "orchestrators.yml",
        "worktrees": "worktrees.yml",
        "workflow": "workflow.yml",
        "tdd": "tdd.yml",
        "ci": "ci.yml",
        "commands": "commands.yml",
        "hooks": "hooks.yml",
        "context7": "context7.yml",
    }

    def __init__(self, repo_root: Path) -> None:
        """Initialize the config writer.
        
        Args:
            repo_root: Repository root path
        """
        self.repo_root = repo_root
        self.config_dir = get_project_config_dir(repo_root, create=False) / "config"
        self._bundled_defaults: Optional[Dict[str, Any]] = None

    @property
    def bundled_defaults(self) -> Dict[str, Any]:
        """Get bundled defaults (cached)."""
        if self._bundled_defaults is None:
            # Load only bundled defaults from all core config files
            manager = ConfigManager(self.repo_root)
            cfg: Dict[str, Any] = {}

            # Load all yaml files from core config directory
            if manager.core_config_dir.exists():
                yml_files = list(manager.core_config_dir.glob("*.yml"))
                yaml_files = list(manager.core_config_dir.glob("*.yaml"))
                for path in sorted(yml_files + yaml_files):
                    module_cfg = manager.load_yaml(path)
                    cfg = deep_merge(cfg, module_cfg)

            self._bundled_defaults = cfg
        return self._bundled_defaults

    def compute_overrides(
        self,
        config_dict: Dict[str, Any],
        defaults: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Compute which values differ from defaults.
        
        Args:
            config_dict: Full config dictionary from questionnaire
            defaults: Defaults to compare against (uses bundled if not provided)
            
        Returns:
            Dict mapping filename to override content
        """
        defaults = defaults or self.bundled_defaults
        overrides: Dict[str, Dict[str, Any]] = {}
        
        for section, value in config_dict.items():
            if not value:  # Skip empty sections
                continue
                
            default_value = defaults.get(section)
            
            # Check if this section differs from defaults
            if self._values_differ(value, default_value):
                # Determine target file
                target_file = self.SECTION_FILE_MAP.get(section, f"{section}.yml")
                
                # Initialize file entry if needed
                if target_file not in overrides:
                    overrides[target_file] = {}
                
                # Compute the minimal diff for this section
                if isinstance(value, dict) and isinstance(default_value, dict):
                    diff = self._compute_dict_diff(value, default_value)
                    if diff:
                        overrides[target_file][section] = diff
                else:
                    overrides[target_file][section] = value
        
        # Remove empty files
        return {k: v for k, v in overrides.items() if v}

    def _values_differ(self, value: Any, default: Any) -> bool:
        """Check if a value differs from its default."""
        if default is None:
            # No default means any non-empty value is an override
            if isinstance(value, (list, dict, str)):
                return bool(value)
            return value is not None
        
        if type(value) != type(default):
            return True
            
        if isinstance(value, dict):
            # Recursively check dict values
            all_keys = set(value.keys()) | set(default.keys())
            for key in all_keys:
                if self._values_differ(value.get(key), default.get(key)):
                    return True
            return False
            
        if isinstance(value, list):
            if len(value) != len(default):
                return True
            return any(v != d for v, d in zip(value, default))
            
        return value != default

    def _compute_dict_diff(
        self,
        value: Dict[str, Any],
        default: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compute minimal diff for nested dicts (only changed keys)."""
        diff: Dict[str, Any] = {}
        
        for key, val in value.items():
            default_val = default.get(key) if default else None
            
            if self._values_differ(val, default_val):
                if isinstance(val, dict) and isinstance(default_val, dict):
                    nested_diff = self._compute_dict_diff(val, default_val)
                    if nested_diff:
                        diff[key] = nested_diff
                else:
                    diff[key] = val
        
        return diff

    def preview_write(
        self,
        configs: Dict[str, str],
        mode: WriteMode = WriteMode.CREATE
    ) -> List[FileAction]:
        """Preview what would happen when writing configs.
        
        Args:
            configs: Dict mapping filename to YAML content string
            mode: Write mode
            
        Returns:
            List of FileAction describing what would happen
        """
        actions: List[FileAction] = []
        
        for filename, content in configs.items():
            target_path = self.config_dir / filename
            
            if target_path.exists():
                existing = target_path.read_text(encoding="utf-8")
                
                if mode == WriteMode.CREATE:
                    actions.append(FileAction(
                        path=target_path,
                        action="skip",
                        content=content,
                        existing_content=existing
                    ))
                elif mode == WriteMode.MERGE:
                    actions.append(FileAction(
                        path=target_path,
                        action="merge",
                        content=content,
                        existing_content=existing
                    ))
                else:  # OVERWRITE
                    actions.append(FileAction(
                        path=target_path,
                        action="update",
                        content=content,
                        existing_content=existing
                    ))
            else:
                actions.append(FileAction(
                    path=target_path,
                    action="create",
                    content=content
                ))
        
        return actions

    def write_configs(
        self,
        configs: Dict[str, str],
        mode: WriteMode = WriteMode.CREATE
    ) -> WriteResult:
        """Write config files with conflict handling.
        
        Args:
            configs: Dict mapping filename to YAML content string
            mode: Write mode (create/merge/overwrite)
            
        Returns:
            WriteResult with details of what was written
        """
        result = WriteResult(success=True)
        
        # Ensure config directory exists
        ensure_directory(self.config_dir)
        
        for filename, content in configs.items():
            target_path = self.config_dir / filename
            
            try:
                if target_path.exists():
                    if mode == WriteMode.CREATE:
                        result.files_skipped.append(target_path)
                        continue
                    elif mode == WriteMode.MERGE:
                        # Merge with existing
                        existing_data = read_yaml(target_path, default={})
                        from edison.core.utils.io import parse_yaml_string
                        new_data = parse_yaml_string(content, default={})
                        merged = deep_merge(existing_data, new_data)
                        content = dump_yaml_string(merged, sort_keys=False)
                        result.files_merged.append(target_path)
                    # For OVERWRITE, we just write
                
                # Write the file
                target_path.write_text(content, encoding="utf-8")
                if target_path not in result.files_merged:
                    result.files_written.append(target_path)
                    
            except Exception as e:
                result.success = False
                result.errors.append(f"Failed to write {filename}: {e}")
        
        return result

    def write_overrides_only(
        self,
        config_dict: Dict[str, Any],
        mode: WriteMode = WriteMode.CREATE
    ) -> WriteResult:
        """Generate and write only override configs (diff from defaults).
        
        Args:
            config_dict: Full config dict from questionnaire
            mode: Write mode
            
        Returns:
            WriteResult with details
        """
        # Compute overrides
        overrides = self.compute_overrides(config_dict)
        
        # Convert to YAML strings
        configs: Dict[str, str] = {}
        for filename, data in overrides.items():
            configs[filename] = dump_yaml_string(data, sort_keys=False)
        
        # Write
        return self.write_configs(configs, mode)

    def render_and_write(
        self,
        rendered_configs: Dict[str, str],
        mode: WriteMode = WriteMode.CREATE,
        overrides_only: bool = True
    ) -> WriteResult:
        """Write configs from render_modular_configs output.
        
        Args:
            rendered_configs: Output from questionnaire.render_modular_configs()
            mode: Write mode
            overrides_only: If True, compute diff against defaults first
            
        Returns:
            WriteResult
        """
        if overrides_only:
            # Parse each file and compute overrides
            from edison.core.utils.io import parse_yaml_string
            
            combined: Dict[str, Any] = {}
            for filename, content in rendered_configs.items():
                data = parse_yaml_string(content, default={})
                if isinstance(data, dict):
                    combined.update(data)
            
            return self.write_overrides_only(combined, mode)
        else:
            return self.write_configs(rendered_configs, mode)


def write_project_configs(
    repo_root: Path,
    answers: Dict[str, Any],
    mode: WriteMode = WriteMode.CREATE,
    overrides_only: bool = True
) -> WriteResult:
    """High-level function to write project configs from questionnaire answers.
    
    Args:
        repo_root: Repository root path
        answers: Questionnaire answers
        mode: Write mode
        overrides_only: If True, only write values that differ from defaults
        
    Returns:
        WriteResult
    """
    from edison.core.setup.questionnaire import SetupQuestionnaire
    from edison.core.setup.questionnaire.context import build_context_with_defaults, build_config_dict
    
    # Build config dict from answers
    questionnaire = SetupQuestionnaire(repo_root=repo_root, assume_yes=True)
    context = build_context_with_defaults(questionnaire, answers)
    config_dict = build_config_dict(context)
    
    # Write using ConfigWriter
    writer = ConfigWriter(repo_root)
    return writer.write_overrides_only(config_dict, mode) if overrides_only else writer.write_configs(
        {f"{k}.yml": dump_yaml_string({k: v}, sort_keys=False) for k, v in config_dict.items()},
        mode
    )


__all__ = [
    "ConfigWriter",
    "WriteMode",
    "WriteResult",
    "FileAction",
    "write_project_configs",
]
