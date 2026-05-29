#!/bin/bash
# box_health.sh — at-a-glance fleet health from runs/scored/box_heartbeat.jsonl
#
# Operator query (no side effects). The grader_watchdog writes one heartbeat record per box
# per poll (default 5min); this script reads the last N samples per box and prints:
#   - last seen (minutes ago)
#   - current container (uptime, CPU%, idle min); flags '+N stale' if leaked
#   - load1 trend (last N samples)
#   - verdict on the active container: STUCK (logs idle ≥30m), · slow (logs idle ≥10m), or quiet
#
# usage:
#   bash driver/box_health.sh                # snapshot, all boxes, ~30min trend
#   bash driver/box_health.sh --window 12    # ~1h trend
#   bash driver/box_health.sh coord3         # focus one box, ~1h trend

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

HEARTBEAT="runs/scored/box_heartbeat.jsonl"
[ -f "$HEARTBEAT" ] || { echo "no heartbeat data yet (waiting on grader_watchdog poll)" >&2; exit 0; }

WINDOW="${1:-6}"
FILTER=""
if [[ "${1:-}" =~ ^-- ]]; then
  case "$1" in
    --window) WINDOW="${2:-6}";;
    *) echo "unknown flag: $1" >&2; exit 1;;
  esac
elif [[ "${1:-}" =~ ^coord ]]; then
  FILTER="$1"
  WINDOW=12
fi

WINDOW="$WINDOW" FILTER="$FILTER" python3 -c '
import json, os, sys, datetime as dt, collections
window = int(os.environ.get("WINDOW", "6"))
filt = os.environ.get("FILTER", "")
now = dt.datetime.utcnow()

records = collections.defaultdict(list)
with open("runs/scored/box_heartbeat.jsonl") as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except: continue
        records[r["box"]].append(r)

for box in sorted(records):
    if filt and box != filt: continue
    samples = records[box][-window:]
    if not samples: continue
    latest = samples[-1]
    age_s = (now - dt.datetime.fromisoformat(latest["ts"].replace("Z","+00:00")).replace(tzinfo=None)).total_seconds()
    age_min = int(age_s / 60)

    # Container state from latest sample (docker ps lists newest-first, so containers[0] is active)
    if latest["containers"]:
        c = latest["containers"][0]
        cname = c["name"][:20]
        cup = c["uptime_min"]
        ccpu = c["cpu_pct"]
        cidle = c["idle_min"]
        ncont = len(latest["containers"])
        suffix = "" if ncont == 1 else f" (+{ncont-1} stale)"
        c_str = f"container={cname} up={cup}m cpu={ccpu}% idle={cidle}m{suffix}"
    else:
        c_str = "no container"

    # Load trend (last N samples)
    loads = [s["load1"] for s in samples]
    load_str = "load1=[" + " ".join(f"{l:.2f}" for l in loads) + "]"

    # Stuck verdict: idle_min from latest sample tells the truth. CPU% is misleading for
    # I/O-bound graders (npx mocha sits at ~0.4% CPU while running long Node test suites).
    # The real progress signal is whether /workspace/stdout.log is being written, which is
    # what idle_min now measures (watchdog reads inside-container log mtime).
    stuck = ""
    latest_c = latest["containers"][0] if latest["containers"] else None
    if latest_c:
        idle = latest_c["idle_min"]
        if idle >= 30:
            stuck = f"  ⚠ STUCK (logs idle {idle}m)"
        elif idle >= 10:
            stuck = f"  · slow (logs idle {idle}m)"

    print(f"{box}  last={age_min}m ago  {c_str}  {load_str}{stuck}")

if filt and not any(b == filt for b in records):
    print(f"no records for {filt}", file=sys.stderr)
'
