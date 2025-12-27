#!/usr/bin/env bash
# Edison Hook: session-cleanup
# Type: SessionEnd
# Description: Cleanup session resources

# Fast check: Skip if no Edison session file exists
SESSION_FILE=".project/.session-id"
if [[ ! -f "$SESSION_FILE" ]]; then
  exit 0  # No Edison session, skip hook
fi

echo "👋 Edison Session Ending..."

# Cleanup operations
SESSION_ID=$(cat "$SESSION_FILE" 2>/dev/null | head -1 || echo "")

_edison_audit_event() {
  # Fail-open: audit must never break hooks.
  local event="$1"
  shift || true
  edison audit event "$event" \
    --repo-root "$PWD" \
    --session "$SESSION_ID" \
    --field "hook_id=session-cleanup" \
    --field "hook_type=SessionEnd" \
    "$@" 2>/dev/null || true
}

_edison_audit_event "hook.session-cleanup.start"

_edison_audit_event "hook.session-cleanup.save-logs.requested"


_edison_audit_event "hook.session-cleanup.end" --field "save_logs=True"

exit 0