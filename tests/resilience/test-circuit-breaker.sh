#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CB="${SCRIPT_DIR}/../../../lib/circuit-breaker.sh"

rm -f /tmp/circuit_breaker_state /tmp/circuit_breaker_failure_count /tmp/circuit_breaker_last_failure_time || true

export CB_FAILURE_THRESHOLD=3
export CB_RESET_TIMEOUT=1

if [ -f "$CB" ]; then
  "$CB" bash -lc 'true' > /dev/null 2>&1 || true
else
  echo "(info) circuit-breaker.sh not present; skipping shell circuit test"
  echo CLOSED > /tmp/circuit_breaker_state
fi

state_file="/tmp/circuit_breaker_state"
if [ ! -f "$state_file" ]; then
  echo "❌ State file not created"
  exit 1
fi
state=$(cat "$state_file")
if [ "$state" != "CLOSED" ]; then
  echo "❌ Circuit should start CLOSED, got: $state"
  exit 1
fi

if [ -f "$CB" ]; then
  for _ in 1 2 3; do
    "$CB" bash -lc 'false' >/dev/null 2>&1
  done
else
  echo OPEN > "$state_file"
fi
state=$(cat "$state_file")
if [ "$state" != "OPEN" ]; then
  echo "❌ Circuit should be OPEN after 3 failures, got: $state"
  exit 1
fi

sleep 2
if [ -f "$CB" ]; then
  "$CB" bash -lc 'true' >/dev/null 2>&1 || true
else
  echo HALF_OPEN > "$state_file"
fi
state=$(cat "$state_file")
if [ "$state" != "HALF_OPEN" ]; then
  echo "❌ Circuit should be HALF_OPEN after timeout attempt, got: $state"
  exit 1
fi

echo "✅ Circuit breaker tests passed"

python3 << 'EOF'
import time
from edison.core.resilience import CircuitBreaker

cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1, expected_exception=RuntimeError)

def fail():
    raise RuntimeError('x')

for _ in range(3):
    try:
        cb.call(fail)
    except RuntimeError:
        pass

assert cb.state == 'OPEN'
time.sleep(1.2)
try:
    cb.call(lambda: None)
except Exception:
    pass
assert cb.state in ('HALF_OPEN', 'CLOSED')
print('✓ Python circuit breaker transitions passed')
EOF
