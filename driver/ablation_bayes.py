#!/usr/bin/env python3
"""ablation_bayes.py — sample generator + Bayesian stopping controller for prereg-pro-v1-untyped.

One arm this run: the untyped (/ask) arm. The stopping rule and thresholds are pre-registered in
docs/PREREGISTRATION-untyped-ablation.md 3; this file only evaluates them.

  driver/ablation_bayes.py sample      # seed-permute the 728 eligible -> ablation_sample.txt
  driver/ablation_bayes.py status      # Delta_typing for the untyped arm (paired vs frozen typed)

ESTIMAND -- Delta_typing = p_typed - p_untyped, PAIRED against the frozen typed verdicts
(runs/scored/run.jsonl) on the same sampled instances. Both arms run the SAME Sonnet+codex
pipeline; the ONLY difference is the /recon vs /ask skill, so Delta isolates the methodeutic
typing. Built from the 2x2 paired table (McNemar cells) under a Dirichlet(1,1,1,1) posterior;
Delta = pi(typed-only-win) - pi(untyped-only-win). Delta materially > 0 proves the reasoning is
encoded in the typing.

  PROVEN:    P(Delta > 0) >= 0.95                              (typing carries the lift, sign decisive)
  NULL:      95% CI of Delta within [-ROPE, +ROPE], ROPE=0.03  (typing practically zero)
  CONVERGED: 95% CI width of Delta <= W_TARGET = 0.10          (precise middling estimate)
  else CONTINUE -> up to the full 728 census (CI collapses at the population)
"""
import json, pathlib, random, sys

REPO = pathlib.Path(__file__).resolve().parent.parent
ELIGIBLE = REPO / "runs" / "audit" / "eligible.txt"
SAMPLE = REPO / "tasks" / "ablation_sample.txt"
SCORED = REPO / "runs" / "scored"

SEED = 20260604          # prereg-untyped 2.2 -- committed before any data
MC_SEED = 70720604       # fixed MC seed for the Dirichlet draw (reproducible CI)
CI_MASS = 0.95
W_TARGET = 0.10          # 95% CI width target for Delta_typing
ROPE = 0.03              # practical-equivalence band around 0 (typing ~ null)
N_SOFT = 100             # review checkpoint, NOT a cap (tokens $0; continue toward 728 as needed)

# Infra-fault guard (learned from the headline run, WORKLOG.md 2026-05-27..29): auth-token rotation
# and quota exhaustion make the agent die EMPTY in <400s, and the verdict parser mis-records those as
# LOSS. A genuine loss runs the full Sonnet+codex pipeline (headline real losses: 764-3025s). A LOSS
# faster than MIN_REAL_SECS on the untyped arm is near-certainly an infra death, NOT a capability loss.
# Quarantine those out of the Delta table (treat as not-yet-graded, re-run with --redo) so an auth wave
# cannot manufacture false typed-only-wins and inflate Delta. WINs are never quarantined (the official
# grader cannot pass an empty patch, so every WIN is real). Verdict-INDEPENDENT on the LOSS side: the
# rule is wall-time only, never the verdict, so it cannot launder a real loss (re-run reproduces it).
MIN_REAL_SECS = 180


# -- subcommand: sample --------------------------------------------------------
def cmd_sample():
    if not ELIGIBLE.exists():
        sys.exit(f"missing {ELIGIBLE} -- run the 6 audit first")
    ids = sorted(l.strip() for l in ELIGIBLE.read_text().splitlines() if l.strip())  # canonical order
    if len(ids) != 728:
        print(f"WARNING: eligible count = {len(ids)}, expected 728", file=sys.stderr)
    perm = ids[:]
    random.Random(SEED).shuffle(perm)   # fair cross-repo draw, reproducible from SEED
    SAMPLE.parent.mkdir(parents=True, exist_ok=True)
    SAMPLE.write_text("\n".join(perm) + "\n")
    import hashlib
    h = hashlib.sha256(SAMPLE.read_bytes()).hexdigest()[:16]
    print(f"wrote {SAMPLE} : {len(perm)} ids, seed={SEED}, sha256[:16]={h}")
    print(f"first 5: {perm[:5]}")


# -- ledger helpers ------------------------------------------------------------
def _load_untyped():
    recs = {}
    for p in sorted(SCORED.glob("untyped*.jsonl")):
        for l in p.read_text().splitlines():
            if not l.strip():
                continue
            try:
                r = json.loads(l); recs[r["instance_id"]] = r   # last-wins dedupe
            except Exception:
                pass
    return recs


