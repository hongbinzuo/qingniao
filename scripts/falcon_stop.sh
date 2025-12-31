#!/usr/bin/env bash
set -euo pipefail
PIDFILE=trading_signals/.falcon.pid
if [[ -f "$PIDFILE" ]];
then
  PID=$(cat "$PIDFILE")
  if ps -p "$PID" > /dev/null 2>&1; then
    kill "$PID" || true
    echo "Falcon stopped (pid=$PID)."
  else
    echo "Falcon not running (stale pid=$PID)."
  fi
  rm -f "$PIDFILE"
else
  echo "No PID file; Falcon may not be running."
fi

