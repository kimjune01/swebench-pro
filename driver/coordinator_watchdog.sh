#!/bin/bash
# coordinator_watchdog.sh — restart the coordinator if it dies.
#
# Operator infra. Does not touch the inner harness (coordinator.py / pro_run.py /
# pro_pilot.py / skills). Polls every $INTERVAL seconds; if no coordinator.py
# process is alive, re-launches with --skip-setup against the existing
# /tmp/coord*.env files (so it reuses the already-provisioned boxes instead
# of double-billing EC2).
#
# Bring it up:
#   cd /Users/junekim/Documents/swebench-pro
#   nohup bash driver/coordinator_watchdog.sh > runs/scored/watchdog-boot.log 2>&1 &
#
# Tail:  tail -f runs/scored/watchdog.log
# Stop:  pkill -f coordinator_watchdog.sh

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

LOG="runs/scored/watchdog.log"
COORD_LOG="runs/scored/coordinator-resurrect.log"
INTERVAL="${WATCHDOG_INTERVAL:-30}"   # seconds between health checks
BOXES="${WATCHDOG_BOXES:-8}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG" >&2; }

is_coord_alive() {
  # match the script path, exclude grep + this watchdog itself
  ps -axo pid,command | grep -E "driver/coordinator\.py" | grep -v grep | grep -v watchdog > /dev/null
}

log "watchdog start (pid=$$, interval=${INTERVAL}s, boxes=${BOXES})"
log "policy: --skip-setup; reuse /tmp/coord*.env; AUTH_MODE=subscription"

# Sanity: at least one env file must exist or --skip-setup will refuse
if ! ls /tmp/coord*.env >/dev/null 2>&1; then
  log "FATAL: no /tmp/coord*.env files — refusing to start (provision first)"
  exit 1
fi

RESTART_COUNT=0
while true; do
  if ! is_coord_alive; then
    RESTART_COUNT=$((RESTART_COUNT + 1))
    log "coordinator DOWN — restart #${RESTART_COUNT}"
    log "  command: AUTH_MODE=subscription python3 -u driver/coordinator.py --boxes ${BOXES} --skip-setup --eligible runs/audit/eligible.txt"
    AUTH_MODE=subscription nohup python3 -u driver/coordinator.py \
      --boxes "${BOXES}" --skip-setup \
      --eligible runs/audit/eligible.txt \
      >> "$COORD_LOG" 2>&1 &
    NEW_PID=$!
    log "  spawned pid=${NEW_PID}; sleeping 15s before next poll"
    sleep 15
  fi
  sleep "$INTERVAL"
done
