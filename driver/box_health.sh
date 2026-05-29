#!/bin/bash
# box_health.sh — at-a-glance fleet health from runs/scored/box_heartbeat.jsonl
#
# The grader_watchdog writes one heartbeat record per box per poll (default 5min).
# This script reads the last N samples per box and prints:
#   - last seen (minutes ago)
#   - current container (uptime, CPU%, idle min) if any
#   - load1 trend (last 6 samples = ~30min at default cadence)
#   - "stuck?" verdict: consecutive low-CPU container samples
#
# usage:
#   bash driver/box_health.sh                # current state of every box
#   bash driver/box_health.sh --window 12    # 12 samples = ~1h
#   bash driver/box_health.sh coord3         # detail one box

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

    # Container state from latest sample
    if latest["containers"]:
        c = latest["containers"][-1]
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

    # Stuck verdict: container present in last K samples AND cpu always <1%
    stuck = ""
    container_samples = [(s, s["containers"][-1] if s["containers"] else None) for s in samples]
    container_samples = [(s, c) for s, c in container_samples if c is not None]
    if len(container_samples) >= 3:
        low_cpu = all(c["cpu_pct"] < 1.0 for _, c in container_samples[-min(6, len(container_samples)):])
        if low_cpu:
            span_min = container_samples[-1][1]["idle_min"]
            stuck = f"  ⚠ STUCK (low-cpu ≥{span_min}m)"

    print(f"{box}  last={age_min}m ago  {c_str}  {load_str}{stuck}")

if filt and not any(b == filt for b in records):
    print(f"no records for {filt}", file=sys.stderr)
'
