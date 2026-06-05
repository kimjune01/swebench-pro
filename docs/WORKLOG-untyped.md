# swebench-pro worklog -- `prereg-pro-v1-untyped` (typed-mode ablation)

Newest first. Scored-run trail for the frozen artifact `prereg-pro-v1-untyped`: the clean
single-factor ablation isolating the methodeutic typing (`/ask` vs `/recon`). Sibling to the
`prereg-pro-v1` headline; the typed verdicts (`runs/scored/run.jsonl`) are the frozen paired
comparator, read but never re-run. Pre-registration: `docs/PREREGISTRATION-untyped-ablation.md`.

## 2026-06-04 (run in progress, ~1h) -- early signal leans null/untyped; high-power lens considered and DEFERRED

**Run health.** 8 boxes (`abl1-8`, `m7i.xlarge`, us-west-2), all live, 0 INCOMPLETE, 0 infra-guard
quarantines, no auth wave, no grader hang. Smoke (`ansible`) re-runs as part of shard 1/8 post-freeze.

**Early signal (SOFT, n=34, ~1h).** Paired vs the frozen typed ledger: `2x2 = both-win 32 /
typed-only-win 0 / untyped-only-win 1 / both-lose 1`. `Delta_typing = -0.026`, 95% CI [-0.124, +0.061],
`P(Delta>0) = 0.25`. Recorded as the honest trail, NOT a verdict: n=34, CI is +/-0.09, and only ~2 of
the 34 are hard (non-both-win) instances. But the direction is real and worth stating plainly: so far
the untyped `/ask` arm is doing at least as well as typed, and the existence-proof case (a typed-only-win)
has not appeared while its opposite has, once. The hard tail decides; it is barely sampled.

**Methodology deliberation (recorded BEFORE more data, to keep it honest).** Considered raising power by
importance-sampling the discordant boundary instead of uniform random: McNemar / the Dirichlet posterior
draw all their power from discordant pairs, so ~94% of random trials (both-win) are statistically inert
(effective N = b+c = 1 at n=34). Theory is standard: stratified sampling + Neyman allocation, with
Horvitz-Thompson inverse-probability weights to stay unbiased for the population Delta. Strata pre-computed
from the FROZEN typed ledger (so they predate any targeted run): `S_fail` = 34 typed-LOSS; `S_marginal` =
140 typed-WIN with `secs >= p80 = 1072s` (the hard wins); `S_easy` = 554 (Neyman ~0 allocation).

**Decision: random arm is the headline; existence case pursued, but only the multiplicity-clean way.**
- The HT-weighted stratified **average** is legitimate (unbiased for the SAME population Delta; it buys
  precision, never direction -- it cannot turn a null positive). Held as a budget-triggered amendment
  option, NOT registered/run yet.
