"""Edison core Python library package.

Exposes helpers consumed by repository-level tests. Minimal surface for W1-G1.
"""

from types import ModuleType

# Re-export exceptions module
from . import exceptions  # noqa: F401

# Create a compatibility shim for cli_utils that imports from the new locations
# This allows existing code to use `from edison.core import cli_utils` while
# we migrate to the split modules in edison.core.utils
_cli_utils = ModuleType("cli_utils")

# Import from the new split locations
from .utils.cli_errors import json_output, cli_error, run_cli
from .utils.subprocess import (
    run_command,
    run_git_command,
    run_db_command,
    run_ci_command_from_string,
    expand_shell_pipeline,
)

# Populate the shim module
_cli_utils.json_output = json_output
_cli_utils.cli_error = cli_error
_cli_utils.run_cli = run_cli
_cli_utils.run_command = run_command
_cli_utils.run_git_command = run_git_command
_cli_utils.run_db_command = run_db_command
_cli_utils.run_ci_command_from_string = run_ci_command_from_string
_cli_utils.expand_shell_pipeline = expand_shell_pipeline

# Make it available as cli_utils
cli_utils = _cli_utils

__all__ = ["cli_utils", "exceptions"]

