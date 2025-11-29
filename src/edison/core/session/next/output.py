"""CLI output formatting for session next results.

Human-readable output formatting for compute_next results.
"""
from __future__ import annotations

from typing import Any, Dict


def format_human_readable(payload: Dict[str, Any]) -> str:
    """Format compute_next payload as human-readable output.

    Args:
        payload: Result from compute_next()

    Returns:
        Formatted string for terminal output
    """
    lines = []
    lines.append(f"═══ Session {payload['sessionId']} – Next Steps ═══\n")

    # Show applicable rules FIRST (proactive, not just at enforcement)
    if payload.get("rulesEngine"):
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
    lines.append(f"🎯 RECOMMENDED ACTIONS ({len(payload.get('actions', []))} total):\n")
    for i, a in enumerate(payload.get("actions", []), 1):
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
            lines.append(f"      Total blocking: {roster.get('totalBlocking', 0)} | Max concurrent: {roster.get('maxConcurrent', 5)}")

            if roster.get("alwaysRequired"):
                lines.append(f"\n      ✅ Always Required ({len(roster['alwaysRequired'])} validators):")
                for v in roster["alwaysRequired"]:
                    lines.append(f"         - {v['id']} (model: {v['model']}, role: {v['zenRole']})")

            if roster.get("triggeredBlocking"):
                lines.append(f"\n      ⚠️  Triggered Blocking ({len(roster['triggeredBlocking'])} validators):")
                for v in roster["triggeredBlocking"]:
                    method_icon = "🎯" if v.get("detectionMethod") == "git-diff" else "📄"
                    lines.append(f"         {method_icon} {v['id']} (model: {v['model']}, role: {v['zenRole']})")
                    lines.append(f"           Reason: {v['reason']}")

            if roster.get("triggeredOptional"):
                lines.append(f"\n      💡 Triggered Optional ({len(roster['triggeredOptional'])} validators):")
                for v in roster["triggeredOptional"]:
                    method_icon = "🎯" if v.get("detectionMethod") == "git-diff" else "📄"
                    lines.append(f"         {method_icon} {v['id']} (model: {v['model']}, role: {v['zenRole']})")

            if roster.get("decisionPoints"):
                lines.append(f"\n      🤔 Decision Points:")
                for dp in roster["decisionPoints"]:
                    lines.append(f"         - {dp}")

        # Show delegation details if present
        if a.get("delegationDetails"):
            details = a["delegationDetails"]
            if details.get("suggested"):
                lines.append(f"\n   🔧 DELEGATION SUGGESTION:")
                lines.append(f"      Model: {details.get('model')} | Role: {details.get('zenRole')}")
                lines.append(f"      Interface: {details.get('interface')}")
                if details.get("reasoning"):
                    lines.append(f"      Reasoning:")
                    for r in details["reasoning"]:
                        lines.append(f"         - {r}")

        # Show related tasks if present
        if a.get("relatedTasks"):
            related = a["relatedTasks"]
            if related:
                lines.append(f"\n   🔗 RELATED TASKS IN SESSION:")
                for rel in related[:3]:  # Show max 3
                    lines.append(f"      - {rel['relationship'].upper()}: {rel['taskId']} (task: {rel['taskStatus']}, qa: {rel['qaStatus']})")
                    lines.append(f"        {rel['note']}")

        lines.append("")  # Blank line between actions

    # Show blockers
    if payload.get("blockers"):
        lines.append("🚫 BLOCKERS:")
        for b in payload["blockers"]:
            lines.append(f"   - {b['recordId']}: {b['message']}")
            if b.get("fixCmd"):
                lines.append(f"     Fix: {' '.join(b['fixCmd'])}")
        lines.append("")

    # Show missing reports
    if payload.get("reportsMissing"):
        lines.append("⚠️  MISSING REPORTS:")
        for r in payload["reportsMissing"]:
            lines.append(f"   - Task {r['taskId']}: Missing {r['type']} report")
            if r.get("validatorId"):
                lines.append(f"     Validator: {r['validatorId']}")
            if r.get("packages"):
                lines.append(f"     Packages: {', '.join(r['packages'])}")
            if r.get("suggested"):
                lines.append(f"     Suggested fix:")
                for s in r["suggested"]:
                    lines.append(f"       - {s}")
        lines.append("")

    # Show recommendations
    if payload.get("recommendations"):
        lines.append("💡 RECOMMENDATIONS:")
        for rec in payload["recommendations"]:
            lines.append(f"   - {rec}")
        lines.append("")

    # Show follow-ups plan
    if payload.get("followUpsPlan"):
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

    lines.append("═══ End of Next Steps ═══")

    return "\n".join(lines)
