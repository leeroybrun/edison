"""Validator metadata registry - single source of truth for validator data.

Provides read-only access to validator configuration from YAML.
Uses the flat validator format with engines and waves.

This module is THE single source of truth for all validator metadata.
Other components (EngineRegistry, QAConfig) MUST delegate to this registry
rather than loading their own validator data.

Example:
    registry = ValidatorRegistry()
    validators = registry.get_all()
    roster = registry.build_execution_roster("T001")
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from edison.core.config import ConfigManager
from edison.core.entity.base import EntityId

from ._base import BaseRegistry


@dataclass
class ValidatorMetadata:
    """Validator metadata from configuration."""

    id: str
    name: str
    engine: str
    wave: str
    triggers: list[str] = field(default_factory=list)
    blocking: bool = True
    always_run: bool = False
    fallback_engine: str = ""
    prompt: str = ""
    timeout: int = 300
    context7_required: bool = False
    context7_packages: list[str] = field(default_factory=list)
    focus: list[str] = field(default_factory=list)

    @property
    def pal_role(self) -> str:
        """Get the Pal role for this validator (inferred from ID)."""
        return f"validator-{self.id}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = asdict(self)
        result["pal_role"] = self.pal_role
        return result


def _collect_validators_from_config(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Collect validators from flat configuration format.

    Args:
        config: Full configuration dict

    Returns:
        Dict mapping validator_id to validator config
    """
    validation_cfg = config.get("validation", {}) or {}
    validators = validation_cfg.get("validators", {})
    if isinstance(validators, dict):
        return validators
    return {}


