#!/usr/bin/env python3
"""pro_run.py — the whole-set driver for SWE-bench Pro. One loop, two modes.

The §6 defect audit and the §2 measurement run are the SAME iteration over the frozen order
(`tasks/run_order.txt`, prereg §3) — they differ only in the per-instance action:

  --mode audit : grade each instance's GOLD patch via pro_smoke (official grader, $0 tokens).
                 RESOLVED -> eligible; not-RESOLVED or missing image/parser -> DEFECT (§6);
                 enumerated platform fault -> audit-incomplete (retried, never a defect).
  --mode run   : make_task + pro_pilot agent loop, record the official verdict (spends tokens).

Sharding (`--shard i/N`) is a deterministic stripe of the frozen order, so shard maps are
reproducible (prereg §3). Resume is automatic: an instance with a committed result line is
skipped, so a re-run only fills gaps (prereg §3 "re-run only the aborted instances").

  driver/pro_run.py --mode audit [--shard 1/4] [--limit N] [--redo ID ...]
  driver/pro_run.py --mode run   [--shard 1/4] [--eligible runs/audit/eligible.txt]

Reads $PY/$SWEAP_OS_REPO from driver/.proenv (source it first). Frozen target: concrete by design.
"""
import argparse, json, os, pathlib, re, subprocess, sys, time

REPO = pathlib.Path(__file__).resolve().parent.parent
DRIVER = REPO / "driver"
ORDER = REPO / "tasks" / "run_order.txt"
PY = sys.executable  # the .venv python that imports this is the one to reuse

# Enumerated platform faults (prereg §4): audit-incomplete, retried — NOT a defect / NOT a loss.
FAULT_RE = re.compile(r"BOX_DEATH|AWS_API|OOM|DISK_FULL|SETUP_NETWORK_FAIL|QUOTA_EXHAUSTED|"
                      r"No space left|Cannot connect to the Docker daemon|manifest unknown|"
                      r"failed to pull|Killed|MemoryError", re.I)


def load_order():
    if not ORDER.exists():
        sys.exit(f"missing {ORDER} — generate the frozen order first (prereg §3)")
    return [l.strip() for l in ORDER.read_text().splitlines() if l.strip()]


def shard(ids, spec):
    if not spec:
        return ids
    i, n = (int(x) for x in spec.split("/"))
    if not (1 <= i <= n):
        sys.exit(f"--shard {spec}: need 1<=i<=N")
    return [x for k, x in enumerate(ids) if k % n == (i - 1)]  # deterministic stripe of frozen order


def prune_images():
    """Audit/run pulls a distinct multi-GB image per instance — without pruning, a shard's worth
    overflows the disk (→ false DISK_FULL). Best-effort reclaim between instances. Off via
    PRO_RUN_PRUNE=0. Nothing is running between instances, so `prune -af` only drops cached images."""
    if os.environ.get("PRO_RUN_PRUNE", "1") == "0":
        return
    subprocess.run("sudo docker system prune -af --volumes >/dev/null 2>&1 || "
                   "docker system prune -af --volumes >/dev/null 2>&1",
                   shell=True, timeout=300)


def audit_one(iid):
    """Grade the gold patch. Returns (state, detail). state in {eligible, defect, incomplete}."""
    try:
        p = subprocess.run([PY, str(DRIVER / "pro_smoke.py"), iid],
                           capture_output=True, text=True, timeout=2400)
    except subprocess.TimeoutExpired:
        return "incomplete", "TIMEOUT (2400s) — retry"
    out = (p.stdout + p.stderr)
    m = re.search(r"RESOLVED=(True|False)", out)
    if m:
        return ("eligible", "gold RESOLVED") if m.group(1) == "True" else ("defect", "gold NOT resolved")
    # no verdict line: platform fault (retry) vs broken image/parser (defect)
    if FAULT_RE.search(out):
        return "incomplete", "platform fault: " + (FAULT_RE.search(out).group(0))
    return "defect", "no grade (missing/broken image or parser): " + out.strip()[-200:]


