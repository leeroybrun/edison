#!/usr/bin/env bash
# Edison Hook: compaction-reminder
# Type: PreCompact
# Description: Remind agent to re-read constitution after context compaction
#
# This hook is triggered automatically by Claude Code BEFORE context compaction.
# It reminds the agent to re-read its constitution after compaction completes.

# Emit a minimal, deterministic context refresher.
command -v edison >/dev/null 2>&1 && edison session context 2>/dev/null || true



# Configuration from hooks.yaml
ROLE="agents"

MESSAGE_TEMPLATE="⚠️ Context compacted. Re-read your constitution at: constitutions/{ROLE}.md"
NOTIFY="True"

# Expand {ROLE} placeholder in message template
MESSAGE="${MESSAGE_TEMPLATE//\{ROLE\}/$ROLE}"

# Output reminder (Claude Code will inject this into context)
if [ "$NOTIFY" = "true" ] || [ "$NOTIFY" = "True" ]; then
    echo "$MESSAGE"
fi

exit 0