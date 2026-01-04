"""CLI output formatting for session next results.

Human-readable output formatting for compute_next results.
"""

from __future__ import annotations

from typing import Any


def format_human_readable(payload: dict[str, Any]) -> str:
    """Format compute_next payload as human-readable output.

    Args:
        payload: Result from compute_next()

    Returns:
        Formatted string for terminal output
    """
    from edison.core.session._config import get_config

    def _get_output_cfg() -> dict[str, Any]:
        try:
            cfg = get_config()
            section = cfg.section if isinstance(cfg.section, dict) else {}
            nxt = section.get("next", {}) if isinstance(section.get("next"), dict) else {}
            out = nxt.get("output", {}) if isinstance(nxt.get("output"), dict) else {}
            return dict(out)
        except Exception:
            return {}

    def _section_enabled(output_cfg: dict[str, Any], section_id: str, *, default: bool = True) -> bool:
        sections = output_cfg.get("sections")
        if not isinstance(sections, dict):
            return default
        s = sections.get(section_id)
        if not isinstance(s, dict):
            return default
        enabled = s.get("enabled")
        return default if enabled is None else bool(enabled)

    def _format_template(template: str, **kwargs: Any) -> str:
        try:
            return str(template).format(**kwargs)
        except Exception:
            return str(template)

    output_cfg = _get_output_cfg()

    lines = []
    header_template = str(output_cfg.get("headerTemplate") or "═══ Session {sessionId} – Next Steps ═══")
    lines.append(_format_template(header_template, sessionId=payload.get("sessionId", "")))
    lines.append("")

    # Show compact session context (hook-safe payload).
    if _section_enabled(output_cfg, "context", default=True):
        ctx = payload.get("context") or {}
        try:
            from edison.core.session.context_payload import format_session_context_for_next

            lines.extend(format_session_context_for_next(ctx if isinstance(ctx, dict) else {}))
        except Exception:
            # Fail-open: session-next should not crash due to context formatting drift.
            pass

    # Show applicable rules FIRST (proactive, not just at enforcement)
    if _section_enabled(output_cfg, "rules", default=True) and payload.get("rulesEngine"):
        lines.append("📋 APPLICABLE RULES (read FIRST):")

        # Context-aware rules from RulesEngine
        re_summary = payload.get("rulesEngine") or {}
        for ctx_type, rules_list in re_summary.items():
            label = str(ctx_type).upper()
            lines.append(f"\n  Context: {label}")
            for r in rules_list:
                blocking = " (blocking)" if r.get("blocking") else ""
                lines.append(f"    - {r['id']}{blocking}: {r.get('description','')}")
        lines.append("")

    # Show actions with enhanced details
    if _section_enabled(output_cfg, "actions", default=True):
        actions = payload.get("actions", [])
        lines.append(f"🎯 RECOMMENDED ACTIONS ({len(actions) if isinstance(actions, list) else 0} total):")
        lines.append("")

        for i, a in enumerate(actions if isinstance(actions, list) else [], 1):
            if not isinstance(a, dict):
                continue
            cmd = " ".join(a["cmd"]) if a.get("cmd") else a.get("id")
            rid = a.get("recordId", "")
            blocking = "🔴 BLOCKING" if a.get("blocking") else "🟢 OPTIONAL"

            lines.append(f"{i}. [{blocking}] {a['id']} for `{rid}`")
            lines.append(f"   Command: {cmd}")
            if a.get("rationale"):
                lines.append(f"   Why: {a['rationale']}")

            # Show guard preview when available
            guard = a.get("guard") or {}
            if guard:
                status = str(guard.get("status") or "unknown")
                icon = "✅" if status == "allowed" else ("🔒" if status == "blocked" else "⚪")
                g_from = guard.get("from") or "?"
                g_to = guard.get("to") or "?"
                if status == "blocked" and guard.get("message"):
                    lines.append(f"   Guard: {icon} {g_from} → {g_to} ({guard['message']})")
                else:
                    lines.append(f"   Guard: {icon} {g_from} → {g_to}")

            # Show validator roster if present
            if a.get("validatorRoster"):
                roster = a["validatorRoster"]
                detection = roster.get("detectionMethod", "unknown")
                detection_label = "🎯 GIT DIFF" if detection == "git-diff" else "📄 TASK FILES"
                lines.append(f"\n   📊 VALIDATOR ROSTER ({detection_label}):")
                lines.append(
                    f"      Total blocking: {roster.get('totalBlocking', 0)} | Max concurrent: {roster.get('maxConcurrent', 5)}"
                )

                if roster.get("alwaysRequired"):
                    lines.append(f"\n      ✅ Always Required ({len(roster['alwaysRequired'])} validators):")
                    for v in roster["alwaysRequired"]:
                        lines.append(
                            f"         - {v['id']} (engine: {v.get('engine', 'N/A')}, palRole: {v.get('palRole', 'N/A')})"
                        )

                if roster.get("triggeredBlocking"):
                    lines.append(f"\n      ⚠️  Triggered Blocking ({len(roster['triggeredBlocking'])} validators):")
                    for v in roster["triggeredBlocking"]:
                        method_icon = "🎯" if v.get("detectionMethod") == "git-diff" else "📄"
                        lines.append(
                            f"         {method_icon} {v['id']} (engine: {v.get('engine', 'N/A')}, palRole: {v.get('palRole', 'N/A')})"
                        )
                        lines.append(f"           Reason: {v.get('reason', 'N/A')}")

                if roster.get("triggeredOptional"):
                    lines.append(f"\n      💡 Triggered Optional ({len(roster['triggeredOptional'])} validators):")
                    for v in roster["triggeredOptional"]:
                        method_icon = "🎯" if v.get("detectionMethod") == "git-diff" else "📄"
                        lines.append(
                            f"         {method_icon} {v['id']} (engine: {v.get('engine', 'N/A')}, palRole: {v.get('palRole', 'N/A')})"
                        )

                if roster.get("decisionPoints"):
                    lines.append("\n      🤔 Decision Points:")
                    for dp in roster["decisionPoints"]:
                        lines.append(f"         - {dp}")

            # Show delegation details if present
            if a.get("delegationDetails"):
                details = a["delegationDetails"]
                if details.get("suggested"):
                    lines.append("\n   🔧 DELEGATION SUGGESTION:")
                    lines.append(f"      Model: {details.get('model')} | Role: {details.get('palRole')}")
                    lines.append(f"      Interface: {details.get('interface')}")
                    if details.get("reasoning"):
                        lines.append("      Reasoning:")
                        for r in details["reasoning"]:
                            lines.append(f"         - {r}")

            # Show related tasks if present
            if a.get("relatedTasks"):
                related = a["relatedTasks"]
                if related:
                    lines.append("\n   🔗 RELATED TASKS IN SESSION:")
                    for rel in related[:3]:  # Show max 3
                        lines.append(
                            f"      - {rel['relationship'].upper()}: {rel['taskId']} (task: {rel['taskStatus']}, qa: {rel['qaStatus']})"
                        )
                        lines.append(f"        {rel['note']}")

            # Show task start checklist if present
            if a.get("checklist"):
                checklist = a["checklist"]
                items = checklist.get("items", [])
                if items:
                    has_blockers = checklist.get("hasBlockers", False)
                    blocker_icon = "🚫" if has_blockers else "✅"
                    kind = str(checklist.get("kind") or "").strip().lower()
                    label = "CHECKLIST"
                    if kind == "task_start":
                        label = "TASK START CHECKLIST"
                    elif kind == "session_start":
                        label = "SESSION START CHECKLIST"
                    elif kind == "qa_validate_preflight":
                        label = "QA VALIDATE PREFLIGHT CHECKLIST"
                    elif kind == "session_close_preflight":
                        label = "SESSION CLOSE PREFLIGHT CHECKLIST"
                    lines.append(f"\n   {blocker_icon} {label}:")
                    for item in items:
                        severity = item.get("severity", "info")
                        status = item.get("status", "unknown")
                        title = item.get("title", "Unknown")
                        if status == "ok":
                            icon = "✅"
                        elif severity == "blocker":
                            icon = "🚫"
                        elif severity == "warning":
                            icon = "⚠️"
                        else:
                            icon = "ℹ️"
                        lines.append(f"      {icon} {title}")
                        if item.get("rationale") and status != "ok":
                            lines.append(f"         {item['rationale']}")
                        if item.get("suggestedCommands") and status != "ok":
                            for cmd in item["suggestedCommands"][:3]:
                                lines.append(f"         -> {cmd}")

            lines.append("")  # Blank line between actions

    # Show blockers
    if _section_enabled(output_cfg, "blockers", default=True) and payload.get("blockers"):
        lines.append("🚫 BLOCKERS:")
        for b in payload["blockers"]:
            lines.append(f"   - {b['recordId']}: {b['message']}")
            if b.get("fixCmd"):
                lines.append(f"     Fix: {' '.join(b['fixCmd'])}")
        lines.append("")

    # Show missing reports
    if _section_enabled(output_cfg, "reportsMissing", default=True) and payload.get("reportsMissing"):
        lines.append("⚠️  MISSING REPORTS:")
        for r in payload["reportsMissing"]:
            lines.append(f"   - Task {r['taskId']}: Missing {r['type']} report")
            if r.get("validatorId"):
                lines.append(f"     Validator: {r['validatorId']}")
            if r.get("packages"):
                lines.append(f"     Packages (missing): {', '.join(r['packages'])}")
            if r.get("invalidMarkers"):
                invalid = r.get("invalidMarkers") or []
                if isinstance(invalid, list) and invalid:
                    lines.append("     Packages (invalid markers):")
                    for inv in invalid[:5]:
                        if not isinstance(inv, dict):
                            continue
                        pkg = inv.get("package") or "unknown"
                        missing_fields = inv.get("missing_fields") or inv.get("missingFields") or []
                        if isinstance(missing_fields, list) and missing_fields:
                            lines.append(f"       - {pkg} (missing: {', '.join([str(x) for x in missing_fields])})")
                        else:
                            lines.append(f"       - {pkg}")
            if r.get("suggested"):
                lines.append("     Suggested fix:")
                for s in r["suggested"]:
                    lines.append(f"       - {s}")
        lines.append("")

    # Show recommendations
    if _section_enabled(output_cfg, "recommendations", default=True) and payload.get("recommendations"):
        lines.append("💡 RECOMMENDATIONS:")
        for rec in payload["recommendations"]:
            lines.append(f"   - {rec}")
        lines.append("")

    # Show follow-ups plan
    if _section_enabled(output_cfg, "followUpsPlan", default=True) and payload.get("followUpsPlan"):
        lines.append("🧩 FOLLOW-UPS (Claim vs Create-only):\n")
        for plan in payload["followUpsPlan"]:
            lines.append(f"- Parent: `{plan['taskId']}`")
            for s in plan.get("suggestions", []):
                cmd = " ".join(s.get("cmd", []))
                kind = s.get("kind")
                title = s.get("title") or "(untitled)"
                icon = "🔗" if kind == "create-link-claim" else "➕"
                lines.append(f"  {icon} {title}")
                lines.append(f"     {s.get('note')}")
                lines.append(f"     Command: {cmd}")
                if s.get("similar"):
                    lines.append("     Similar existing:")
                    for m in s["similar"]:
                        lines.append(f"       - {m['taskId']} (score {m['score']})")
        lines.append("")

    footer_template = str(output_cfg.get("footerTemplate") or "═══ End of Next Steps ═══")
    lines.append(_format_template(footer_template, sessionId=payload.get("sessionId", "")))

    return "\n".join(lines)
