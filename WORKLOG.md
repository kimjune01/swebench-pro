# swebench-pro worklog — `prereg-pro-v1`

Newest first. This is the **scored-run trail** for the frozen artifact `prereg-pro-v1`. Pre-freeze
development history is in [`WORKLOG_PREFREEZE.md`](WORKLOG_PREFREEZE.md). Per §13, each scored tag
gets its own worklog; this one carries only `v1`'s run.

## 2026-05-27 (later still) — switch to paid API for a time-boxed window (Sonnet on key, codex on sub)

**Decision:** rather than wait out the Max quota grind, the operator dropped a **short-lived
`ANTHROPIC_API_KEY`** (expires ~2026-05-29 03:00, then revert to subscription, same 4-box pace). Plan:
run the scored set on **paid Sonnet + codex-on-sub** until the window closes. Key stored 600 at
`~/.swebench-pro/anthropic.key` (outside repo); validated live (`claude-sonnet-4-5-20250929`). Operator
confirmed the key is short-lived so transcript exposure is acceptable; rotate-after not required.

**Auth-source change is NOT an artifact change → stays v1**, byte-identical (PROCEDURE "Token access"):
auth source isn't part of the frozen artifact, the headline already discloses model+scaffold.

**Plumbing built (operator, not artifact):** `coordinator.py` + `run_fleet.sh` gained `AUTH_MODE=api`
alongside subscription — pushes a 600 key file (not OAuth), `run_instance` exports `ANTHROPIC_API_KEY`
and leaves `CLAUDE_SUBSCRIPTION` unset so `plan_env()` honors the key; codex sub auth untouched.
Subscription path byte-identical (assert refactored into an injected snippet; both modes
simulation-verified to render valid remote bash). The dynamic coordinator's fault-tolerance is retained
(vs the fragile static-shard path) for the unattended window. Committed.

**Canary (DONE — PASS):** 1 box, `AUTH_MODE=api`, 3 quota-paused **flipt** instances → dev ledger
(`runs/dev/canary_api.jsonl`). Plumbing works end-to-end (api provision, key billing, codex-on-sub, full
pipeline, clean teardown). **Confirms the quota-casualty diagnosis:** under healthy tokens these ran
**full-length 885–1378s** (vs 196–374s fast-deaths at the wall) → **2 WIN / 1 LOSS**. flipt-0b119520
flipped LOSS@268s → **WIN@885s**; flipt-05d7234f ran 1378s and genuinely lost. So re-running cleanly
separates quota-casualties from real losses — the reclassification was correct.
**Measured cost: USD 6.21 / 3 = ~$2.07/instance (flipt = light end; ~900–1400s).** Heavy repos cost
more, so blended is higher. Cost read from the Console (regular key can't query the cost API — needs
admin key). Box self-terminated on drain → session logs lost again (3rd teardown artifact-loss; retro:
pull logs before teardown). Canary verdicts stay on the dev ledger; the scored run re-runs those 3.

**Bulk run launched:** 4 boxes, `AUTH_MODE=api`, full eligible → scored ledger, resuming the 680 (354
quota-paused + 326 never-attempted; 48 terminal skipped). Runs until the key window (~2026-05-29 03:00),
then revert to subscription at 4-box pace. Projection: ~250–300 instances in-window ≈ **~$1k–2.4k**.

## 2026-05-27 (later) — PAUSE: Max quota exhausted mid-run → 341 un-run, resume when budget refreshes

**Not a fault — the pre-registered `QUOTA_EXHAUSTED` PAUSE (§4).** After the auth-fix resume (~22:49Z),
the fleet ran ~5.5h and exhausted the Max token budget. The `claude` CLI hit the quota wall and died
empty (48–311s, no output across all stages) — the **same harness mis-recording** as the auth outage:
~341 quota-deaths written as `LOSS ("no verdict endogenous")` instead of PAUSE. This briefly showed an
11.2% resolve rate, which was **garbage** (mostly quota-deaths, not capability).

**Reclassified** (mechanical, output-substance criterion — `state==LOSS AND detail startswith "no
verdict (endogenous)"`): 341 rows `LOSS`→`INCOMPLETE`, `fault=QUOTA_EXHAUSTED`. Backed up →
`run.jsonl.prequota.bak`. Real-output verdicts stand.

**Follow-up investigation (the "13 same-repo fast losses" the operator flagged).** The 16 standing
real-diff LOSSes split on duration: 3 genuine full-length (teleport 2622s@00:58, protonmail
5489s@06:36 + 1015s@07:51, all *healthy regime*) vs **13 flipt at 196–374s, all 08:18–09:41Z**.
Smoking gun = a **fleet-wide temporal regime change**, not instance difficulty: flipt WINs (9) all ran
05:51–07:52 at **764–3025s**; flipt LOSSes (13) all ran 08:18–09:41 at **<400s** — 3× faster than any
flipt win, and **interspersed with the empty-deaths** inside the quota wall [08:01–11:28Z], where
**WIN=0 fleet-wide**. Mechanism: under quota throttling a *light* Go repo (flipt) can limp to a thin
shallow patch (~250s, real diff → graded LOSS) while heavy repos die fully empty. **Same
`QUOTA_EXHAUSTED` fault, thin-output variant.** Reclassified the 13 → INCOMPLETE/QUOTA by the same
verdict-independent window rule (zero in-window wins, so no cherry-picking). The 3 healthy-regime
losses **stand**.

