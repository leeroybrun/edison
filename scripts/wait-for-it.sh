#!/usr/bin/env sh
# wait-for-it.sh - Wait for a service to be available
# Usage: wait-for-it.sh host:port [-t timeout] [-- command args]

set -e

TIMEOUT=15
QUIET=0
HOST=""
PORT=""

usage() {
  cat << EOF
Usage: $0 host:port [-t timeout] [-q] [-- command args]
  -h HOST:PORT         Host and port to wait for
  -t TIMEOUT           Timeout in seconds (default: 15)
  -q                   Quiet mode
  -- COMMAND ARGS      Execute command with args after the test finishes
EOF
  exit 1
}

wait_for() {
  if [ "$QUIET" -ne 1 ]; then
    echo "Waiting for $HOST:$PORT..."
  fi

  for i in $(seq $TIMEOUT); do
    if nc -z "$HOST" "$PORT" > /dev/null 2>&1; then
      if [ "$QUIET" -ne 1 ]; then
        echo "$HOST:$PORT is available"
      fi
      return 0
    fi
    sleep 1
  done

  echo "Timeout occurred after waiting $TIMEOUT seconds for $HOST:$PORT"
  return 1
}

# Parse arguments
while [ $# -gt 0 ]; do
  case "$1" in
    *:* )
      HOST=$(echo "$1" | cut -d: -f1)
      PORT=$(echo "$1" | cut -d: -f2)
      shift
      ;;
    -t)
      TIMEOUT="$2"
      shift 2
      ;;
    -q)
      QUIET=1
      shift
      ;;
    --)
      shift
      break
      ;;
    *)
      usage
      ;;
  esac
done

if [ -z "$HOST" ] || [ -z "$PORT" ]; then
  usage
fi

wait_for

# Execute command if provided
if [ $# -gt 0 ]; then
  exec "$@"
fi
