# Quarantined: round-2 DET fill, token-outage-contaminated (2026-06-05)

These six `feynman_{i}of6.jsonl` ledgers are **excluded from all analysis**. They are the round-2
DET continuation (6-box fleet, `tasks/perturbation_control.txt`, DET-first) that ran into a
token/auth outage.

**Contamination signature.** The feynman pipeline printed its `FEYNMAN <instance_id>` header and then
died with **no gate verdict**, recorded as `no verdict (endogenous)` LOSS at 26–256s. A real feynman
loss runs the full Sonnet+codex pipeline and returns `not resolved (refusals=N)` (e.g. the genuine
837s record). Every infra-death paired with a real frozen recon-WIN, manufacturing recon-only cells
and inflating `Delta_DET` to a bogus **+0.64** (`p_feyn=0.317` on the *determined* — i.e. easiest —
stratum, impossible as a real result; clean round-1 DET had `p_feyn=0.971`).

**Why the whole batch, not a filtered subset.** Two guards leaked: `FAULT_RE` doesn't match this
auth-failure string, and `MIN_REAL_SECS=180` only quarantines the *fast* deaths — the 210s/254s/256s
"no verdict" deaths landed as terminal losses. And a run can be hit **halfway** (recon ok, craft dies),
so no per-record secs/pattern rule cleanly separates infra-death from capability-loss. The entire
outage window is therefore discarded.

**Status.** Round-1 (`runs/scored/feynman_{i}of4.jsonl`) predates this outage, shows no signature, and
is intact: UNDER PROVEN `Delta=+0.278`, DET `33/1/0/0`. The DET ROPE-close is still open and will be
refilled on a FRESH fleet in a clean auth window, with the runner hardened to treat `no verdict
(endogenous)` as infra (quarantine + non-terminal retry) regardless of secs.
