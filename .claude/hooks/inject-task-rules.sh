#!/usr/bin/env bash
# Edison Hook: inject-task-rules
# Type: UserPromptSubmit
# Description: Inject rules for current task state
# Blocking: NO (always exit 0)

# Fast check: Skip if no Edison session file exists
SESSION_FILE=".project/.session-id"
if [[ ! -f "$SESSION_FILE" ]]; then
  exit 0  # No Edison session, skip hook
fi

# Parse input JSON (with timeout to prevent hanging)
INPUT=$(timeout 1 cat 2>/dev/null || echo '{}')
FILE_PATHS=$(echo "$INPUT" | jq -r '.file_paths // [] | .[]' 2>/dev/null || echo "")

# Check if any file matches our patterns using bash glob matching
RELEVANT=false
for file in $FILE_PATHS; do
  case "$file" in
*|*.___never_match___)
      RELEVANT=true
      break
      ;;
  esac
done

if [[ "$RELEVANT" != "true" ]]; then
  exit 0
fi

# Get current task state (don't fail if no session)
TASK_STATE=$(edison task status --current --json 2>/dev/null | jq -r '.state // empty' 2>/dev/null)
if [[ -z "$TASK_STATE" ]]; then
  exit 0  # No active task, nothing to inject
fi

# Inject rules for current state
if [[ "$TASK_STATE" == "todo" ]]; then
  echo ""
  echo "## Edison Rules (todo state)"
  echo ""
fi
if [[ "$TASK_STATE" == "wip" ]]; then
  echo ""
  echo "## Edison Rules (wip state)"
  echo ""
  RULE_CONTENT=$(edison rules get tdd-workflow --brief 2>/dev/null || echo "")
  if [[ -n "$RULE_CONTENT" ]]; then
    echo "### tdd-workflow"
    echo "$RULE_CONTENT"
    echo ""
  fi
  RULE_CONTENT=$(edison rules get testing-patterns --brief 2>/dev/null || echo "")
  if [[ -n "$RULE_CONTENT" ]]; then
    echo "### testing-patterns"
    echo "$RULE_CONTENT"
    echo ""
  fi
fi
if [[ "$TASK_STATE" == "done" ]]; then
  echo ""
  echo "## Edison Rules (done state)"
  echo ""
  RULE_CONTENT=$(edison rules get validation-checklist --brief 2>/dev/null || echo "")
  if [[ -n "$RULE_CONTENT" ]]; then
    echo "### validation-checklist"
    echo "$RULE_CONTENT"
    echo ""
  fi
fi
if [[ "$TASK_STATE" == "validated" ]]; then
  echo ""
  echo "## Edison Rules (validated state)"
  echo ""
fi

exit 0