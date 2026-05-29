#!/bin/bash
# retry_grader_kills.sh — cross-reference watchdog kills with LOSS entries; strip the spurious
# LOSSes from the ledger so the queue re-picks those instances on next coordinator startup.
#
# Operator infra (one-shot). Modifies runs/scored/run.jsonl in place; backs up the original
# to runs/scored/run.jsonl.bak-pre-retry-<UTC-stamp>. Idempotent: re-running is a no-op once
# all matching LOSSes have been stripped.
#
# Pattern: for each KILL in runs/scored/grader_kills.jsonl, find any LOSS in run.jsonl recorded
# within MATCH_WINDOW seconds on the same box. Those LOSSes are presumed grader-hang artifacts.
#
# Policy: if a re-queued instance fails again on the next attempt, it's a genuine failure
# (or a repeating platform bug worthy of KNOWN_BAD). Decision is operator's, not automated.
#
# usage:
#   bash driver/retry_grader_kills.sh                  # default MATCH_WINDOW=60s
#   MATCH_WINDOW=120 bash driver/retry_grader_kills.sh # widen the LOSS-to-KILL match window
#
# Apply takes effect on next coordinator startup (queue rebuilds from ledger). Caller decides
# when to kill the running coordinator; the watchdog will bring it back with --skip-setup.

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

LEDGER="runs/scored/run.jsonl"
KILLS="runs/scored/grader_kills.jsonl"
MATCH_WINDOW="${MATCH_WINDOW:-60}"   # seconds between watchdog KILL and ledger LOSS to count as caused

[ -f "$KILLS"  ] || { echo "no $KILLS — nothing to retry" >&2; exit 0; }
[ -f "$LEDGER" ] || { echo "FATAL: $LEDGER missing" >&2; exit 1; }

# Python does the heavy lifting (jsonl parsing, time math, ledger rewriting)
python3 <<PY
import json, pathlib, datetime as dt, shutil, sys

LEDGER = pathlib.Path("$LEDGER")
KILLS  = pathlib.Path("$KILLS")
WINDOW = $MATCH_WINDOW

def parse_iso(s):
    # ledger uses ...Z; date -u +%FT%TZ produces ...Z too
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))

kills = []
with KILLS.open() as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try: kills.append(json.loads(line))
        except: pass

if not kills:
    print("no kills to process"); sys.exit(0)

ledger_lines = LEDGER.read_text().splitlines()
ledger_recs  = []
for i, line in enumerate(ledger_lines):
    try:
        r = json.loads(line)
        if r.get("state") == "LOSS" and r.get("ended_at"):
            ledger_recs.append((i, r))
    except: pass

# For each kill, find LOSSes on the same box ended within WINDOW seconds after the kill
spurious_indices = set()
matches = []
for k in kills:
    kt = parse_iso(k["ts"])
    box = k["box"]
    for i, r in ledger_recs:
        if r["box"] != box: continue
        rt = parse_iso(r["ended_at"])
        delta = (rt - kt).total_seconds()
        if 0 <= delta <= WINDOW:
            spurious_indices.add(i)
            matches.append((k["ts"], box, k["container"], r["instance_id"], delta))

if not spurious_indices:
    print("no LOSS entries match a recent watchdog kill"); sys.exit(0)

# Back up + rewrite ledger
bak = LEDGER.with_suffix(LEDGER.suffix + f".bak-pre-retry-{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}")
shutil.copy(LEDGER, bak)

kept = [line for i, line in enumerate(ledger_lines) if i not in spurious_indices]
LEDGER.write_text("\n".join(kept) + ("\n" if kept else ""))

print(f"backed up original ledger to {bak.name}")
print(f"removed {len(spurious_indices)} LOSS entries matching watchdog kills:")
for ts, box, cname, iid, delta in matches:
    print(f"  {ts}  {box:7s}  kill={cname}  loss_after={delta:.0f}s  iid={iid[:60]}")

print()
print(f"queue will re-pick these on next coordinator startup.")
print(f"current coordinator must be restarted for the change to take effect:")
print(f"  pkill -f 'driver/coordinator\\.py'   # watchdog brings it back with --skip-setup")
PY