**True state on genuine (quota-healthy) completions: 45 WIN / 3 LOSS = 93.8%** (N=48, skewed to
early-order teleport/protonmail/flipt — NOT a headline). Remaining: **354 quota-paused + 326
never-attempted = 680 to run**.

**Process gap (retro action):** `coordinator.py` checkpoints only verdicts, not captured diffs / agent
logs — so post-teardown the flipt losses were diagnosable *only* from ledger timing/metadata, not the
actual patches. The coordinator must pull per-instance diff + logs to the laptop (echoes the 2026-05-26
heavy-patch teardown loss). Until then, diagnosis leans on the timing trail.

**Resume discipline (§4 QUOTA_EXHAUSTED):** byte-identical artifact, no peek-to-decide, same tag v1,
same order. Diagnosing the fault is not peeking-to-decide (no artifact/order change). **Cannot resume
until Max quota refreshes.** Structural note: 667 heavy instances on one Max sub = a multi-quota-window
grind; cadence needs a decision (see next steps).

## 2026-05-27 — FAULT logged: auth outage (operator re-login) → 32 INCOMPLETE, re-run (§4a)

**Fault class: `AUTH_OUTAGE`** (operator-induced platform fault; verdict-independent). Corroboration:
- **Trigger:** operator got logged out of Claude and re-authenticated (`/login`) mid-run. Max OAuth
  re-login rotates the refresh token, invalidating the tokens pushed to the boxes at setup.
- **Signature:** a cliff at **04:42:39Z**. From then, 32 instances failed with `detail="no verdict
  (endogenous): … craft:[empty] audit:[empty] pilot_done:[empty]"` — **empty output across all three
  stages**, 156–297s each. Before the cliff: full-length loops (WINs 1000–2900s, one genuine 2622s
  LOSS). The agent produced *nothing*, which is the auth-failure signature, not capability.
- **Not difficulty-correlated:** WINs continued as late as 05:11 (boxes on still-valid cached tokens
  completed; only token-*refresh* attempts failed) → the failures track auth, not instance hardness.

**Classification (pre-registered, mechanical, verdict-INDEPENDENT — NOT discretion):** the trigger is
**outage-window membership** — `started_at ∈ [04:42:39Z, 05:29:14Z]` (first..last empty-output start)
→ INCOMPLETE, **regardless of verdict**. This supersedes a first-pass empty-output-only criterion: that
version would have kept in-window WINs while re-running in-window losses — an asymmetry that is exactly
the loss-laundering the §4 anti-cheat forbids. Treating the *whole* window as contaminated and
re-running **wins too** is the verdict-independent version. Re-running the 2 in-window WINs may not
reproduce them; accepting that risk is the cost that keeps the rule honest. Grounded in §13
regression-check #1 (environment-induced results are platform faults, INCOMPLETE not method LOSS).

**Out-of-window terminal verdicts STAND** (clean auth): 23 WIN + 1 LOSS (the genuine 2622s teleport
@ 00:58). Only the documented fault window is re-run.

**Action (§4a recovery, byte-identical artifact, same tag — NOT a v2 restart):**
1. Ledger backed up → `runs/scored/run.jsonl.preauthoutage.bak` (every original verdict preserved).
2. **37 in-window rows reclassified → `INCOMPLETE`** (`fault=AUTH_OUTAGE`, `orig_state`, reclass_note):
   35 LOSS (32 empty + 3 flipt `not resolved`) + **2 WIN**. `load_done()` treats INCOMPLETE as
   runnable → all 37 re-dispatch on resume.
3. Coordinator stopped; creds re-pushed to all 4 boxes from the now-valid keychain; **auth verified
   (`AUTHOK` on coord1)** before resume.

**State at fault:** 61 graded rows → **23 WIN + 1 LOSS terminal (out-of-window), 37 INCOMPLETE
(in-window, to re-run)**. Note for final tally: re-run appends fresh terminal rows; dedupe by
`instance_id` last-wins (as `load_done` does) so the INCOMPLETE rows don't double-count.

## 2026-05-26 — FROZEN: `prereg-pro-v1` cut, scored run begins

**Freeze SHA:** `99536f01fc0f3ac61e7c92a959ef5780ebe05587` (annotated tag `prereg-pro-v1` points
here). Every scored-run artifact cites this SHA.

The §13 pre-freeze gate is cleared (all four items committed): §6 defect list (eligible = 728/731),
batch/sharding driver + fleet, frozen config block, and this §13 self-update + worklog rotation. The
prereg is frozen and `WORKLOG.md` rotated — pre-freeze churn lives in `WORKLOG_PREFREEZE.md`.

**Restart motivation:** none — this is `v1`, the first scored tag. (A future `v2` would open its own
worklog with the failure class that justified the restart, per §3.)

Scored run proceeds on the 728 eligible instances under the frozen config (Sonnet 4.5 generator +
GPT-5.5 craft challenger), whole-set, fixed `tasks/run_order.txt` order, no early stop (§5).
Run/resume events, fault classifications, and the headline land below as they happen.
