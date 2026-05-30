#!/usr/bin/env bash
# Health monitor for swebench-pro coordinator run.
# Emits one line on CHANGE only. Quiet runs stay quiet.
# Watches: run.jsonl (verdict tally), box_heartbeat.jsonl (per-box freshness),
#          coordinator-resurrect.log (Traceback/EMPTY/error markers).
#
# Output:   runs/scored/health_monitor.log
# Cadence:  60s
# Stop:     pkill -f health_monitor.sh

set -u
cd "$(dirname "$0")/.."
RUN=runs/scored/run.jsonl
HB=runs/scored/box_heartbeat.jsonl
COORD=runs/scored/coordinator-resurrect.log
OUT=runs/scored/health_monitor.log

prev_run=0
prev_err=0
prev_empty=0
stale_coord1=0
stale_coord2=0
stale_coord3=0
stale_coord4=0

emit() { echo "[$(date -u +%H:%M:%SZ)] $*" >> "$OUT"; }

emit "monitor up (pid $$): watching run.jsonl, heartbeat, coordinator-resurrect.log"

check_box() {
  local box=$1
  local prev_var=stale_$box
  local prev=${!prev_var}
  local last_ts
  last_ts=$(grep "\"box\": \"$box\"" "$HB" 2>/dev/null | tail -1 | python3 -c '
import sys,json,datetime
l=sys.stdin.read().strip()
if l:
  d=json.loads(l)
  t=datetime.datetime.strptime(d["ts"],"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()
  print(int(t))
' 2>/dev/null)
  [ -z "$last_ts" ] && return
  local now age
  now=$(date -u +%s)
  age=$((now - last_ts))
  if [ "$age" -gt 720 ]; then
    if [ "$prev" -eq 0 ]; then
      last_hms=$(python3 -c "import datetime;print(datetime.datetime.utcfromtimestamp($last_ts).strftime('%H:%M:%SZ'))" 2>/dev/null)
      emit "!! $box silent ${age}s (last $last_hms)"
      eval "$prev_var=1"
    fi
  else
    if [ "$prev" -eq 1 ]; then
      emit "ok  $box back (age ${age}s)"
      eval "$prev_var=0"
    fi
  fi
}

while true; do
  # 1. run.jsonl progress
  if [ -f "$RUN" ]; then
    n=$(wc -l < "$RUN" | tr -d ' ')
    if [ "$n" -gt "$prev_run" ]; then
      delta=$((n - prev_run))
      last=$(tail -1 "$RUN" | python3 -c '
import sys, json
d = json.loads(sys.stdin.read())
s = d.get("state", "?")
i = d.get("instance_id", "?")[:60]
print(s, i)
' 2>/dev/null)
      wins=$(grep -c '"state": "WIN"' "$RUN" 2>/dev/null)
      loss=$(grep -c '"state": "LOSS"' "$RUN" 2>/dev/null)
      emit "run +$delta (total=$n W=$wins L=$loss) last: $last"
      prev_run=$n
    fi
  fi

  # 2. heartbeat freshness per box
  if [ -f "$HB" ]; then
    check_box coord1
    check_box coord2
    check_box coord3
    check_box coord4
  fi

  # 3. coordinator log errors / EMPTY
  if [ -f "$COORD" ]; then
    err=$(grep -cE "Traceback|Killed|OOM|Connection refused|Permission denied" "$COORD" 2>/dev/null)
    empty=$(grep -c "EMPTY patch" "$COORD" 2>/dev/null)
    if [ "$err" -gt "$prev_err" ]; then
      emit "!! errors +$((err - prev_err)) (total=$err):"
      grep -E "Traceback|Killed|OOM|Connection refused|Permission denied" "$COORD" | tail -3 >> "$OUT"
      prev_err=$err
    fi
    if [ "$empty" -gt "$prev_empty" ]; then
      emit "!! EMPTY patch +$((empty - prev_empty)) (total=$empty)"
      prev_empty=$empty
    fi
  fi

  sleep 60
done
