#!/bin/bash
# runtime_histogram.sh — ASCII distribution of completed-instance wall times from run.jsonl
#
# Operator query (no side effects). Reads runs/scored/run.jsonl, deduplicates by instance_id
# (last-wins), and prints:
#   - overall histogram of `secs` for WIN + LOSS, 5-min bins
#   - p50/p90/p95/max wall time, separately for WIN and LOSS
#   - per-repo breakdown for the top 10 repos (count + median)
#   - calibration check: how far is p95 from the grader_watchdog IDLE_THRESHOLD_MIN
#
# usage:
#   bash driver/runtime_histogram.sh              # all completed instances
#   bash driver/runtime_histogram.sh --repo NodeBB # one repo
#   bash driver/runtime_histogram.sh --state WIN  # WIN only

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

LEDGER="runs/scored/run.jsonl"
[ -f "$LEDGER" ] || { echo "no $LEDGER" >&2; exit 1; }

FILTER_REPO=""
FILTER_STATE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo)  FILTER_REPO="$2"; shift 2;;
    --state) FILTER_STATE="$2"; shift 2;;
    *) echo "unknown flag: $1" >&2; exit 1;;
  esac
done

FILTER_REPO="$FILTER_REPO" FILTER_STATE="$FILTER_STATE" python3 -c '
import json, os, re, collections, statistics, sys

filt_repo  = os.environ.get("FILTER_REPO", "")
filt_state = os.environ.get("FILTER_STATE", "")

# Dedupe by instance_id, last-wins
records = {}
with open("runs/scored/run.jsonl") as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try: r = json.loads(line)
        except: continue
        if "secs" not in r: continue
        if r.get("state") not in ("WIN", "LOSS"): continue
        records[r["instance_id"]] = r

# Repo extraction from instance_id: "instance_<owner>__<repo>-<sha>..."
def get_repo(iid):
    m = re.match(r"instance_([^_]+)__", iid)
    return m.group(1) if m else "unknown"

rows = []
for iid, r in records.items():
    repo = get_repo(iid)
    if filt_repo and repo != filt_repo: continue
    if filt_state and r["state"] != filt_state: continue
    rows.append({"iid": iid, "repo": repo, "state": r["state"], "secs": int(r["secs"])})

if not rows:
    print("no matching records"); sys.exit(0)

# Overall stats
all_secs = sorted(r["secs"] for r in rows)
wins  = [r["secs"] for r in rows if r["state"] == "WIN"]
losses= [r["secs"] for r in rows if r["state"] == "LOSS"]

def pct(xs, p):
    if not xs: return 0
    k = int(len(xs) * p)
    k = min(k, len(xs)-1)
    return sorted(xs)[k]

def fmt_secs(s):
    if s < 60: return f"{s}s"
    return f"{s/60:.1f}m"

n = len(rows)
print(f"=== runtime distribution ({n} graded instances")
if filt_repo or filt_state:
    fparts = []
    if filt_repo:  fparts.append(f"repo={filt_repo}")
    if filt_state: fparts.append(f"state={filt_state}")
    print(f"    filter: {chr(44).join(fparts)})")
else:
    print(")")
print()
print(f"  overall:  p50={fmt_secs(pct(all_secs,0.5))}  p90={fmt_secs(pct(all_secs,0.9))}  p95={fmt_secs(pct(all_secs,0.95))}  max={fmt_secs(all_secs[-1])}")
if wins:
    print(f"  WIN ({len(wins):>3}): p50={fmt_secs(pct(wins,0.5))}  p90={fmt_secs(pct(wins,0.9))}  p95={fmt_secs(pct(wins,0.95))}  max={fmt_secs(max(wins))}")
if losses:
    print(f"  LOSS ({len(losses):>2}): p50={fmt_secs(pct(losses,0.5))}  p90={fmt_secs(pct(losses,0.9))}  p95={fmt_secs(pct(losses,0.95))}  max={fmt_secs(max(losses))}")

# ASCII histogram, 5-min bins up to 60 min, then 60+ bucket
print()
print("=== histogram (5-min bins) ===")
bins = collections.Counter()
for r in rows:
    m = r["secs"] // 60
    if m >= 120:    key = "120m+"
    elif m >= 60:   key = "60-120m"
    else:           key = f"{(m//5)*5:>2}-{(m//5)*5+5:>2}m"
    bins[key] += 1
ordered = sorted(bins.keys(), key=lambda k: (999 if "+" in k else 998 if "60-" in k else int(k.split("-")[0])))
maxct = max(bins.values()) if bins else 1
for k in ordered:
    bar = "█" * int(40 * bins[k] / maxct)
    print(f"  {k:>10s} {bar} {bins[k]}")

# Per-repo breakdown
if not filt_repo:
    print()
    print("=== top repos (by instance count) ===")
    by_repo = collections.defaultdict(list)
    for r in rows: by_repo[r["repo"]].append(r["secs"])
    repos = sorted(by_repo.items(), key=lambda kv: -len(kv[1]))[:10]
    for repo, secs in repos:
        med = sorted(secs)[len(secs)//2]
        p95v = pct(secs, 0.95)
        print(f"  {repo:>20s}  n={len(secs):>3}  median={fmt_secs(med):>6s}  p95={fmt_secs(p95v):>6s}")

# Calibration vs watchdog threshold
WATCHDOG_IDLE = 30  # IDLE_THRESHOLD_MIN default
print()
print("=== calibration vs grader_watchdog IDLE_THRESHOLD_MIN=30 ===")
p95min = pct(all_secs, 0.95) // 60
over_thresh = sum(1 for r in rows if r["secs"] > WATCHDOG_IDLE * 60)
ratio = over_thresh / len(rows)
print(f"  {over_thresh}/{len(rows)} runs ({ratio:.0%}) finished after >30min wall time")
print(f"  p95 wall time = {p95min}m  → 30m threshold gives {30/p95min:.2f}x headroom" if p95min > 0 else "")
if 30 / max(p95min, 1) < 1.5:
    print(f"  ⚠ headroom < 1.5x — watchdog may kill legitimate runs near p95")
else:
    print(f"  ✓ headroom adequate")
'
