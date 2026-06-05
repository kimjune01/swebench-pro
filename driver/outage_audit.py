#!/usr/bin/env python3
"""outage_audit.py -- contamination audit for the feynman ablation (2026-06-05 token outages).

Reproduces the retraction in docs/WORKLOG-untyped.md. The `no verdict (endogenous)` loss type is the
auth-death signature (pipeline dies before the gate). The MIN_REAL_SECS=180 guard caught only the FAST
ones; SLOW (>180s) no-verdict deaths leaked into Delta_UNDER as recon-only wins and inflated the
round-1 UNDER headline. This script recomputes Delta under two contamination-robust rules and prints
the inferred outage windows.

  python3 driver/outage_audit.py

  - VERDICT-TYPE rule (strict): only WIN / "not resolved" count (the gate definitively ran); every
    "no verdict" is dropped as infra. Lower bound on Delta.
  - TIME-CENSORED rule: WIN / "not resolved" always count; a "no verdict" is infra IFF its run interval
    overlaps an inferred outage window, else it is a legit static give-up (counts as a feynman loss).
"""
import json, glob, pathlib, sys
from datetime import datetime
from collections import Counter, defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
SCORED = REPO / "runs" / "scored"
# Round-1 ledgers ONLY for the clean restatement. The round-2 `_of6` batch is quarantined wholesale
# (runs/scored/quarantine_r2_tokenoutage/) -- it ran almost entirely inside outage window W2, and a
# halfway-hit run (outage-truncated craft -> gate grades a broken patch -> false "not resolved") can
# pass as a real loss, so no per-record salvage from it is trusted. Round-1's outage (W1) is a sharp
# ~50-min block with clean runs on both sides, so round-1 censors cleanly.
LEDGERS = ["runs/scored/feynman_*of4.jsonl"]
# Inferred from feynman-death density (>=~100% kill-rate contiguous blocks); padded by 5 min each edge.
WINDOWS = [("2026-06-05T12:55:00Z", "2026-06-05T13:55:00Z"),   # W1: round-1 outage
           ("2026-06-05T16:55:00Z", "2026-06-05T19:25:00Z")]   # W2: round-2 outage


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ") if s else None


def in_window(r):
    s, e = ts(r.get("started_at", "")), ts(r.get("ended_at", ""))
    if not e:
        return False
    s = s or e
    return any(s <= ts(w1) and e >= ts(w0) for w0, w1 in WINDOWS)


def load():
    strata = {}
    for l in (REPO / "tasks" / "perturbation_strata.tsv").read_text().splitlines()[1:]:
        if l.strip():
            iid, st = l.split("\t")[0], l.split("\t")[1]
            strata[iid] = st
    recon = {}
    for l in (SCORED / "run.jsonl").read_text().splitlines():
        if l.strip():
            r = json.loads(l); recon[r["instance_id"]] = r["state"]
    recs = defaultdict(list)
    for pat in LEDGERS:
        for f in glob.glob(str(REPO / pat)):
            for l in open(f):
                if l.strip():
                    r = json.loads(l); recs[r["instance_id"]].append(r)
    return strata, recon, recs


def delta(paired, seed=70720605):
    import numpy as np
    a = sum(1 for _, t, u in paired if t == "WIN" and u == "WIN")
    b = sum(1 for _, t, u in paired if t == "WIN" and u == "LOSS")
    c = sum(1 for _, t, u in paired if t == "LOSS" and u == "WIN")
    d = sum(1 for _, t, u in paired if t == "LOSS" and u == "LOSS")
    x = np.random.default_rng(seed).dirichlet([1 + a, 1 + b, 1 + c, 1 + d], size=200_000)
    de = x[:, 1] - x[:, 2]
    return a, b, c, d, float(de.mean()), float(np.quantile(de, .025)), float(np.quantile(de, .975)), float((de > 0).mean())


def best(recs_i, rule):
    """Pick a feynman outcome for an instance under a rule. Returns 'WIN'/'LOSS'/None(censored)."""
    # prefer a gate-completed record if one exists
    for r in recs_i:
        if r["state"] == "WIN":
            return "WIN"
    for r in recs_i:
        if "not resolved" in r.get("detail", ""):
            return "LOSS"
    # only no-verdict / other records remain
    for r in recs_i:
        if "no verdict" in r.get("detail", ""):
            if rule == "strict":
                return None
            return None if in_window(r) else "LOSS"   # time-censored: out-of-window = legit give-up
    return None


def main():
    strata, recon, recs = load()
    print("=== inferred outage windows (UTC) ===")
    for w0, w1 in WINDOWS:
        print(f"  {w0} .. {w1}")
    for rule in ("strict", "time-censored"):
        print(f"\n=== Delta per stratum -- {rule} rule ===")
        for st in ("UNDER", "MID", "DET"):
            paired = []
            for i, s in strata.items():
                if s != st or i not in recon:
                    continue
                u = best(recs.get(i, []), rule)
                if u is None:
                    continue
                paired.append((i, recon[i], u))
            if not paired:
                print(f"  [{st}] n=0"); continue
            a, b, c, d, m, lo, hi, p = delta(paired)
            print(f"  [{st:5s}] n={len(paired):3d}  2x2={a}/{b}/{c}/{d}  "
                  f"Delta={m:+.3f}  95%CI=[{lo:+.3f},{hi:+.3f}]  P(>0)={p:.4f}")


if __name__ == "__main__":
    main()
