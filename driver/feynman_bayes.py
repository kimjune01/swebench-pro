#!/usr/bin/env python3
"""feynman_bayes.py -- Bayesian stopping controller for prereg-pro-v1-feynman.

One arm this run: the STATIC (/ask-feynman) arm. It is paired against the frozen /recon verdicts
(runs/scored/run.jsonl) on the SAME instances; both arms run the SAME Sonnet+codex pipeline, the
ONLY difference is that feynman may not run scoped diagnostic perturbations during diagnosis. So
Delta isolates perturbative abduction. Stratified by perturbation-relevance (tasks/perturbation_strata.tsv).

  driver/feynman_bayes.py status      # per-stratum Delta_perturb + the interaction verdict

ESTIMAND -- Delta_perturb = p_recon - p_feynman, PAIRED (McNemar cells) under Dirichlet(1,1,1,1):
Delta = pi(recon-only-win) - pi(feynman-only-win). Computed SEPARATELY per stratum.

HEADLINE = the INTERACTION, not a global number (prereg-feynman 3):
  - UNDERDETERMINED stratum: perturbation is decision-relevant -> expect Delta_UNDER > 0.
  - DETERMINED stratum (control): cause is static-resolvable -> expect Delta_DET ~ 0 (within ROPE).
The theory in the paper predicts the DIFFERENCE: perturbation earns its keep exactly where the cause
is underdetermined. A uniform Delta across strata would instead say "harness scaffolding helps," not
"perturbative abduction helps." An EXISTENCE case (one UNDER instance recon wins and feynman loses,
with a legible perturbation in recon's trajectory) is itself reportable: it shows a capability the
static arm cannot reach.

  PROVEN-INTERACTION: P(Delta_UNDER > 0) >= 0.95  AND  Delta_DET 95% CI within [-ROPE,+ROPE]
  NULL (per stratum): 95% CI of Delta within [-ROPE,+ROPE], ROPE=0.03
  CONVERGED (per stratum): 95% CI width <= W_TARGET = 0.10
  else CONTINUE -> run UNDER first (front-loaded), then DET control.
"""
import json, pathlib, sys
from collections import defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
SCORED = REPO / "runs" / "scored"
STRATA = REPO / "tasks" / "perturbation_strata.tsv"

MC_SEED = 70720605       # fixed MC seed for the Dirichlet draw (reproducible CI); +1 vs typing run
CI_MASS = 0.95
W_TARGET = 0.10          # 95% CI width target for a per-stratum Delta
ROPE = 0.03              # practical-equivalence band around 0
N_SOFT = 100             # review checkpoint, NOT a cap

# Infra-fault guard (shared with the typing run, ablation_bayes.py): a LOSS faster than MIN_REAL_SECS
# is near-certainly an auth/quota death mis-parsed as LOSS, not a capability loss. The static arm CAN
# legitimately return early (a model that under-utilizes its budget is its own failure mode -- prereg
# allows it), so a fast LOSS here is genuinely ambiguous. Quarantine it (re-run with --redo) rather
# than letting it count: a real static loss reproduces; an infra death does not. WINs never quarantined
# (the official grader cannot pass an empty patch). Verdict-INDEPENDENT on the LOSS side (wall-time only).
MIN_REAL_SECS = 180


def _load_strata():
    if not STRATA.exists():
        sys.exit(f"missing {STRATA} -- run driver/perturbation_strata.py")
    out = {}
    for l in STRATA.read_text().splitlines()[1:]:
        if not l.strip():
            continue
        iid, stratum = l.split("\t")[0], l.split("\t")[1]
        out[iid] = stratum
    return out


def _load_feynman():
    recs = {}
    for p in sorted(SCORED.glob("feynman*.jsonl")):
        for l in p.read_text().splitlines():
            if not l.strip():
                continue
            try:
                r = json.loads(l); recs[r["instance_id"]] = r   # last-wins dedupe
            except Exception:
                pass
    return recs


def _recon_verdicts():
    """Frozen /recon headline verdicts (prereg-pro-v1). Read, never re-run."""
    out = {}
    f = SCORED / "run.jsonl"
    if f.exists():
        for l in f.read_text().splitlines():
            if not l.strip():
                continue
            try:
                r = json.loads(l); out[r["instance_id"]] = r["state"]
            except Exception:
                pass
    return out


def _delta(paired, rng):
    """McNemar 2x2 -> Dirichlet posterior on Delta = pi(recon-only) - pi(feynman-only)."""
    import numpy as np
    a = sum(1 for _, t, u in paired if t == "WIN" and u == "WIN")    # both win
    b = sum(1 for _, t, u in paired if t == "WIN" and u == "LOSS")   # recon-only win (perturb helped)
    c = sum(1 for _, t, u in paired if t == "LOSS" and u == "WIN")   # feynman-only win (perturb hurt)
    d = sum(1 for _, t, u in paired if t == "LOSS" and u == "LOSS")  # both lose
    draws = rng.dirichlet([1 + a, 1 + b, 1 + c, 1 + d], size=200_000)
    delta = draws[:, 1] - draws[:, 2]
    n = len(paired)
    return {
        "n": n, "a": a, "b": b, "c": c, "d": d,
        "mean": float(delta.mean()),
        "lo": float(np.quantile(delta, (1 - CI_MASS) / 2)),
        "hi": float(np.quantile(delta, 1 - (1 - CI_MASS) / 2)),
        "p_pos": float((delta > 0).mean()),
        "p_recon": (a + b) / n if n else 0.0,
        "p_feynman": (a + c) / n if n else 0.0,
    }


