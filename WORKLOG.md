# swebench-pro worklog — `prereg-pro-v1`

Newest first. This is the **scored-run trail** for the frozen artifact `prereg-pro-v1`. Pre-freeze
development history is in [`WORKLOG_PREFREEZE.md`](WORKLOG_PREFREEZE.md). Per §13, each scored tag
gets its own worklog; this one carries only `v1`'s run.

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

**Classification (pre-registered, mechanical — NOT discretion):** §13 regression-check #1 states
environment-induced empty output "reads as INCOMPLETE, never a method LOSS." The criterion keyed on is
mechanical — `state==LOSS AND detail startswith "no verdict (endogenous)"` (empty-all-stages) — not on
timing or which losses we'd prefer to re-roll. The 4 genuine `"not resolved"` LOSSes (agent produced a
real diff the grader rejected, incl. 3 flipt *inside* the window) **stand as LOSS**.

**Action (§4a recovery, byte-identical artifact, same tag — NOT a v2 restart):**
1. Ledger backed up → `runs/scored/run.jsonl.preauthoutage.bak` (original LOSS rows preserved).
2. 32 rows reclassified `LOSS`→`INCOMPLETE` (`fault=AUTH_OUTAGE`, `orig_state=LOSS`, reclass_note).
   `load_done()` treats INCOMPLETE as runnable → they re-dispatch on resume.
3. Coordinator stopped; creds re-pushed to all 4 boxes from the now-valid keychain; auth verified
   before resume.

**State at fault:** 61 graded rows → 25 WIN, 4 LOSS (genuine), 32 INCOMPLETE (auth, to re-run). True
rate on genuine completions = 25/29. Note for final tally: re-run appends fresh terminal rows; dedupe
by `instance_id` last-wins (as `load_done` does) so the INCOMPLETE rows don't double-count.

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
