# swebench-pro worklog -- `prereg-pro-v1-untyped` (typed-mode ablation)

Newest first. Scored-run trail for the frozen artifact `prereg-pro-v1-untyped`: the clean
single-factor ablation isolating the methodeutic typing (`/ask` vs `/recon`). Sibling to the
`prereg-pro-v1` headline; the typed verdicts (`runs/scored/run.jsonl`) are the frozen paired
comparator, read but never re-run. Pre-registration: `docs/PREREGISTRATION-untyped-ablation.md`.

## 2026-06-05 -- TERMINAL: CONVERGED, null. Delta_typing = -0.013, 95% CI [-0.062, +0.030] (n=73)

**Result.** The Bayesian run converged at n=73 (prereg §3.2, 95% CI width 0.092 <= W_TARGET 0.10):
`Delta_typing = p_typed - p_untyped = -0.013, 95% CI [-0.062, +0.030]`. 2x2 paired table: both-win 70,
typed-only-win **0**, untyped-only-win 1, both-lose 2. `P(Delta > 0) = 0.25`. 0 INCOMPLETE, 0 infra-guard
quarantines (clean auth/regime throughout). The CI excludes any meaningful positive effect; the point
estimate is null-to-slightly-negative.

**Reading.** The Peircean mode-TYPING of the diagnosis stage (abduction/deduction/induction labels,
confidence-by-mode, typed-node semantics) adds **no measurable resolve-rate lift** over the same inquiry
without it. The strong claim of the paper's abstract / §grounding -- "the encoding is typing" -- is
**falsified at runtime** to within +/-~5 points. The existence case for the typing (a typed-only-win)
did not appear in 73 instances.

**The honest frame (the result's actual content).** The ablation was a **rename refactor**: same function
bodies (reproduce -> abduce -> ground -> rule-out -> defer), new identifiers (generic names for the
Peircean ones). It preserved runtime behavior -> null. NOT a tautology: unlike a compiler, the model
*reads* the names, so a behavior change was possible; the null is the empirical finding that **this model
(Sonnet 4.5, a 2025 model) compiles the vocabulary away** -- it executes the operations specified and is
indifferent to the labels. Model-dependent: a weaker model might lean on the names. The names were
load-bearing for the *author* (Peirce was the lens that produced the function bodies), and inert for the
*runtime* -- which reconciles "Peirce led me to the skill" with "the typing doesn't move the number."
Live-artifact evidence corroborates mechanistically: on easy AND hard instances, the untyped `/ask` arm
produced grounded, evidence-cited, non-confabulated diagnoses; the only losses were gate-divergence
grader artifacts both arms hit.

**What survives / what's next.** Step-separation + context isolation is precedented (Agentless,
Anthropic subagents, LangChain; codex prior-art search). The Peircean typing is null. The candidate claim
that survives both the ablation and the prior-art check is **inquiry CONTENT vs localization** -- the
function *bodies*, not their names: Agentless localizes (points at edit sites), our diagnosis abduces
(grounded falsifiable root cause). That is UNTESTED here (both arms have the content) and is the next
experiment (codex-designed: `OURS_INQUIRY` vs `AGENTLESS_LOCALIZE` vs `ACR_CONTEXT_RETRIEVAL`, neutral
canonical handoff, conditional-on-gold-file analysis; its own prereg).

**Provenance + teardown.** Per-instance artifacts (captured patches, `/ask`+craft+audit outputs, notes,
failbase) pulled off all 8 boxes before teardown -> `runs/scored/artifacts/untyped/` (466 files). Merged
scored ledger committed at `runs/scored/untyped.jsonl` (73 graded). Fleet torn down at CONVERGED per the
prereg stop (census not required; resume-able if a full-set number is later wanted).

## 2026-06-04 (run in progress, ~2h, n=52) -- hard-instance inspection: untyped reasons cleanly; losses are grader-divergence, not confabulation

**Inspected the live `/ask` artifacts on hard instances** (the place the typing would have to earn its keep).
Findings, recorded as the honest trail:
- **No confabulation, easy or hard.** On flipt (easy both-win), qutebrowser (version-conditional config logic),
  and openlibrary (validation-architecture refactor), `/ask` produced grounded, evidence-cited diagnoses with
  ruled-out alternatives and precise edit sites -- the full inquiry loop (abduce -> ground -> eliminate ->
  falsifiable edits) in plain prose, with the Peircean labels stripped. The failure mode the typing is meant to
  prevent (confident confabulation) is not appearing.
- **Both both-lose cases are gate-divergence, not capability misses.** qutebrowser (in-container 6/6 F2P PASSED)
  and openlibrary (35/35 PASSED) both went green in-container and red on the official grader -- the headline's
  documented pytest/django divergence class. The frozen TYPED arm lost both identically, so they are bench/grader
  artifacts both arms hit (concordant, cancel in Delta). The capability-hard tail is thinner than the raw LOSS
  count suggests.
- **The diagnosis stage is Sonnet 4.5 (a 2025 model), no codex.** `RCA_MODEL` UNSET -> default `claude-sonnet-4-5`;
  `untyped_recon` runs `claude(...)`, codex (GPT-5.5) only challenges the patch downstream in craft. So a year-old
  mid-tier model performs the methodeutic inquiry natively, unprompted by typing. Reads as: the typing is
  DESCRIPTIVE of what the model already does, not GENERATIVE of new capability -- and per the staleness note
  (§limitations), newer generators would push Delta toward zero, not away.
- **Still 0 typed-only-wins** at n=52 (1 untyped-only-win, 2 both-lose grader-artifacts). The decisive case
  (typed reliably resolves what untyped reliably can't) has not appeared, and its mechanism (untyped drifting
  where typed's caps save it) is not manifesting.

**Calibration on the record:** prior on "typing carries the lift" is updating down, and now mechanistically (not
just numerically) -- we can watch the model do the inquiry without the labels. NOT yet a verdict: n=52, CI wide,
the capability-hard tail is ~thin and partly grader-noise. Do not over-update to "typing is worthless" any more
than we'd have clung to "typing is the lever." The survivable claim if this holds: structure-as-lever +
Peirce-as-design-rationale/legibility (§411), with the strong §grounding "the encoding is typing" narrowed.

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
