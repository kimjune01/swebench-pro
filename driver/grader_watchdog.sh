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
HEARTBEAT_LEDGER="runs/scored/box_heartbeat.jsonl"
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
        # heartbeat: emit one line with box-wide load average even when no containers exist
        LOAD1=$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo 0)
        echo "HEARTBEAT load1=${LOAD1}"
        # Reap orphans: pro_run is serial per box, so only the newest container is the active grader.
        # Anything older is a leaked grader from a prior run that never cleaned up. Kill them first.
        # docker ps sorts newest-first by default; skip the first, kill the rest.
        ALL_CIDS=$(docker ps --format '{{.ID}}')
        ORPHAN_CIDS=$(echo "$ALL_CIDS" | tail -n +2)
        for OCID in $ORPHAN_CIDS; do
          OCNAME=$(docker inspect -f '{{.Name}}' "$OCID" 2>/dev/null | sed 's|^/||')
          OSTARTED=$(docker inspect -f '{{.State.StartedAt}}' "$OCID" 2>/dev/null)
          OSTART_SEC=$(date -d "$OSTARTED" +%s 2>/dev/null || echo 0)
          OUPMIN=$(( (NOW - OSTART_SEC) / 60 ))
          echo "REAP_ORPHAN cid=$OCID name=$OCNAME up=${OUPMIN}m"
          docker kill "$OCID" >/dev/null 2>&1
        done
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
      TS=$(date -u +%FT%TZ)
      # Collect this poll's data per box for heartbeat record
      HB_LOAD=""
      HB_CONTAINERS="[]"
      HB_BUF=""
      echo "$OUT" | while IFS= read -r line; do
        log "$name: $line"
        # Structured ledger of kills (for retry_grader_kills.sh to match against run.jsonl)
        if [[ "$line" == KILL* ]]; then
          CID=$(echo "$line"  | sed -nE 's/.*cid=([^ ]+).*/\1/p')
          CNAME=$(echo "$line"| sed -nE 's/.*name=([^ ]+).*/\1/p')
          UPMIN=$(echo "$line"| sed -nE 's/.*up=([0-9]+)m.*/\1/p')
          printf '{"ts":"%s","box":"%s","cid":"%s","container":"%s","uptime_min":%s}\n' \
            "$TS" "$name" "$CID" "$CNAME" "${UPMIN:-0}" >> "$KILL_LEDGER"
        fi
      done
      # Heartbeat record: parse OUT via stdin, append one JSON line per box per poll
      printf '%s\n' "$OUT" | TS="$TS" BOX="$name" python3 -c '
import sys, json, re, os
ts, box = os.environ["TS"], os.environ["BOX"]
load = 0.0
containers = []
for line in sys.stdin:
    line = line.rstrip()
    m = re.match(r"HEARTBEAT load1=([\d.]+)", line)
    if m:
        load = float(m.group(1)); continue
    m = re.match(r"ASSESS cid=(\S+) name=(\S+) up=(\d+)m cpu=([\d.]+) idle=(\d+)m", line)
    if m:
        containers.append({"cid": m.group(1), "name": m.group(2),
                           "uptime_min": int(m.group(3)),
                           "cpu_pct": float(m.group(4)),
                           "idle_min": int(m.group(5))})
print(json.dumps({"ts": ts, "box": box, "load1": load, "containers": containers}))
' >> "$HEARTBEAT_LEDGER"
    fi
  done
  sleep "$INTERVAL"
done
