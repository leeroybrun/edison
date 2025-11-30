"""Setup utilities package for Edison framework.

This module provides core setup functionality including:
- SetupDiscovery: Auto-discovery of packs, validators, agents, orchestrators
- SetupQuestionnaire: Interactive/programmatic setup questionnaire
- ConfigWriter: Unified config file writer with diff-based generation
- configure_project: High-level function for interactive project configuration

These are pure library classes with no CLI dependencies.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from .discovery import SetupDiscovery
from .questionnaire import SetupQuestionnaire
from .writer import ConfigWriter, WriteMode, WriteResult, write_project_configs


def configure_project(
    repo_root: Path,
    interactive: bool = True,
    mode: str = "basic",
    provided_answers: Optional[Dict[str, Any]] = None,
    write_files: bool = False,
    write_mode: WriteMode = WriteMode.CREATE,
    overrides_only: bool = True,
) -> Dict[str, Any]:
    """Configure a project using the setup questionnaire.

    Args:
        repo_root: Path to the project root directory
        interactive: If True, prompt user for input; if False, use defaults
        mode: Setup mode ('basic' or 'advanced')
        provided_answers: Pre-filled answers (bypasses prompting for those keys)
        write_files: If True, write config files to disk
        write_mode: How to handle existing files (CREATE/MERGE/OVERWRITE)
        overrides_only: If True, only write values that differ from defaults

    Returns:
        Dict with 'success' boolean and either 'configs'/'write_result' or 'error' key
    """
    try:
        questionnaire = SetupQuestionnaire(
            repo_root=repo_root,
            assume_yes=not interactive,
        )

        answers = questionnaire.run(
            mode=mode,
            provided_answers=provided_answers,
            assume_yes=not interactive,
        )

        configs = questionnaire.render_modular_configs(answers)

        result: Dict[str, Any] = {
            "success": True,
            "answers": answers,
            "configs": configs,
        }

        # Optionally write files
        if write_files:
            writer = ConfigWriter(repo_root)
            write_result = writer.render_and_write(
                configs, 
                mode=write_mode, 
                overrides_only=overrides_only
            )
            result["write_result"] = write_result
            if not write_result.success:
                result["success"] = False
                result["errors"] = write_result.errors

        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


__all__ = [
    "SetupDiscovery",
    "SetupQuestionnaire",
    "ConfigWriter",
    "WriteMode",
    "WriteResult",
    "configure_project",
    "write_project_configs",
]
