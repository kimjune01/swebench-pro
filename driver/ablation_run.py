#!/usr/bin/env python3
"""ablation_run.py — RUNNER for the methodeutic ablation (prereg-pro-v1-untyped), one arm this run.

Runner is flexible; the harness is frozen (prior preregs). Pure runner: shards the seeded-random
sample, owns the ledger / resume / platform-fault state machine, and shells per-instance to the
untyped arm driver (pro_untyped.py). It never touches the measurement contract.

THE ARM: the clean single-factor ablation. The full headline pipeline (Sonnet + codex + gate +
outer loop) with the /recon skill swapped for /ask -- same goal, no applied epistemology. The
frozen typed headline (runs/scored/run.jsonl) is the paired comparator; p_typed - p_untyped =
Delta_typing.

  driver/ablation_run.py [--shard i/8] [--limit N] [--redo ID ...] [--only ID ...]

Ledger: runs/scored/untyped[_iofN].jsonl. Resume = skip recorded. Sources $PY/$SWEAP_OS_REPO from
driver/.proenv (source it first).
"""
import argparse, json, os, pathlib, re, subprocess, sys, time
from collections import Counter

REPO = pathlib.Path(__file__).resolve().parent.parent
DRIVER = REPO / "driver"
PY = sys.executable
SAMPLE = REPO / "tasks" / "ablation_sample.txt"   # seeded-random draw (prereg-untyped 2.2)
ARM_DRIVER = "pro_untyped.py"

# Same enumerated platform faults as pro_run.py 4 (kept in sync with the frozen runner's discipline).
FAULT_RE = re.compile(r"BOX_DEATH|AWS_API|OOM|DISK_FULL|SETUP_NETWORK_FAIL|QUOTA_EXHAUSTED|"
                      r"No space left|Cannot connect to the Docker daemon|manifest unknown|"
                      r"failed to pull|Killed|MemoryError", re.I)


def load_sample():
    if not SAMPLE.exists():
        sys.exit(f"missing {SAMPLE} (generate it: driver/ablation_bayes.py sample)")
    return [l.strip() for l in SAMPLE.read_text().splitlines() if l.strip()]


def shard(ids, spec):
    if not spec:
        return ids
    i, n = (int(x) for x in spec.split("/"))
    if not (1 <= i <= n):
        sys.exit(f"--shard {spec}: need 1<=i<=N")
    return [x for k, x in enumerate(ids) if k % n == (i - 1)]   # deterministic stripe of sample order


def prune_images():
    if os.environ.get("PRO_RUN_PRUNE", "1") == "0":
        return
    subprocess.run("sudo docker system prune -af --volumes >/dev/null 2>&1 || "
                   "docker system prune -af --volumes >/dev/null 2>&1",
                   shell=True, timeout=300)


def run_one(iid):
    """make_task + pro_untyped.py. Verdict parse identical to pro_run.run_one."""
    task = REPO / "tasks" / "generated" / f"{iid}.json"
    mk = subprocess.run([PY, str(DRIVER / "make_task.py"), iid], capture_output=True, text=True,
                        env={**os.environ, "BENCH": "pro"}, timeout=600)
    if not task.exists():
        return "INCOMPLETE", "make_task failed: " + (mk.stderr or mk.stdout).strip()[-200:]
    p = subprocess.run([PY, str(DRIVER / ARM_DRIVER), str(task), iid], capture_output=True, text=True)
    out = p.stdout + p.stderr
    m = re.search(r"OFFICIAL RESOLVED:\s*(True|False)", out)
    if m:
        return ("WIN", "official RESOLVED") if m.group(1) == "True" else ("LOSS", "not resolved")
    if FAULT_RE.search(out):
        return "INCOMPLETE", "platform fault: " + FAULT_RE.search(out).group(0)
    return "LOSS", "no verdict (endogenous): " + out.strip()[-200:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard", help="i/N deterministic stripe of the sample order")
    ap.add_argument("--limit", type=int, help="stop after N instances (dev only)")
    ap.add_argument("--redo", nargs="*", default=[], help="force re-run these ids even if recorded")
    ap.add_argument("--only", nargs="*", default=[], help="run exactly these ids (coordinator single-dispatch)")
    args = ap.parse_args()

    outdir = REPO / "runs" / "scored"
    outdir.mkdir(parents=True, exist_ok=True)
    ledger = outdir / (f"untyped_{args.shard.replace('/', 'of')}.jsonl" if args.shard else "untyped.jsonl")

    done = {}
    if ledger.exists():
        for l in ledger.read_text().splitlines():
            try:
                r = json.loads(l); done[r["instance_id"]] = r
            except Exception:
                pass

    if args.only:
        sample = set(load_sample())
        ids = [i for i in args.only if i in sample]   # validate against the frozen sample
        args.redo = list(args.only)
    else:
        ids = shard(load_sample(), args.shard)
        if args.limit:
            ids = ids[:args.limit]

    with open(ledger, "a") as f:
        for k, iid in enumerate(ids, 1):
            if iid in done and iid not in args.redo:
                continue   # resume: skip recorded
            t0 = time.time()
            started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
            print(f"[{k}/{len(ids)}] untyped {iid} ...", flush=True)
            state, detail = run_one(iid)
            rec = {"instance_id": iid, "mode": "untyped", "state": state, "detail": detail,
                   "secs": round(time.time() - t0),
                   "started_at": started_at,
                   "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            f.write(json.dumps(rec) + "\n"); f.flush()
            print(f"    -> {state} ({rec['secs']}s) {detail[:80]}", flush=True)
            print("RESULT_JSON " + json.dumps(rec), flush=True)   # coordinator parses this off stdout
            prune_images()

    recs = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    c = Counter(r["state"] for r in recs)
    print(f"\n=== untyped summary (ledger {ledger.name}): {dict(c)} of {len(recs)} ===")


if __name__ == "__main__":
    main()
