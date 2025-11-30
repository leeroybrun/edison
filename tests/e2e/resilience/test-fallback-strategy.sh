#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
source "${SCRIPT_DIR}/../../../lib/fallback.sh"
# Sourced script set -euo; relax for negative-path checks
set +e
set +u
set +o pipefail
set -e

# Override availability for tests
model_available() {
  case "$1" in
    primary) return 0 ;;
    secondary) return 0 ;;
    tertiary) return 1 ;;
    none) return 1 ;;
    *) return 1 ;;
  esac
}

# Test 1: Preferred available
chosen=$(fallback_chain "api-route" primary secondary tertiary)
if [ "$chosen" != "primary" ]; then
  echo "❌ Expected primary, got: $chosen"
  exit 1
fi

# Test 2: Preferred unavailable, fallback to secondary
model_available() {
  case "$1" in
    primary) return 1 ;;
    secondary) return 0 ;;
    tertiary) return 0 ;;
    *) return 1 ;;
  esac
}
chosen=$(fallback_chain "api-route" primary secondary tertiary)
if [ "$chosen" != "secondary" ]; then
  echo "❌ Expected secondary, got: $chosen"
  exit 1
fi

# Test 3: None available -> non-zero exit
model_available() { return 1; }
if fallback_chain "api-route" none >/dev/null 2>&1; then
  echo "❌ Expected non-zero when no models available"
  exit 1
fi

echo "✅ Fallback strategy tests passed"
