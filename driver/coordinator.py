#!/usr/bin/env python3
"""coordinator.py — laptop-side dynamic dispatcher for the scored run.

NOT the canonical reproducible path. Scale reproduces the number with `pro_run.py --mode run
--shard i/N` — just EC2 + pinned deps, zero custom infra. THIS is an operator convenience for our
week-long run: keep N EC2 boxes near-100% utilized by handing each the next eligible instance over
SSH the moment it finishes, instead of static stripes where a box that drew the heavy instances runs
long while the rest idle. The per-instance unit is identical to the canonical path
(`pro_run --only <iid>` -> make_task + pro_pilot + official grade), so verdicts match exactly.

The laptop is the always-on coordinator and holds the authoritative ledger (runs/scored/run.jsonl).
Boxes hold no durable state.

Fault tolerance:
  - box dies/hangs mid-instance -> SSH errors or hits --instance-ceiling -> id requeued, box
    re-provisioned (run_fleet.sh kill-box + setup-box), work resumes (<= 1 instance redone)
  - coordinator crash           -> re-run; resumes from the ledger (terminal verdicts skipped)
  - poison instance             -> bounded --max-attempts -> recorded INCOMPLETE (prereg §4), no loop
  - box won't come up           -> bounded --box-restart-max -> that worker retires; others carry on

  driver/coordinator.py --boxes 4 --eligible runs/audit/eligible.txt
"""
import argparse, json, os, pathlib, queue, re, subprocess, sys, threading, time

REPO = pathlib.Path(__file__).resolve().parent.parent
DRIVER = REPO / "driver"
LEDGER = REPO / "runs" / "scored" / "run.jsonl"
FLEET = str(DRIVER / "run_fleet.sh")
SSH = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=15"]

_ledger_lock = threading.Lock()
_attempts_lock = threading.Lock()
_attempts = {}   # iid -> count


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_done():
    """Terminal verdicts already in the authoritative ledger (resume; prereg §3)."""
    done = {}
    if LEDGER.exists():
        for l in LEDGER.read_text().splitlines():
            try:
                r = json.loads(l)
                if r["state"] in ("WIN", "LOSS"):       # INCOMPLETE stays runnable
                    done[r["instance_id"]] = r
            except Exception:
                pass
    return done


def heavy_first(ids):
    """Order longest-expected-first to shorten the makespan tail (LPT intuition). Weight = the §6
    audit's gold-grade secs (committed, deterministic); missing -> median. Affects dispatch order
    only, never the verdict."""
    w = {}
    for f in (REPO / "runs" / "audit" / "shards").glob("audit_*.jsonl"):
        for l in f.read_text().splitlines():
            try:
                r = json.loads(l); w[r["instance_id"]] = r.get("secs", 0)
            except Exception:
                pass
    med = sorted(w.values())[len(w) // 2] if w else 0
    return sorted(ids, key=lambda i: (-w.get(i, med), i))


def box_env(name):
    """Parse /tmp/<name>.env written by provision_box.sh."""
    env = {}
    p = pathlib.Path(f"/tmp/{name}.env")
    if not p.exists():
        return None
    for line in p.read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1); env[k] = v
    return env if env.get("PUBIP") and env.get("KEY") else None


def setup_box(name, restart_max):
    """Provision + ready a box (bash helper). Returns env dict or None after restart_max failures."""
    for attempt in range(1, restart_max + 1):
        log(f"{name}: setup-box (attempt {attempt}/{restart_max})")
        r = subprocess.run(["bash", FLEET, "setup-box", name], capture_output=True, text=True)
        if "READY_" in r.stdout:
            env = box_env(name)
            if env:
                log(f"{name}: READY @ {env['PUBIP']}")
                return env
        log(f"{name}: setup failed — {(r.stdout + r.stderr).strip().splitlines()[-1:] }")
        subprocess.run(["bash", FLEET, "kill-box", name], capture_output=True, text=True)
    return None


def kill_box(name):
    subprocess.run(["bash", FLEET, "kill-box", name], capture_output=True, text=True)