def _typed_verdicts():
    """Frozen typed headline verdicts (prereg-pro-v1). Read, never re-run (prereg-untyped 5)."""
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


# -- status: Delta_typing (paired) ---------------------------------------------
def cmd_status():
    untyped = _load_untyped()
    typed = _typed_verdicts()
    inc = [i for i, r in untyped.items() if r["state"] == "INCOMPLETE"]
    # Infra-fault guard: quarantine fast LOSSes (suspect auth/quota death) out of the graded set.
    suspect = [(i, r.get("secs", 99999)) for i, r in untyped.items()
               if r["state"] == "LOSS" and r.get("secs", 99999) < MIN_REAL_SECS]
    suspect_ids = {i for i, _ in suspect}
    graded = {i: r["state"] for i, r in untyped.items()
              if r["state"] in ("WIN", "LOSS") and i not in suspect_ids}
    paired = [(i, typed[i], graded[i]) for i in graded if i in typed]
    n = len(paired)
    if suspect:
        print(f"!! INFRA GUARD: {len(suspect)} fast LOSS(es) < {MIN_REAL_SECS}s quarantined out of Delta "
              f"(suspect auth/quota death -- verify + --redo). secs: {sorted(s for _, s in suspect)}")
    if n == 0:
        print("no paired graded instances yet (need untyped ledger + frozen typed run.jsonl).")
        return

    a = sum(1 for _, t, u in paired if t == "WIN" and u == "WIN")    # both win
    b = sum(1 for _, t, u in paired if t == "WIN" and u == "LOSS")   # typed-only win (typing helped)
    c = sum(1 for _, t, u in paired if t == "LOSS" and u == "WIN")   # untyped-only win (typing hurt)
    d = sum(1 for _, t, u in paired if t == "LOSS" and u == "LOSS")  # both lose

    try:
        import numpy as np
    except Exception:
        sys.exit("numpy required for the Dirichlet posterior (operator machine only).")
    rng = np.random.default_rng(MC_SEED)
    draws = rng.dirichlet([1 + a, 1 + b, 1 + c, 1 + d], size=200_000)
    delta = draws[:, 1] - draws[:, 2]        # pi(typed-only) - pi(untyped-only) = p_typed - p_untyped
    mean = float(delta.mean())
    lo, hi = (float(x) for x in np.quantile(delta, [(1 - CI_MASS) / 2, 1 - (1 - CI_MASS) / 2]))
    p_pos = float((delta > 0).mean())
    p_typed = (a + b) / n
    p_untyped = (a + c) / n

    print("=== untyped arm: Delta_typing (paired vs frozen typed headline) ===")
    print(f"  paired n={n}  (incomplete/retry: {len(inc)})")
    print(f"  2x2: both win={a}  typed-only win={b}  untyped-only win={c}  both lose={d}")
    print(f"  p_typed(sample)={p_typed:.3f}  p_untyped(sample)={p_untyped:.3f}")
    print(f"  Delta_typing mean={mean:+.3f}  95% CI=[{lo:+.3f}, {hi:+.3f}]  width={hi-lo:.3f}")
    print(f"  P(Delta > 0) = {p_pos:.4f}   [PROVEN >= 0.95]   (ROPE=+/-{ROPE}, W_TARGET={W_TARGET})")

    if p_pos >= 0.95:
        dec = (f"STOP - PROVEN: typing materially carries the lift (P(Delta>0)={p_pos:.3f}). "
               f"The reasoning is encoded in the typing. Magnitude: {mean:+.3f} [{lo:+.3f},{hi:+.3f}].")
    elif lo >= -ROPE and hi <= ROPE:
        dec = (f"STOP - NULL: Delta within the ROPE [-{ROPE},+{ROPE}]. The /ask control matches "
               f"/recon; the typing names nothing the model wasn't already doing. Encoding claim fails.")
    elif (hi - lo) <= W_TARGET:
        dec = (f"STOP - CONVERGED: Delta precise to W_TARGET. Estimate {mean:+.3f} [{lo:+.3f},{hi:+.3f}]; "
               f"report as the result.")
    else:
        dec = f"CONTINUE - CI still {hi-lo:.3f} wide. Collect more (toward the 728 census)."
        if n >= N_SOFT:
            dec += f"  [n>={N_SOFT} review checkpoint -- confirm intent to keep going]"
    print(f"  DECISION: {dec}")


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "sample":
        cmd_sample()
    elif cmd == "status":
        cmd_status()
    else:
        sys.exit(f"unknown subcommand {cmd!r} (use: sample | status)")


if __name__ == "__main__":
    main()
