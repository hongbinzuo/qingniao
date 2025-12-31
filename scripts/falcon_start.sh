#!/usr/bin/env bash
set -euo pipefail
mkdir -p trading_signals
LOG=trading_signals/.falcon.log
PIDFILE=trading_signals/.falcon.pid
nohup python3 scripts/falcon.py --daemon > "$LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "Falcon started. PID=$(cat "$PIDFILE"), log=$LOG"

