#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT_REAL="$(git rev-parse --show-toplevel)"
SCRIPTS_ROOT="$REPO_ROOT_REAL/.edison/core/scripts/recovery"

tmprepo=$(mktemp -d)
trap 'rm -rf "$tmprepo"' EXIT
cd "$tmprepo"
git init -q

# Minimal structure expected by scripts
mkdir -p .edison/core/scripts/validators
cat > .edison/core/scripts/validators/validate <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
echo "[stub] validate $@" >&2
exit 0
EOS
chmod +x .edison/core/scripts/validators/validate

mkdir -p .project/qa/validation-evidence
mkdir -p .project/sessions/wip
echo '{}' > .project/sessions/wip/test-session-123.json
echo 'name: edison-test' > edison.yaml
mkdir -p .edison/core
mkdir -p .edison/packs
mkdir -p node_modules

# Prepare validation evidence: last round = 1
TASK_ID="test-task-abc"
mkdir -p ".project/qa/validation-evidence/${TASK_ID}/round-1"

# Test 1: recover-failed-validation resumes from round 2 and calls stub
set -e
"$SCRIPTS_ROOT/recover-failed-validation.sh" "$TASK_ID" 2>err.log 1>out.log
grep -q "Resuming validation from round 2" out.log || { echo "❌ recover-failed-validation did not announce round 2"; exit 1; }

# Test 2: recover-stuck-session finds session and prints
out=$("$SCRIPTS_ROOT/recover-stuck-session.sh" test-session-123 2>&1)
echo "$out" | grep -q "Recovering session: test-session-123" || { echo "❌ recover-stuck-session did not print expected line"; exit 1; }

# Test 3: recover-partial-split prints target id
out=$("$SCRIPTS_ROOT/recover-partial-split.sh" "$TASK_ID" 2>&1)
echo "$out" | grep -q "Recovering partial split for: ${TASK_ID}" || { echo "❌ recover-partial-split did not print expected line"; exit 1; }

# Test 4: health-check succeeds
"$SCRIPTS_ROOT/health-check.sh" >/dev/null

echo "✅ Error recovery tests passed"
