#!/bin/bash
# drain_boxes.sh — for each named box, let its current run finish, then permanently
# retire it from the fleet. Does NOT touch the inner harness.
#
# Operator infra (medium-running). Exits cleanly once all named boxes have retired (their
# /tmp/<name>.env files have been gone for the 90s confirmation window with no late
# reprovisions). Sentinel files in /tmp/drain-<name>.fired track which boxes have already
# completed their drain trigger; they're cleaned up on normal exit.
#
# Strategy: poll the ledger; on the box's next completion, terminate its EC2 instance
# + delete /tmp/<name>.env. The coordinator's box-fault path will retry setup_box up to
# its restart_max (default 3); whack any fresh /tmp/<name>.env that appears during the
# retry window. Once setup_box exhausts retries the worker retires gracefully.
#
# Bring it up:
#   nohup bash driver/drain_boxes.sh coord5 coord6 coord7 coord8 \
#     > runs/scored/drain-boot.log 2>&1 &
#
# Cancel: pkill -f drain_boxes.sh; rm -f /tmp/drain-coord*.fired
#   (manual /tmp cleanup needed because abnormal exit doesn't reach the sentinel-cleanup path)
#
# log:    runs/scored/drain.log

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

LEDGER="runs/scored/run.jsonl"
LOG="runs/scored/drain.log"
REGION="us-west-2"

DRAIN_BOXES=("$@")
[ ${#DRAIN_BOXES[@]} -gt 0 ] || { echo "usage: $0 <box> [box ...]" >&2; exit 1; }

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG" >&2; }

terminate_box() {
  local name="$1"
  local envf="/tmp/${name}.env"
  [ -f "$envf" ] || return 0
  (. "$envf" 2>/dev/null
   [ -n "${IID:-}" ] && aws ec2 terminate-instances --instance-ids "$IID" --region "$REGION" >/dev/null 2>&1
   [ -n "${SG:-}"  ] && aws ec2 delete-security-group --group-id  "$SG"  --region "$REGION" 2>/dev/null
   [ -n "${KEY:-}" ] && aws ec2 delete-key-pair       --key-name  "$KEY" --region "$REGION" 2>/dev/null
   log "  terminated $name (IID=${IID:-?})"
  )
  rm -f "$envf"
}

START_OFFSET=$(wc -c < "$LEDGER")
log "drain start: boxes=${DRAIN_BOXES[*]}, ledger_offset=$START_OFFSET"
log "policy: kill on first ledger entry; whack reprovisions until setup_box retries exhaust"

# Sentinel files (bash 3 compatible — no associative arrays)
SENTINEL_DIR="/tmp"
for b in "${DRAIN_BOXES[@]}"; do rm -f "${SENTINEL_DIR}/drain-${b}.fired"; done

fired() { [ -f "${SENTINEL_DIR}/drain-${1}.fired" ]; }
mark_fired() { touch "${SENTINEL_DIR}/drain-${1}.fired"; }

while true; do
  # Phase 1: watch for first completion on each draining box
  CUR_OFFSET=$(wc -c < "$LEDGER")
  if [ "$START_OFFSET" -lt "$CUR_OFFSET" ]; then
    NEW=$(tail -c +$((START_OFFSET + 1)) "$LEDGER")
    for b in "${DRAIN_BOXES[@]}"; do
      if ! fired "$b" && echo "$NEW" | grep -q "\"box\": \"$b\""; then
        log "$b just recorded an instance — initiating drain"
        terminate_box "$b"
        mark_fired "$b"
      fi
    done
    START_OFFSET=$CUR_OFFSET
  fi

  # Phase 2: re-terminate any reprovisioned env files for already-fired boxes
  for b in "${DRAIN_BOXES[@]}"; do
    if fired "$b" && [ -f "/tmp/${b}.env" ]; then
      log "$b reprovisioned by setup_box — re-terminating"
      terminate_box "$b"
    fi
  done

  # Exit: all boxes fired AND none have a fresh env file
  ALL_DOWN=1
  for b in "${DRAIN_BOXES[@]}"; do
    if ! fired "$b" || [ -f "/tmp/${b}.env" ]; then ALL_DOWN=0; break; fi
  done
  if [ "$ALL_DOWN" -eq 1 ]; then
    log "all targets retired; sleeping 90s to confirm no late reprovisions"
    sleep 90
    REGRESS=0
    for b in "${DRAIN_BOXES[@]}"; do
      [ -f "/tmp/${b}.env" ] && { log "  $b regressed (env reappeared); resuming whack"; REGRESS=1; break; }
    done
    if [ "$REGRESS" -eq 0 ]; then
      log "drain complete — ${#DRAIN_BOXES[@]} boxes permanently retired"
      for b in "${DRAIN_BOXES[@]}"; do rm -f "${SENTINEL_DIR}/drain-${b}.fired"; done
      exit 0
    fi
  fi

  sleep 10
done