def _collect_validators_grouped(config: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Collect validators grouped by wave.

    Args:
        config: Full configuration dict

    Returns:
        Dict mapping wave to list of validator configs
    """
    all_validators = _collect_validators_from_config(config)

    grouped: dict[str, list[dict[str, Any]]] = {}
    for validator_id, validator_cfg in all_validators.items():
        # Ensure id is set
        validator_cfg = dict(validator_cfg)
        validator_cfg["id"] = validator_id

        wave = validator_cfg.get("wave", "")
        if wave not in grouped:
            grouped[wave] = []
        grouped[wave].append(validator_cfg)

    return grouped


class ValidatorRegistry(BaseRegistry[ValidatorMetadata]):
    """Registry for validator metadata.

    Reads validator configuration from YAML.
    Uses the flat validator format with engines and waves.

    Example:
        registry = ValidatorRegistry(project_root)
        validators = registry.get_all_grouped()
        for wave, validators in validators.items():
            print(f"{wave}: {len(validators)} validators")
    """

    entity_type: str = "validator"

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize validator registry.

        Args:
            project_root: Project root directory. Auto-detected if not provided.
        """
        super().__init__(project_root)
        self._cfg_mgr = ConfigManager(repo_root=self.project_root)
        self._cache: dict[str, ValidatorMetadata] | None = None
        self._grouped_cache: dict[str, list[ValidatorMetadata]] | None = None
        self._default_wave: str | None = None

    @property
    def default_wave(self) -> str:
        """Get the default wave for validators without explicit wave assignment.
        
        Reads from validation.defaults.wave config. Falls back to "comprehensive"
        if not configured.
        """
        if self._default_wave is None:
            config = self._load_config()
            validation_cfg = config.get("validation", {}) or {}
            defaults = validation_cfg.get("defaults", {}) or {}
            self._default_wave = defaults.get("wave", "comprehensive")
        return self._default_wave

    def _load_config(self) -> dict[str, Any]:
        """Load configuration."""
        return self._cfg_mgr.load_config(validate=False)

    def _normalize_entry(self, entry: dict[str, Any]) -> ValidatorMetadata:
        """Convert config entry to ValidatorMetadata.

        Args:
            entry: Raw config entry

        Returns:
            ValidatorMetadata instance
        """
        validator_id = entry.get("id", "")

        triggers_raw = entry.get("triggers", [])
        triggers: list[str] = []
        if isinstance(triggers_raw, list):
            for p in triggers_raw:
                s = str(p).strip()
                if s:
                    triggers.append(s)

        return ValidatorMetadata(
            id=validator_id,
            name=entry.get("name", validator_id.replace("-", " ").title()),
            engine=entry.get("engine", ""),
            wave=entry.get("wave", ""),
            triggers=triggers,
            blocking=entry.get("blocking", True),
            always_run=entry.get("always_run", False),
            fallback_engine=entry.get("fallback_engine", ""),
            prompt=entry.get("prompt", ""),
            timeout=entry.get("timeout", 300),
            context7_required=entry.get("context7_required", False),
            context7_packages=entry.get("context7_packages", []),
            focus=entry.get("focus", []),
        )

    def _load_all(self) -> dict[str, ValidatorMetadata]:
        """Load all validators (cached).

        Returns:
            Dict mapping validator ID to metadata
        """
        if self._cache is not None:
            return self._cache

        config = self._load_config()
        all_validators = _collect_validators_from_config(config)

        self._cache = {}
        for validator_id, entry in all_validators.items():
            # Ensure id is set
            entry_with_id = dict(entry)
            entry_with_id["id"] = validator_id
            metadata = self._normalize_entry(entry_with_id)
            self._cache[metadata.id] = metadata

        return self._cache

    def _load_grouped(self) -> dict[str, list[ValidatorMetadata]]:
        """Load validators grouped by wave (cached).

        Returns:
            Dict mapping wave to list of validators
        """
        if self._grouped_cache is not None:
            return self._grouped_cache

        config = self._load_config()
        grouped = _collect_validators_grouped(config)

        self._grouped_cache = {}
        for wave, entries in grouped.items():
            self._grouped_cache[wave] = []
            for entry in entries:
                metadata = self._normalize_entry(entry)
                self._grouped_cache[wave].append(metadata)

        return self._grouped_cache

    def exists(self, entity_id: EntityId) -> bool:
        """Check if a validator exists.

        Args:
            entity_id: Validator ID

        Returns:
            True if validator exists
        """
        return entity_id in self._load_all()

    def get(self, entity_id: EntityId) -> ValidatorMetadata | None:
        """Get validator metadata by ID.

        Args:
            entity_id: Validator ID

        Returns:
            ValidatorMetadata if found, None otherwise
        """
        return self._load_all().get(entity_id)

    def get_all(self) -> list[ValidatorMetadata]:
        """Get all validator metadata.

        Returns:
            List of all validator metadata, sorted by ID
        """
        return sorted(self._load_all().values(), key=lambda v: v.id)

    def get_all_grouped(self) -> dict[str, list[ValidatorMetadata]]:
        """Get validators grouped by wave.

        Returns:
            Dict mapping wave to validators
        """
        return self._load_grouped()

    def get_by_wave(self, wave: str) -> list[ValidatorMetadata]:
        """Get validators for a specific wave.

        Args:
            wave: Wave name (e.g., "critical", "comprehensive")

        Returns:
            List of validators in that wave
        """
        return self._load_grouped().get(wave, [])

    def list_names(self) -> list[str]:
        """List all validator IDs.

        Returns:
            Sorted list of validator IDs
        """
        return sorted(self._load_all().keys())

    def get_triggered_validators(
        self,
        files: list[str],
        wave: Optional[str] = None,
    ) -> tuple[list[ValidatorMetadata], list[ValidatorMetadata], list[ValidatorMetadata]]:
        """Return (always_run, triggered_blocking, triggered_optional) validators.

        Categorizes validators based on:
        - always_run: Validators that always run regardless of file triggers
        - triggered_blocking: Validators triggered by file patterns that block on failure
        - triggered_optional: Validators triggered by file patterns that don't block

        Args:
            files: List of file paths to match against triggers
            wave: Optional wave filter (only return validators for this wave)

        Returns:
            Tuple of (always_run, triggered_blocking, triggered_optional) validator lists
        """
        from edison.core.utils.patterns import match_patterns

        always_run: list[ValidatorMetadata] = []
        triggered_blocking: list[ValidatorMetadata] = []
        triggered_optional: list[ValidatorMetadata] = []

        for v in self.get_all():
            if wave and v.wave != wave:
                continue
            if v.always_run:
                always_run.append(v)
            elif v.triggers and match_patterns(files, v.triggers):
                if v.blocking:
                    triggered_blocking.append(v)
                else:
                    triggered_optional.append(v)

        return always_run, triggered_blocking, triggered_optional

    def build_execution_roster(
        self,
        task_id: str,
        session_id: Optional[str] = None,
        wave: Optional[str] = None,
        extra_validators: Optional[list[dict[str, str]]] = None,
    ) -> dict[str, Any]:
        """Build execution roster for validation.

        This is THE canonical method for building validator rosters.
        EngineRegistry and CLI commands should delegate to this method.

        Args:
            task_id: Task identifier
            session_id: Optional session context
            wave: Optional wave filter
            extra_validators: Additional validators to include
                Each item: {"id": "validator-id", "wave": "wave-name"}

        Returns:
            Roster dict with:
            - taskId: Task identifier
            - sessionId: Session identifier (if provided)
            - modifiedFiles: List of files triggering validators
            - alwaysRequired: List of always-run validators
            - triggeredBlocking: List of triggered blocking validators
            - triggeredOptional: List of triggered optional validators
            - extraAdded: List of extra validators added
            - skipped: List of validators that didn't match
            - totalBlocking: Count of blocking validators
            - decisionPoints: Suggestions for orchestrator
        """
        from edison.core.context.files import FileContextService

        file_ctx_svc = FileContextService(project_root=self.project_root)
        file_ctx = file_ctx_svc.get_for_task(task_id, session_id)
        files = file_ctx.all_files

        # Get triggered validators
        always_run, triggered_blocking, triggered_optional = self.get_triggered_validators(
            files, wave
        )

        # Build skipped list (validators that didn't trigger)
        skipped: list[dict[str, Any]] = []
        triggered_ids = {v.id for v in always_run + triggered_blocking + triggered_optional}
        for v in self.get_all():
            if wave and v.wave != wave:
                continue
            if v.id not in triggered_ids:
                skipped.append({
                    "id": v.id,
                    "name": v.name,
                    "triggers": v.triggers,
                    "reason": "No matching files",
                })

        # Handle extra validators
        extra_added: list[dict[str, Any]] = []
        if extra_validators:
            for ev in extra_validators:
                v = self.get(ev["id"])
                if v and ev["id"] not in triggered_ids:
                    wave = ev.get("wave", self.default_wave)
                    extra_added.append({
                        "id": v.id,
                        "wave": wave,
                        "name": v.name,
                        "engine": v.engine,
                        "palRole": v.pal_role,
                        "blocking": v.blocking,
                        "reason": f"Added by orchestrator (wave: {wave})",
                        "addedByOrchestrator": True,
                    })

        # Build roster entries with full metadata
        def _to_entry(v: ValidatorMetadata, reason: str = "") -> dict[str, Any]:
            return {
                "id": v.id,
                "name": v.name,
                "engine": v.engine,
                "wave": v.wave,
                "palRole": v.pal_role,
                "priority": 1 if v.always_run else 2,
                "blocking": v.blocking,
                "context7Required": v.context7_required,
                "context7Packages": v.context7_packages,
                "focus": v.focus,
                "triggers": v.triggers,
                "reason": reason or f"{v.wave.title()} validator",
            }

        always_required_entries = [
            _to_entry(v, f"{v.wave.title()} validator (always runs)")
            for v in always_run
        ]
        triggered_blocking_entries = [
            _to_entry(v, self._build_trigger_reason(files, v.triggers))
            for v in triggered_blocking
        ]
        triggered_optional_entries = [
            _to_entry(v, self._build_trigger_reason(files, v.triggers))
            for v in triggered_optional
        ]

        total_blocking = (
            len(always_required_entries)
            + len(triggered_blocking_entries)
        )

        return {
            "taskId": task_id,
            "sessionId": session_id,
            "modifiedFiles": files,
            "alwaysRequired": always_required_entries,
            "triggeredBlocking": triggered_blocking_entries,
            "triggeredOptional": triggered_optional_entries,
            "extraAdded": extra_added,
            "skipped": skipped,
            "totalBlocking": total_blocking,
            "decisionPoints": self._build_decision_points(files, skipped, extra_added),
        }

    def _build_trigger_reason(self, files: list[str], triggers: list[str]) -> str:
        """Build human-readable trigger reason.

        Args:
            files: List of file paths
            triggers: List of trigger patterns

        Returns:
            Formatted reason string
        """
        from edison.core.utils.patterns import match_patterns

        matched = match_patterns(files, triggers)
        if not matched:
            return "Triggered by file patterns"
        reason = f"Triggered by: {', '.join(matched[:3])}"
        if len(matched) > 3:
            reason += f" (+{len(matched) - 3} more)"
        return reason

    def _build_decision_points(
        self,
        modified_files: list[str],
        skipped: list[dict[str, Any]],
        extra_added: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Build decision points for orchestrator guidance.

        Identifies validators that might be relevant but weren't auto-triggered.

        Args:
            modified_files: List of modified file paths
            skipped: List of skipped validators
            extra_added: List of extra validators added

        Returns:
            List of decision point dicts
        """
        points: list[dict[str, Any]] = []
        extra_ids = {e["id"] for e in extra_added}

        # Check for potential React validation in non-.tsx files
        react_skipped = next((s for s in skipped if s["id"] == "react"), None)
        if react_skipped and "react" not in extra_ids:
            js_files = [f for f in modified_files if f.endswith((".js", ".mjs"))]
            if js_files:
                points.append({
                    "validator": "react",
                    "suggestion": "Consider adding 'react' validator",
                    "reason": f"Found .js files that may contain React: {', '.join(js_files[:3])}",
                    "command": "--add-validators react",
                })

        # Check for API validation in non-route files
        api_skipped = next((s for s in skipped if s["id"] == "api"), None)
        if api_skipped and "api" not in extra_ids:
            potential_api = [
                f for f in modified_files
                if any(p in f.lower() for p in ["handler", "service", "client", "fetch"])
            ]
            if potential_api:
                points.append({
                    "validator": "api",
                    "suggestion": "Consider adding 'api' validator",
                    "reason": f"Found files that may contain API logic: {', '.join(potential_api[:3])}",
                    "command": "--add-validators api",
                })

        return points

    def parse_extra_validators(self, specs: list[str]) -> list[dict[str, str]]:
        """Parse [WAVE:]VALIDATOR-ID specs into list of dicts.

        Supports the unified CLI syntax where validators can optionally
        specify a wave prefix.

        Args:
            specs: List of validator specs like "react" or "critical:react"

        Returns:
            List of dicts with 'id' and 'wave' keys

        Examples:
            >>> registry.parse_extra_validators(['critical:react', 'api'])
            [{'id': 'react', 'wave': 'critical'}, {'id': 'api', 'wave': '<default_wave>'}]
        """
        result: list[dict[str, str]] = []
        for spec in specs:
            if ":" in spec:
                wave, vid = spec.split(":", 1)
                result.append({"id": vid, "wave": wave})
            else:
                result.append({"id": spec, "wave": self.default_wave})
        return result

    def build_preset_roster(
        self,
        task_id: str,
        session_id: Optional[str] = None,
        preset_id: Optional[str] = None,
        files: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        """Build execution roster using validation policy presets.

        This method uses the ValidationPolicyResolver to determine which
        validators to run based on preset configuration and file context.
        It's the preferred method for preset-aware validation.

        Args:
            task_id: Task identifier
            session_id: Optional session context
            preset_id: Explicit preset ID (overrides inference)
            files: Optional file list (auto-detected from task if not provided)

        Returns:
            Roster dict with:
            - taskId: Task identifier
            - sessionId: Session identifier (if provided)
            - policy: Resolved validation policy info
            - validators: List of validators for this preset
            - evidenceRequired: List of required evidence files
            - modifiedFiles: List of files triggering validators
        """
        from edison.core.context.files import FileContextService
        from edison.core.qa.policy import ValidationPolicyResolver

        # Get files if not provided
        if files is None:
            file_ctx_svc = FileContextService(project_root=self.project_root)
            file_ctx = file_ctx_svc.get_for_task(task_id, session_id)
            files = file_ctx.all_files

        # Resolve policy
        resolver = ValidationPolicyResolver(project_root=self.project_root)
        policy = resolver.resolve(files=files, preset_id=preset_id, task_id=task_id)

        # Get validator metadata for preset validators
        preset_validators: list[dict[str, Any]] = []
        for vid in policy.preset.validators:
            v = self.get(vid)
            if v:
                preset_validators.append({
                    "id": v.id,
                    "name": v.name,
                    "engine": v.engine,
                    "wave": v.wave,
                    "palRole": v.pal_role,
                    "blocking": v.blocking,
                    "context7Required": v.context7_required,
                    "context7Packages": v.context7_packages,
                    "focus": v.focus,
                })

        return {
            "taskId": task_id,
            "sessionId": session_id,
            "policy": {
                "presetId": policy.preset.id,
                "presetName": policy.preset.name,
                "isEscalated": policy.is_escalated,
                "escalatedFrom": policy.escalated_from,
                "escalationReason": policy.escalation_reason,
            },
            "validators": preset_validators,
            "evidenceRequired": list(policy.preset.evidence_required),
            "modifiedFiles": files,
        }

    def get_validators_for_preset(self, preset_id: str) -> list[ValidatorMetadata]:
        """Get validators defined in a validation preset.

        Args:
            preset_id: Preset identifier (e.g., "quick", "standard")

        Returns:
            List of ValidatorMetadata for validators in the preset
        """
        from edison.core.qa.policy import PresetConfigLoader

        loader = PresetConfigLoader(project_root=self.project_root)
        preset = loader.get_preset(preset_id)
        if not preset:
            return []

        result: list[ValidatorMetadata] = []
        for vid in preset.validators:
            v = self.get(vid)
            if v:
                result.append(v)
        return result


__all__ = ["ValidatorRegistry", "ValidatorMetadata"]