def run_one(iid):
    """make_task + pro_pilot agent loop. Returns (verdict, detail). verdict in {WIN, LOSS, INCOMPLETE}."""
    task = REPO / "tasks" / "generated" / f"{iid}.json"
    mk = subprocess.run([PY, str(DRIVER / "make_task.py"), iid], capture_output=True, text=True,
                        env={**os.environ, "BENCH": "pro"}, timeout=600)
    if not task.exists():
        return "INCOMPLETE", "make_task failed: " + (mk.stderr or mk.stdout).strip()[-200:]
    p = subprocess.run([PY, str(DRIVER / "pro_pilot.py"), str(task), iid],
                       capture_output=True, text=True)
    out = p.stdout + p.stderr
    m = re.search(r"OFFICIAL RESOLVED:\s*(True|False)", out)
    if m:
        return ("WIN", "official RESOLVED") if m.group(1) == "True" else ("LOSS", "not resolved")
    if FAULT_RE.search(out):
        return "INCOMPLETE", "platform fault: " + FAULT_RE.search(out).group(0)
    return "LOSS", "no verdict (endogenous): " + out.strip()[-200:]  # prereg §4: endogenous no-patch = LOSS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["audit", "run"])
    ap.add_argument("--shard", help="i/N deterministic stripe of the frozen order")
    ap.add_argument("--limit", type=int, help="stop after N instances (dev only)")
    ap.add_argument("--eligible", help="(run mode) file of eligible ids; default = all in order")
    ap.add_argument("--redo", nargs="*", default=[], help="force re-run these ids even if recorded")
    ap.add_argument("--only", nargs="*", default=[], help="run exactly these ids (coordinator single-dispatch)")
    args = ap.parse_args()

    outdir = REPO / "runs" / ("audit" if args.mode == "audit" else "scored")
    outdir.mkdir(parents=True, exist_ok=True)
    ledger = outdir / (f"audit{('_'+args.shard.replace('/','of')) if args.shard else ''}.jsonl"
                       if args.mode == "audit" else
                       f"run{('_'+args.shard.replace('/','of')) if args.shard else ''}.jsonl")

    done = {}
    if ledger.exists():
        for l in ledger.read_text().splitlines():
            try:
                r = json.loads(l); done[r["instance_id"]] = r
            except Exception:
                pass

    if args.only:
        order = set(load_order())
        ids = [i for i in args.only if i in order]   # validate against frozen order
        args.redo = list(args.only)                  # --only always runs, even if recorded
    else:
        ids = shard(load_order(), args.shard)
        if args.mode == "run" and args.eligible:
            elig = set(pathlib.Path(args.eligible).read_text().split())
            ids = [i for i in ids if i in elig]
        if args.limit:
            ids = ids[:args.limit]

    act = audit_one if args.mode == "audit" else run_one
    with open(ledger, "a") as f:
        for k, iid in enumerate(ids, 1):
            if iid in done and iid not in args.redo:
                continue  # resume: skip recorded (prereg §3)
            t0 = time.time()
            started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
            print(f"[{k}/{len(ids)}] {args.mode} {iid} ...", flush=True)
            state, detail = act(iid)
            # UTC wall-clock start/end: lets every INCOMPLETE be correlated against provider-incident
            # timelines (prereg §4) — an INCOMPLETE outside any Anthropic/OpenAI outage is a suspicious
            # re-roll, not a platform fault. Records the audit trail that closes that cheating vector.
            rec = {"instance_id": iid, "mode": args.mode, "state": state, "detail": detail,
                   "secs": round(time.time() - t0),
                   "started_at": started_at,
                   "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            f.write(json.dumps(rec) + "\n"); f.flush()
            print(f"    -> {state} ({rec['secs']}s) {detail[:80]}", flush=True)
            print("RESULT_JSON " + json.dumps(rec), flush=True)  # coordinator parses this off stdout
            prune_images()  # bound disk: drop the instance image before pulling the next

    # summary + (audit) frozen eligible/defect lists
    recs = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    from collections import Counter
    c = Counter(r["state"] for r in recs)
    print(f"\n=== {args.mode} summary (ledger {ledger.name}): {dict(c)} of {len(recs)} ===")
    if args.mode == "audit" and not args.shard:  # whole-set audit -> emit the frozen §6 lists
        elig = [r["instance_id"] for r in recs if r["state"] == "eligible"]
        defects = [r for r in recs if r["state"] == "defect"]
        (outdir / "eligible.txt").write_text("\n".join(elig) + "\n")
        (outdir / "defects.jsonl").write_text("".join(json.dumps(d) + "\n" for d in defects))
        inc = [r["instance_id"] for r in recs if r["state"] == "incomplete"]
        print(f"  eligible={len(elig)}  defects={len(defects)}  incomplete(retry)={len(inc)}")
        if inc:
            print("  INCOMPLETE (re-run with --redo to finish): " + " ".join(inc[:10]))


if __name__ == "__main__":
    main()
