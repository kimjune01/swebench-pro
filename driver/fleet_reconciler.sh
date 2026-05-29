#!/bin/bash
# fleet_reconciler.sh — single-knob fleet scaling via desired-state file.
#
# Reads runs/scored/fleet_state (key=value) every WATCHDOG_INTERVAL seconds and
# reconciles actual fleet (count of /tmp/coord*.env + coordinator alive) to desired.
#
# State file format:
#   desired_boxes=N         # target box count (1..8)
#   mode=graceful|force     # how to handle scale-down
#
# Single-knob operator UX:
#   bash driver/scale_fleet.sh 4          # → writes desired_boxes=4 mode=graceful
#   bash driver/scale_fleet.sh 2 --force  # → writes desired_boxes=2 mode=force
# The reconciler picks it up on next poll and converges.
#
# Replaces the old coordinator_watchdog.sh (also restarts dead coord). Does NOT
# touch the inner harness. Drain logic delegates to drain_boxes.sh (existing).

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

STATE_FILE="runs/scored/fleet_state"
LOG="runs/scored/reconciler.log"
COORD_LOG="runs/scored/coordinator-resurrect.log"
INTERVAL="${WATCHDOG_INTERVAL:-30}"
SETTLE_AFTER_RESTART="${SETTLE:-20}"   # seconds after a coordinator restart before next reconcile

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG" >&2; }

read_state() {
  if [ ! -f "$STATE_FILE" ]; then
    DESIRED=$(ls /tmp/coord*.env 2>/dev/null | wc -l | tr -d ' ')
    MODE="graceful"
    return
  fi
  DESIRED=$(grep -E '^desired_boxes=' "$STATE_FILE" | tail -1 | cut -d= -f2 | tr -d ' ')
  MODE=$(grep -E '^mode=' "$STATE_FILE" | tail -1 | cut -d= -f2 | tr -d ' ')
  DESIRED="${DESIRED:-1}"
  MODE="${MODE:-graceful}"
}

count_actual() { ls /tmp/coord*.env 2>/dev/null | wc -l | tr -d ' '; }

is_coord_alive() { pgrep -f "driver/coordinator\.py" > /dev/null; }

start_coord() {
  local n="$1"
  log "  start coordinator --boxes $n --skip-setup"
  AUTH_MODE=subscription nohup python3 -u driver/coordinator.py \
    --boxes "$n" --skip-setup \
    --eligible runs/audit/eligible.txt \
    >> "$COORD_LOG" 2>&1 &
  log "  spawned coord pid=$!"
}

terminate_box() {
  local name="$1"; local envf="/tmp/${name}.env"
  [ -f "$envf" ] || return 0
  (. "$envf"
   [ -n "${IID:-}" ] && aws ec2 terminate-instances --instance-ids "$IID" --region "$REGION" >/dev/null 2>&1
   [ -n "${SG:-}"  ] && aws ec2 delete-security-group --group-id  "$SG"  --region "$REGION" 2>/dev/null
   [ -n "${KEY:-}" ] && aws ec2 delete-key-pair --key-name "$KEY" --region "$REGION" 2>/dev/null
   log "    terminated $name (IID=${IID:-?})"
  )
  rm -f "$envf"
}

drain_in_flight() {
  pgrep -f "drain_boxes\.sh" > /dev/null
}

reconcile() {
  read_state
  local actual; actual=$(count_actual)

  # Case A: counts match → just ensure coordinator alive
  if [ "$DESIRED" = "$actual" ]; then
    if ! is_coord_alive; then
      log "match (desired=actual=$DESIRED) but coord DOWN — restart"
      start_coord "$DESIRED"
      sleep "$SETTLE_AFTER_RESTART"
    fi
    return
  fi

  # Case B: scale UP (lossy — restart at new size)
  if [ "$DESIRED" -gt "$actual" ]; then
    log "scale UP: desired=$DESIRED actual=$actual (provision delta + restart coord)"
    local pids=()
    for i in $(seq $((actual + 1)) "$DESIRED"); do
      log "  provisioning coord$i"
      AUTH_MODE=subscription bash driver/run_fleet.sh setup-box "coord$i" \
        > "/tmp/setup-coord${i}.log" 2>&1 &
      pids+=($!)
    done
    for p in "${pids[@]}"; do wait "$p"; done
    local new_actual; new_actual=$(count_actual)
    log "  provision result: $new_actual of $DESIRED boxes ready"
    if [ "$new_actual" -lt "$DESIRED" ]; then
      log "  WARN: short of target; will restart coord at $new_actual"
      DESIRED="$new_actual"   # don't try to drive coord at impossible width this cycle
    fi
    log "  killing coord for restart at --boxes $DESIRED"
    pkill -f "driver/coordinator\.py" || true
    sleep 3
    start_coord "$DESIRED"
    sleep "$SETTLE_AFTER_RESTART"
    return
  fi

  # Case C: scale DOWN
  if [ "$DESIRED" -lt "$actual" ]; then
    local victims=()
    for i in $(seq $((DESIRED + 1)) "$actual"); do victims+=("coord$i"); done

    if [ "$MODE" = "force" ]; then
      log "scale DOWN FORCE: desired=$DESIRED actual=$actual — killing coord + terminating ${victims[*]}"
      pkill -f "driver/coordinator\.py" || true
      sleep 2
      local pids=()
      for v in "${victims[@]}"; do terminate_box "$v" & pids+=($!); done
      for p in "${pids[@]}"; do wait "$p"; done
      sleep 2
      start_coord "$DESIRED"
      sleep "$SETTLE_AFTER_RESTART"
    else
      # graceful: if drain not already running, spawn one for the tail
      if drain_in_flight; then
        log "scale DOWN GRACEFUL: drain in progress, waiting"
      else
        log "scale DOWN GRACEFUL: desired=$DESIRED actual=$actual — arming drain ${victims[*]}"
        nohup bash driver/drain_boxes.sh "${victims[@]}" > runs/scored/drain-boot.log 2>&1 &
        # NOTE: coordinator stays alive with --boxes <old>. Victims' workers retire when their
        # env files disappear (box-fault path → setup_box retries fail because drain whacks
        # them → worker exits). Coordinator continues with the surviving workers.
      fi
    fi
    return
  fi
}

log "fleet_reconciler start (pid=$$, interval=${INTERVAL}s, state=$STATE_FILE)"
log "policy: reconcile actual fleet to desired_boxes; scale-up always restart-lossy;"
log "        scale-down respects mode (graceful=drain | force=kill+terminate)"

while true; do
  reconcile
  sleep "$INTERVAL"
done
