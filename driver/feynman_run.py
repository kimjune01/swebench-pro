#!/usr/bin/env python3
"""feynman_run.py -- RUNNER for the perturbation ablation (prereg-pro-v1-feynman).

Pure runner (flexible; harness frozen): shards the ORDERED strata sample (UNDER-first), owns the
ledger / resume / platform-fault machinery, shells per-instance to pro_feynman.py. Pairs offline
against the frozen /recon baseline (runs/scored/run.jsonl) via feynman_bayes.py.

  driver/feynman_run.py [--shard i/N] [--limit N] [--redo ID ...] [--only ID ...]

Ledger: runs/scored/feynman[_iofN].jsonl. Resume = skip recorded. Sources $PY/$SWEAP_OS_REPO from
driver/.proenv (source it first).
"""
import argparse, json, os, pathlib, re, signal, subprocess, sys, time
from collections import Counter

REPO = pathlib.Path(__file__).resolve().parent.parent
DRIVER = REPO / "driver"
PY = sys.executable
SAMPLE = REPO / "tasks" / "perturbation_sample.txt"   # ordered: UNDER first (prereg-feynman 3)
ARM_DRIVER = "pro_feynman.py"

# Per-instance wall cap. The per-STAGE caps in rung5 (RECON 2000 / CRAFT 3600 / gate 1800, MAX_OUTER 5)
# do NOT reliably reap a wedged process tree -- heavy suites (NodeBB et al.) hang the gate's docker-exec
# below the stage timeout and freeze the box for hours (observed 3-4h, zero log output). This is the
# documented craft-hang. The OUTERMOST boundary always works: Popen in its own session, SIGKILL the
# whole group on timeout, then docker-kill any container the dead process left wedged on the test suite.
# A TIMEOUT is QUARANTINED (not a LOSS -- a hang is not a capability failure) and re-runnable on resume.
PINST_TIMEOUT = int(os.environ.get("PINST_TIMEOUT", "3600"))   # 60 min; flipt ran 699s, deep loops < ~40m
MIN_REAL_SECS = int(os.environ.get("MIN_REAL_SECS", "180"))    # a LOSS faster than this = suspected
# auth/quota death (a real loss runs the full Sonnet+codex pipeline). Quarantined from Delta in
# feynman_bayes.py AND treated as non-terminal here so resume auto-retries it (consistent philosophy).

FAULT_RE = re.compile(r"BOX_DEATH|AWS_API|OOM|DISK_FULL|SETUP_NETWORK_FAIL|QUOTA_EXHAUSTED|"
                      r"No space left|Cannot connect to the Docker daemon|manifest unknown|"
                      r"failed to pull|Killed|MemoryError", re.I)


def load_sample():
    if not SAMPLE.exists():
        sys.exit(f"missing {SAMPLE} (generate it: driver/perturbation_strata.py)")
    return [l.strip() for l in SAMPLE.read_text().splitlines() if l.strip()]


def shard(ids, spec):
    if not spec:
        return ids
    i, n = (int(x) for x in spec.split("/"))
    if not (1 <= i <= n):
        sys.exit(f"--shard {spec}: need 1<=i<=N")
    return [x for k, x in enumerate(ids) if k % n == (i - 1)]


def prune_images():
    if os.environ.get("PRO_RUN_PRUNE", "1") == "0":
        return
    subprocess.run("sudo docker system prune -af --volumes >/dev/null 2>&1 || "
                   "docker system prune -af --volumes >/dev/null 2>&1", shell=True, timeout=300)


def run_one(iid):
    task = REPO / "tasks" / "generated" / f"{iid}.json"
    mk = subprocess.run([PY, str(DRIVER / "make_task.py"), iid], capture_output=True, text=True,
                        env={**os.environ, "BENCH": "pro"}, timeout=600)
    if not task.exists():
        return "INCOMPLETE", "make_task failed: " + (mk.stderr or mk.stdout).strip()[-200:]
    p = subprocess.Popen([PY, str(DRIVER / ARM_DRIVER), str(task), iid],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=PINST_TIMEOUT)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            out, _ = p.communicate(timeout=60)
        except Exception:
            out = ""
        # the dead process may have left a container wedged mid-test-suite; reap it (runner is sequential).
        subprocess.run("sudo docker kill $(sudo docker ps -q) 2>/dev/null || true", shell=True, timeout=120)
        return "TIMEOUT", f"per-instance wall cap {PINST_TIMEOUT}s (quarantined, re-runnable)"
    m = re.search(r"OFFICIAL RESOLVED:\s*(True|False)", out)
    ref = re.search(r"perturbation_refusals\(diagnosis\):\s*(\d+)", out)
    refusals = int(ref.group(1)) if ref else None
    if m:
        st = "WIN" if m.group(1) == "True" else "LOSS"
        return st, f"official RESOLVED (refusals={refusals})" if st == "WIN" else f"not resolved (refusals={refusals})"
    if FAULT_RE.search(out):
        return "INCOMPLETE", "platform fault: " + FAULT_RE.search(out).group(0)
    return "LOSS", "no verdict (endogenous): " + out.strip()[-200:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shard"); ap.add_argument("--limit", type=int)
    ap.add_argument("--redo", nargs="*", default=[]); ap.add_argument("--only", nargs="*", default=[])
    args = ap.parse_args()

    outdir = REPO / "runs" / "scored"; outdir.mkdir(parents=True, exist_ok=True)
    ledger = outdir / (f"feynman_{args.shard.replace('/', 'of')}.jsonl" if args.shard else "feynman.jsonl")

    done = {}
    if ledger.exists():
        for l in ledger.read_text().splitlines():
            try:
                r = json.loads(l); done[r["instance_id"]] = r
            except Exception:
                pass

    if args.only:
        sample = set(load_sample()); ids = [i for i in args.only if i in sample]; args.redo = list(args.only)
    else:
        ids = shard(load_sample(), args.shard)
        if args.limit:
            ids = ids[:args.limit]

    with open(ledger, "a") as f:
        for k, iid in enumerate(ids, 1):
            # resume skips only TERMINAL verdicts; INCOMPLETE/TIMEOUT and fast-LOSS (suspected infra
            # death, < MIN_REAL_SECS) are quarantined -> auto-retry on the next pass.
            if iid in done and iid not in args.redo:
                pr = done[iid]
                terminal = pr.get("state") == "WIN" or (
                    pr.get("state") == "LOSS" and pr.get("secs", 0) >= MIN_REAL_SECS)
                if terminal:
                    continue
            t0 = time.time(); started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t0))
            print(f"[{k}/{len(ids)}] feynman {iid} ...", flush=True)
            state, detail = run_one(iid)
            rec = {"instance_id": iid, "mode": "feynman", "state": state, "detail": detail,
                   "secs": round(time.time() - t0), "started_at": started,
                   "ended_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
            f.write(json.dumps(rec) + "\n"); f.flush()
            print(f"    -> {state} ({rec['secs']}s) {detail[:80]}", flush=True)
            print("RESULT_JSON " + json.dumps(rec), flush=True)
            prune_images()

    recs = [json.loads(l) for l in ledger.read_text().splitlines() if l.strip()]
    c = Counter(r["state"] for r in recs)
    print(f"\n=== feynman summary (ledger {ledger.name}): {dict(c)} of {len(recs)} ===")


if __name__ == "__main__":
    main()