def cmd_status():
    try:
        import numpy as np
    except Exception:
        sys.exit("numpy required for the Dirichlet posterior (operator machine only).")
    strata = _load_strata()
    feyn = _load_feynman()
    recon = _recon_verdicts()

    inc = [i for i, r in feyn.items() if r["state"] == "INCOMPLETE"]
    suspect = [(i, r.get("secs", 99999)) for i, r in feyn.items()
               if r["state"] == "LOSS" and r.get("secs", 99999) < MIN_REAL_SECS]
    suspect_ids = {i for i, _ in suspect}
    graded = {i: r["state"] for i, r in feyn.items()
              if r["state"] in ("WIN", "LOSS") and i not in suspect_ids}

    by_stratum = defaultdict(list)
    for i, st in graded.items():
        if i in recon and i in strata:
            by_stratum[strata[i]].append((i, recon[i], graded[i]))

    if suspect:
        print(f"!! INFRA GUARD: {len(suspect)} fast LOSS(es) < {MIN_REAL_SECS}s quarantined "
              f"(suspect infra death -- verify + --redo). secs: {sorted(s for _, s in suspect)}")
    total = sum(len(v) for v in by_stratum.values())
    if total == 0:
        print("no paired graded instances yet (need feynman ledger + frozen run.jsonl).")
        return

    rng = np.random.default_rng(MC_SEED)
    res = {}
    print("=== feynman arm: Delta_perturb = p_recon - p_feynman, per stratum (paired vs frozen /recon) ===")
    print(f"  graded n={total}  (incomplete/retry: {len(inc)})\n")
    for st in ("UNDER", "MID", "DET"):
        pr = by_stratum.get(st, [])
        if not pr:
            print(f"  [{st:5s}] n=0  (none graded yet)")
            continue
        r = _delta(pr, np.random.default_rng(MC_SEED))
        res[st] = r
        print(f"  [{st:5s}] n={r['n']:3d}  2x2(both/recon-only/feyn-only/both-lose)="
              f"{r['a']}/{r['b']}/{r['c']}/{r['d']}  "
              f"p_recon={r['p_recon']:.3f} p_feyn={r['p_feynman']:.3f}")
        print(f"          Delta={r['mean']:+.3f}  95%CI=[{r['lo']:+.3f},{r['hi']:+.3f}]  "
              f"width={r['hi']-r['lo']:.3f}  P(Delta>0)={r['p_pos']:.4f}")

    # Existence case: any UNDER instance recon-won & feynman-lost (a capability the static arm misses).
    ex = [i for i, t, u in by_stratum.get("UNDER", []) if t == "WIN" and u == "LOSS"]
    if ex:
        print(f"\n  EXISTENCE CASE(S) in UNDER (recon win, feynman loss): {len(ex)}")
        for i in ex[:5]:
            print(f"    - {i}")

    # Interaction verdict.
    u, dd = res.get("UNDER"), res.get("DET")
    print()
    if u and dd and u["p_pos"] >= 0.95 and dd["lo"] >= -ROPE and dd["hi"] <= ROPE:
        print(f"  DECISION: STOP - PROVEN-INTERACTION. Perturbation lifts UNDER "
              f"(P(Delta>0)={u['p_pos']:.3f}, {u['mean']:+.3f}) but is null in DET "
              f"([{dd['lo']:+.3f},{dd['hi']:+.3f}]). Perturbative abduction earns its keep exactly "
              f"where the cause is underdetermined -- the paper's claim.")
    elif u and u["p_pos"] >= 0.95:
        msg = (f"  DECISION: UNDER PROVEN (P(Delta>0)={u['p_pos']:.3f}); DET not yet pinned to ROPE "
               f"-- run DET control to close the interaction." if not dd or not (dd["lo"] >= -ROPE and dd["hi"] <= ROPE)
               else "")
        print(msg or f"  DECISION: UNDER PROVEN; DET null. (see above)")
    else:
        per = []
        for st in ("UNDER", "DET"):
            r = res.get(st)
            if not r:
                per.append(f"{st}:no-data"); continue
            if r["lo"] >= -ROPE and r["hi"] <= ROPE:
                per.append(f"{st}:NULL")
            elif (r["hi"] - r["lo"]) <= W_TARGET:
                per.append(f"{st}:CONVERGED")
            else:
                per.append(f"{st}:CONTINUE(w={r['hi']-r['lo']:.2f})")
        print(f"  DECISION: CONTINUE -- {', '.join(per)}. UNDER front-loaded; collect more.")
        if total >= N_SOFT:
            print(f"            [n>={N_SOFT} review checkpoint -- confirm intent to keep going]")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        cmd_status()
    else:
        sys.exit(f"unknown subcommand {cmd!r} (use: status)")


if __name__ == "__main__":
    main()