- An **existence case** (one instance where typed reliably resolves what untyped reliably fails) is a
  worthwhile minimum goal -- BUT it is only honest with **denominator disclosure**. The silly version
  screens `S_marginal` and reports the one that worked (selection on outcome; ~7 false witnesses expected
  in 140 at alpha=0.05). The clean version, on the record before any targeted run:
  - **Primary candidates are the typed-only-wins the unbiased random arm surfaces** (not outcome-selected).
    Each is escalated to a per-instance SPRT (typed k/k vs untyped 0/k confirms it isn't sampling variance).
  - **Any targeted candidates are pre-named before testing, and ALL tested instances are reported** -- the
    claim is scoped to "W of K tested," never a lone cherry-picked witness. Targets (from `S_marginal`)
    to be pre-named in a later dated entry, with their full outcomes.
- Principle on the record: **no sampling design moves the estimand.** If the unbiased random arm does not
  clear a positive statsig Delta, the *average* claim ("typing carries the lift") is dead and the Peirce
  section narrows to design-rationale + legibility (the paper's own §411). An existence case, if found
  clean, supports only the *narrower* claim ("the typing does real work on >=1 instance"), with its
  denominator -- it does not resurrect the average.

**Action.** Keep the random arm running to a §3.2 terminal verdict; report then. Auto-flag every
typed-only-win as it appears (primary clean candidates) for SPRT escalation. Pre-name any `S_marginal`
targets in a dated entry before testing them, and report the full denominator. The stratified HT-average
lens stays registered-but-unrun, available only if budget binds before convergence.

## 2026-06-04 -- FREEZE: `prereg-pro-v1-untyped` cut, ablation run begins

**What this run measures.** `Delta_typing = p_typed - p_untyped`, paired on a seeded-random sample
of the 728 eligible. The untyped arm is the full headline pipeline (Sonnet 4.5 generator + GPT-5.5
codex challenger + deterministic gate + outer loop) with **one factor removed**: the `inquire`
stage runs the `/ask` skill (same diagnosis goal, no applied epistemology) instead of `/recon`
(Peircean abduction/deduction/induction, typed hypothesis graph, confidence-by-mode). Everything
else is byte-identical. If `Delta` is materially positive, the typing encodes reasoning (the paper's
central promise); if `Delta ~ 0`, the encoding claim fails. The answer is the answer.

**Single-factor diff, audited.** `/ask` = `/recon` minus exactly three things (mode labels,
confidence-by-mode, typed graph nodes), identical in goal, process, `git log` blame, suspect-set
pruning, imperative phases, and handoff shape. Codex-sniffed twice (GPT-5.5): first pass flagged
non-typing confounds (`/ask` was missing `git log`, softer pruning, lower procedural force); all
fixed; second pass confirmed *"Delta is now a clean measurement of the typing intervention alone."*
The demand-characteristic self-reference was then stripped so `/ask` reads as a plain standalone
skill, symmetric with `/recon`. `/ask` lives in the repo as a real file (skeptics get a real copy).

**Frozen harness untouched.** The measurement contract (`pro_pilot` setup/gate/capture/grade,
`rung5` craft/audit, `skills/recon|craft|audit`) is byte-identical and unmodified -- `git status`
clean. The new code is the arm (`pro_untyped.py`, imports the frozen harness, swaps only the skill)
and the runner (`ablation_run.py`, `ablation_fleet.sh`, `ablation_bayes.py`).

**Sample.** Seeded-random draw of the 728 eligible, `seed=20260604`, `sha256[:16]=a6e6a099d4660d49`,
`tasks/ablation_sample.txt`. Fair across all 11 repos. 728/728 pairable against the frozen typed
ledger (694 WIN / 34 LOSS = 95.3%).

**Bayesian stopping (estimation, not test).** Dirichlet(1,1,1,1) on the 2x2 paired table;
`Delta = pi(typed-only-win) - pi(untyped-only-win)`. Stop on PROVEN `P(Delta>0) >= 0.95` / NULL
(95% CI within +/-0.03) / CONVERGED (95% CI width <= 0.10); else continue to the 728 census. Tokens
are subscription/$0, so `n` is open. Pre-data prediction (recorded, not a prior): `Delta` small and
positive (~2-8 pts), since `/ask` keeps codex + loop and lands high.

**Infra-fault guard (learned from the headline run).** `ablation_bayes.py` quarantines any untyped
LOSS faster than `MIN_REAL_SECS=180s` out of the `Delta` table (auth-rotation / quota deaths die
empty in <400s and the parser mis-records them as LOSS; a real loss runs 764-3025s). Verdict-
independent, so it cannot launder a real loss. WINs never quarantined (the grader cannot pass an
empty patch). Fast-LOSS clusters trigger the `PROVIDER_CRED_REJECT` runbook (halt -> re-push creds
-> `--redo`).

**Smoke (pre-freeze, no-credit telemetry).** 1 box, 1 instance (`ansible-be2c376a`): the untyped
pipeline ran end-to-end (`/ask` -> craft+codex -> gate -> official grade) and resolved **WIN @ 777s**
(healthy regime). Validates fleet install + Max/codex auth + the skill swap + the grade path. The
result is NOT counted toward the scored `Delta` (the post-freeze fleet re-runs ansible).

**Run plan.** <=8 EC2 boxes (`m7i.xlarge`, us-west-2), `ablation_fleet.sh provision 8`, monitor via
`ablation_fleet.sh delta` until a terminal verdict, pull trajectories + diffs before teardown.

**Freeze tag:** annotated `prereg-pro-v1-untyped` points at this commit.
