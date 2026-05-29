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

OFFSET="${WATCHDOG_OFFSET:-0}"           # 0 = coord1-N; 4 = coord5-N (second coordinator)
# Primary (OFFSET=0) uses the unsuffixed log; secondary watchdogs get -off<N> suffix.
if [ "$OFFSET" = "0" ]; then
  LOG="runs/scored/watchdog.log"
  COORD_LOG="runs/scored/coordinator-resurrect.log"
else
  LOG="runs/scored/watchdog-off${OFFSET}.log"
  COORD_LOG="runs/scored/coordinator-resurrect-off${OFFSET}.log"
fi
INTERVAL="${WATCHDOG_INTERVAL:-30}"   # seconds between health checks
BOXES="${WATCHDOG_BOXES:-8}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG" >&2; }

is_coord_alive() {
  # Match this watchdog's specific coordinator by --box-offset value (or its absence for OFFSET=0).
  if [ "$OFFSET" = "0" ]; then
    # primary coordinator: matches coordinator.py but NOT "--box-offset"
    ps -axo pid,command | grep -E "driver/coordinator\.py" | grep -v grep | grep -v watchdog | grep -v -- "--box-offset" > /dev/null
  else
    # secondary coordinator: matches "--box-offset $OFFSET" specifically
    ps -axo pid,command | grep -E "driver/coordinator\.py.*--box-offset[[:space:]]+${OFFSET}\b" | grep -v grep | grep -v watchdog > /dev/null
  fi
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
    OFFSET_FLAG=""
    [ "$OFFSET" != "0" ] && OFFSET_FLAG="--box-offset ${OFFSET}"
    log "  command: AUTH_MODE=subscription python3 -u driver/coordinator.py --boxes ${BOXES} ${OFFSET_FLAG} --skip-setup --eligible runs/audit/eligible.txt"
    AUTH_MODE=subscription nohup python3 -u driver/coordinator.py \
      --boxes "${BOXES}" ${OFFSET_FLAG} --skip-setup \
      --eligible runs/audit/eligible.txt \
      >> "$COORD_LOG" 2>&1 &
    NEW_PID=$!
    log "  spawned pid=${NEW_PID}; sleeping 15s before next poll"
    sleep 15
  fi
  sleep "$INTERVAL"
done
