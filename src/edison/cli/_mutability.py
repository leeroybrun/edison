from __future__ import annotations

import argparse


def is_mutating_invocation(command_name: str, args: argparse.Namespace) -> bool:
    """Best-effort classification of whether a CLI invocation mutates project state.

    This is used by worktree enforcement and hooks:
    - Read-only invocations should be allowed from the primary checkout.
    - Mutating invocations should be blocked unless run inside the session worktree.
    """
    # Standard pattern: many commands expose a dry-run mode.
    if bool(getattr(args, "dry_run", False)):
        return False

    # session status: read-only unless transitioning.
    if command_name == "session status":
        return bool(getattr(args, "status", None))

    # task status: read-only unless transitioning.
    if command_name == "task status":
        return bool(getattr(args, "status", None))

    # task ready: listing is read-only; legacy completion (with record_id) is mutating.
    if command_name == "task ready":
        return bool(getattr(args, "record_id", None))

    # task done: completes a task (wip->done).
    if command_name == "task done":
        return True

    # task split: read-only on dry-run, mutating otherwise.
    if command_name == "task split":
        return True

    # qa validate: roster-only/dry-run are read-only. Execution writes round reports.
    if command_name == "qa validate":
        return bool(getattr(args, "execute", False))

    # qa round: prepare/summarize/set-status all write round artifacts or QA history.
    if command_name == "qa round":
        return True

    # qa run: writes evidence.
    if command_name == "qa run":
        return True

    # qa promote: transitions QA state.
    if command_name == "qa promote":
        return True

    # evidence capture: writes snapshot evidence files.
    if command_name == "evidence capture":
        return True

    # evidence context7: template/list are read-only; save writes marker files.
    if command_name == "evidence context7":
        return str(getattr(args, "subcommand", "") or "") == "save"

    # session validate: currently read-only unless explicitly tracking scores.
    if command_name == "session validate":
        return bool(getattr(args, "track_scores", False))

    # session track: only "active" is read-only; others write tracking artifacts.
    if command_name == "session track":
        sub = str(getattr(args, "subcommand", "") or "")
        return sub in {"start", "heartbeat", "complete"}

    # session continuation: show is read-only; set/clear mutate session metadata.
    if command_name == "session continuation":
        sub = str(getattr(args, "subcommand", "") or "")
        return sub in {"set", "clear"}

    # session next / verify are read-only by design.
    if command_name in {"session next", "session verify"}:
        return False

    # Default for known-mutating commands.
    if command_name in {
        "session close",
        "session complete",
        "task claim",
        "task done",
        "task mark-delegated",
        "task link",
        "qa bundle",
    }:
        return True

    # Fallback: if a command exposes a `status` parameter and it is set, treat as mutating.
    if getattr(args, "status", None):
        return True

    # Conservative default: treat unknown commands in the enforcement list as mutating.
    return True


__all__ = ["is_mutating_invocation"]