def run_instance(env, iid, ceiling):
    """SSH-run exactly one instance on the box. Returns (rec_dict | None). None = box/transport fault."""
    pem = f"/tmp/{env['KEY']}.pem"
    remote = ("cd ~/swebench-pro && . driver/.proenv && "
              "export PATH=$HOME/.local/bin:$HOME/.npm-global/bin:$PATH && "
              f"env PATH=$PATH $PY driver/pro_run.py --mode run --only {iid} 2>&1")
    try:
        r = subprocess.run(SSH + ["-i", pem, f"ec2-user@{env['PUBIP']}", remote],
                           capture_output=True, text=True, timeout=ceiling)
    except subprocess.TimeoutExpired:
        log(f"  {iid}: instance ceiling {ceiling}s hit — treating as box fault")
        return None
    for line in r.stdout.splitlines():
        if line.startswith("RESULT_JSON "):
            try:
                return json.loads(line[len("RESULT_JSON "):])
            except Exception:
                pass
    return None  # no verdict line: ssh died, box gone, or pro_run crashed before recording


def record(rec):
    with _ledger_lock:
        LEDGER.parent.mkdir(parents=True, exist_ok=True)
        with open(LEDGER, "a") as f:
            f.write(json.dumps(rec) + "\n")


def worker(name, q, max_attempts, ceiling, restart_max):
    env = setup_box(name, restart_max)
    if not env:
        log(f"{name}: could not provision after {restart_max} tries — retiring this worker")
        return
    while True:
        try:
            iid = q.get_nowait()
        except queue.Empty:
            break
        with _attempts_lock:
            _attempts[iid] = _attempts.get(iid, 0) + 1
            n = _attempts[iid]
        log(f"{name}: dispatch {iid} (attempt {n})")
        rec = run_instance(env, iid, ceiling)
        if rec is None:
            # box/transport fault — requeue the instance, recycle the box, keep going
            log(f"{name}: box fault on {iid} — requeue + reprovision")
            q.put(iid)
            kill_box(name)
            env = setup_box(name, restart_max)
            if not env:
                log(f"{name}: reprovision failed — retiring worker (work stays queued)")
                return
            continue
        rec["box"] = name
        if rec["state"] == "INCOMPLETE" and n < max_attempts:
            log(f"  {iid}: INCOMPLETE (attempt {n}/{max_attempts}) — requeue")
            q.put(iid)
            continue
        record(rec)
        log(f"  {iid}: {rec['state']} ({rec.get('secs','?')}s) recorded")
    log(f"{name}: queue drained — terminating box")
    kill_box(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boxes", type=int, required=True)
    ap.add_argument("--eligible", default=str(REPO / "runs" / "audit" / "eligible.txt"))
    ap.add_argument("--max-attempts", type=int, default=2, help="per-instance attempts before recording INCOMPLETE")
    ap.add_argument("--box-restart-max", type=int, default=3, help="provision retries before a worker retires")
    ap.add_argument("--instance-ceiling", type=int, default=36000, help="hard per-instance SSH timeout (s); > worst-case MAX_OUTER*caps")
    args = ap.parse_args()

    elig = pathlib.Path(args.eligible).read_text().split()
    done = load_done()
    todo = heavy_first([i for i in elig if i not in done])
    log(f"eligible={len(elig)}  done={len(done)}  todo={len(todo)}  boxes={args.boxes}")
    if not todo:
        log("nothing to do — ledger already complete"); return

    q = queue.Queue()
    for i in todo:
        q.put(i)

    threads = [threading.Thread(target=worker,
                                args=(f"coord{b+1}", q, args.max_attempts, args.instance_ceiling, args.box_restart_max),
                                name=f"coord{b+1}")
               for b in range(args.boxes)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # summary from the authoritative ledger
    recs = {}
    for l in LEDGER.read_text().splitlines():
        try:
            r = json.loads(l); recs[r["instance_id"]] = r
        except Exception:
            pass
    from collections import Counter
    c = Counter(r["state"] for r in recs.values())
    won = [i for i, r in recs.items() if r["state"] == "WIN"]
    graded = [i for i, r in recs.items() if r["state"] in ("WIN", "LOSS")]
    log(f"DONE — {dict(c)} of {len(recs)} recorded; eligible={len(elig)}")
    log(f"  WINS={len(won)}  graded={len(graded)}  resolve-rate={len(won)/max(1,len(graded)):.3f}")
    missing = [i for i in elig if i not in recs]
    if missing:
        log(f"  {len(missing)} eligible instances unrecorded — re-run coordinator to finish")


if __name__ == "__main__":
    main()
