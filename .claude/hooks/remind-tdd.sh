#!/usr/bin/env bash
# Edison Hook: remind-tdd
# Type: PreToolUse
# Description: Remind about TDD workflow when editing code
# Blocking: NO

# Fast check: Skip if no Edison session file exists
SESSION_FILE=".project/.session-id"
if [[ ! -f "$SESSION_FILE" ]]; then
  exit 0  # No Edison session, skip hook
fi

# Parse input JSON (with timeout to prevent hanging)
INPUT=$(timeout 1 cat 2>/dev/null || echo '{}')
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool' 2>/dev/null || echo "")
FILE_PATH=$(echo "$INPUT" | jq -r '.args.file_path // ""' 2>/dev/null || echo "")


# Only for Write/Edit tools
if [[ "$TOOL_NAME" != "Write" && "$TOOL_NAME" != "Edit" ]]; then
  exit 0
fi

# Get current task state (don't fail if no session)
TASK_STATE=$(edison task status --current --json 2>/dev/null | jq -r '.state // empty' 2>/dev/null)

# Only remind in configured states
SHOULD_REMIND=false
if [[ "$TASK_STATE" == "wip" ]]; then
  SHOULD_REMIND=true
fi

if [[ "$SHOULD_REMIND" != "true" ]]; then
  exit 0
fi

# Skip test files
if echo "$FILE_PATH" | grep -qE '\.(test|spec)\.(ts|js|tsx|jsx|py)$'; then
  exit 0
fi

# Print reminder (but don't block)
echo ""
echo "💡 TDD Reminder:"
echo "   RED: Write failing test first"
echo "   GREEN: Implement to pass"
echo "   REFACTOR: Clean up"
echo ""
echo "   See: /edison-rules-tdd for details"
echo ""

# Exit 0 = don't block
exit 0