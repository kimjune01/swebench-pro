#!/bin/bash
# grader_watchdog.sh — detect hung Pro graders and force-kill the docker container so the
# worker can move on. Pure operator infra; does NOT touch the inner harness or the grader code.
#
# Detection (all three required, conservative to avoid killing slow-but-progressing graders):
#   - container uptime > AGE_THRESHOLD_MIN     (default: 60 min)
#   - container CPU%    < CPU_THRESHOLD        (default: 1%)
#   - latest grade-output dir mtime idle for > IDLE_THRESHOLD_MIN  (default: 30 min)
#
# Action: docker kill <container>. The eval process dies; pro_run either records a verdict or
# the coordinator sees a transport fault. Either way the worker becomes dispatchable again.
#
# Bring it up:
#   cd /Users/junekim/Documents/swebench-pro
#   nohup bash driver/grader_watchdog.sh > runs/scored/grader_watchdog-boot.log 2>&1 &
#
# Tail:  tail -f runs/scored/grader_watchdog.log

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

LOG="runs/scored/grader_watchdog.log"
KILL_LEDGER="runs/scored/grader_kills.jsonl"
INTERVAL="${GRADER_WATCHDOG_INTERVAL:-300}"
AGE_THRESHOLD_MIN="${GRADER_AGE_MIN:-60}"
CPU_THRESHOLD="${GRADER_CPU_PCT:-1}"
IDLE_THRESHOLD_MIN="${GRADER_IDLE_MIN:-30}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG" >&2; }

check_box() {
  local name="$1"
  local envf="/tmp/${name}.env"
  [ -f "$envf" ] || return
  ( . "$envf"
    local pem="/tmp/${KEY}.pem"
    [ -f "$pem" ] || { echo "MISSING_PEM"; return; }
    # Remote-side assessment + decision. Thresholds passed via inline env on the ssh command line.
    ssh -i "$pem" -o ConnectTimeout=8 -o StrictHostKeyChecking=no ec2-user@${PUBIP} \
      "AGE=$AGE_THRESHOLD_MIN CPU_T=$CPU_THRESHOLD IDLE=$IDLE_THRESHOLD_MIN bash -s" <<'REMOTE' 2>/dev/null
        set -u
        NOW=$(date +%s)
        docker ps --format '{{.ID}} {{.Names}}' | while read CID CNAME; do
          STARTED=$(docker inspect -f '{{.State.StartedAt}}' "$CID" 2>/dev/null)
          [ -z "$STARTED" ] && continue
          START_SEC=$(date -d "$STARTED" +%s 2>/dev/null || echo 0)
          [ "$START_SEC" = "0" ] && continue
          UPMIN=$(( (NOW - START_SEC) / 60 ))

          CPU=$(timeout 5 docker stats --no-stream --format '{{.CPUPerc}}' "$CID" 2>/dev/null | tr -d '%')
          [ -z "$CPU" ] && CPU=0

          LATEST=$(ls -dt ~/swebench-pro/runs/dev/pro_grade_*/ 2>/dev/null | head -1)
          if [ -n "$LATEST" ]; then
            MTIME=$(stat -c %Y "$LATEST" 2>/dev/null || echo 0)
            IDLEMIN=$(( (NOW - MTIME) / 60 ))
          else
            IDLEMIN=0
          fi

          echo "ASSESS cid=$CID name=$CNAME up=${UPMIN}m cpu=${CPU} idle=${IDLEMIN}m"

          # Decision: all three thresholds tripped.
          LOW_CPU=$(awk -v c="$CPU" -v t="$CPU_T" 'BEGIN{print (c+0 < t+0) ? 1 : 0}')
          if [ "$UPMIN" -gt "$AGE" ] && [ "$LOW_CPU" = "1" ] && [ "$IDLEMIN" -gt "$IDLE" ]; then
            echo "KILL cid=$CID name=$CNAME up=${UPMIN}m cpu=${CPU} idle=${IDLEMIN}m"
            docker kill "$CID" >/dev/null 2>&1
          fi
        done
REMOTE
  )
}

log "watchdog start (pid=$$, interval=${INTERVAL}s, age>${AGE_THRESHOLD_MIN}m cpu<${CPU_THRESHOLD}% idle>${IDLE_THRESHOLD_MIN}m)"

while true; do
  for envf in /tmp/coord*.env; do
    [ -f "$envf" ] || continue
    name=$(basename "$envf" .env)
    OUT=$(check_box "$name")
    if [ -n "$OUT" ]; then
      echo "$OUT" | while IFS= read -r line; do
        log "$name: $line"
        # Structured ledger of kills (for retry_grader_kills.sh to match against run.jsonl)
        if [[ "$line" == KILL* ]]; then
          TS=$(date -u +%FT%TZ)
          CID=$(echo "$line"  | sed -nE 's/.*cid=([^ ]+).*/\1/p')
          CNAME=$(echo "$line"| sed -nE 's/.*name=([^ ]+).*/\1/p')
          UPMIN=$(echo "$line"| sed -nE 's/.*up=([0-9]+)m.*/\1/p')
          printf '{"ts":"%s","box":"%s","cid":"%s","container":"%s","uptime_min":%s}\n' \
            "$TS" "$name" "$CID" "$CNAME" "${UPMIN:-0}" >> "$KILL_LEDGER"
        fi
      done
    fi
  done
  sleep "$INTERVAL"
done
