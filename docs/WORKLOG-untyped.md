# swebench-pro worklog -- `prereg-pro-v1-untyped` (typed-mode ablation)

Newest first. Scored-run trail for the frozen artifact `prereg-pro-v1-untyped`: the clean
single-factor ablation isolating the methodeutic typing (`/ask` vs `/recon`). Sibling to the
`prereg-pro-v1` headline; the typed verdicts (`runs/scored/run.jsonl`) are the frozen paired
comparator, read but never re-run. Pre-registration: `docs/PREREGISTRATION-untyped-ablation.md`.

## 2026-06-05 -- INTERACTION emerges (P=0.981, supplementary); DET trends null but ROPE-close is rate-limited

DET control filled to n=26 (`25/1/0/0` -- 25 both-win, 1 recon-only, 0 feyn-only, 0 both-lose).
Per-stratum deltas, paired vs frozen `/recon`:

```
[UNDER] n=32  Delta=+0.278  95%CI=[+0.079,+0.471]  P(Delta>0)=0.9963   PROVEN (pre-registered)
[DET  ] n=26  Delta=+0.033  95%CI=[-0.076,+0.156]  P(Delta>0)=0.7508   trending null, CI not ROPE-pinned
```

**Direct interaction (difference-of-differences), computed post-hoc:**
`Delta_UNDER - Delta_DET: mean=+0.245  95%CI=[+0.015,+0.466]  P(>0)=0.9811`.

**Honesty scorecard (do NOT let this slide into a manufactured PROVEN):**
- Primary `P(Delta_UNDER>0)>=0.95`: **MET** (0.996), pre-registered.
- Pre-registered PROVEN-INTERACTION also requires `Delta_DET 95% CI within +/-0.03`: **NOT MET**
  (CI is [-0.076,+0.156]). The componentwise registered rule is therefore **not formally closed.**
- The **direct difference-of-differences** test (P=0.981) is a reasonable -- arguably better-aligned --
  test of the interaction, but it was **NOT the pre-registered decision rule.** Reported as
  supplementary, clearly labeled, not substituted in to escape the unmet criterion.

**Why the registered close is expensive (the rare-event tail):** DET's CI is governed by its single
discordant pair (effective-n ~ 1 despite n=26). Pinning the discordant proportion's upper bound below
0.03 needs ~100-150 more DET instances -- likely beyond the $10 budget. So the registered ROPE-close on
DET may be unreachable here; the supplementary interaction test is the strongest *honest* statement.

**Methodological note (the registered criterion was win-rate-shaped; the question is attribution-shaped):**
`Delta_DET within ROPE` is a *win-rate-equivalence* test (prove the two arms resolve DET equally). But
the estimand of interest was never a win rate -- it was **attribution** (does perturbation's effect
*differ* by determinacy). The difference-of-differences is the faithful attribution statistic; the
componentwise ROPE rule was a win-rate residue in an attribution-first design. Disclose both; do not
silently swap. The stratified, UNDER-first sampling was already attribution-first by construction
(front-load the discordant-rich cell), consistent with this.

**Decision:** boxes are paid through their watchdog window; let them keep grinding DET (zero marginal
cost) to tighten the interaction CI as far as budget allows. Report final with full disclosure of
registered-vs-supplementary. No new provisioning (budget ~ceiling).

## 2026-06-05 -- FIRST RESULT: UNDER stratum PROVEN (Delta=+0.286, P(Delta>0)=0.996); survived an auth-death wave

**Headline (clean, n=31 UNDER, paired vs frozen /recon):**
```
[UNDER] n=31  2x2(both/recon-only/feyn-only/both-lose)=12/12/2/5  p_recon=0.774 p_feyn=0.452
        Delta_perturb=+0.286  95% CI=[+0.082,+0.483]  P(Delta>0)=0.9963   -> UNDER PROVEN
```
On the underdetermined stratum, removing scoped diagnostic perturbation costs **~29 points** of
resolve rate (0.774 -> 0.452). 12 existence cases (recon won, feynman lost) -- instances a static
"think real hard" diagnosis cannot reach but a perturbing one can. This is the paper's inquiry-frame
claim, vindicated where it predicts: **perturbative abduction is load-bearing exactly where the cause
is underdetermined.** Not the deeper null (mental simulation did NOT suffice); the empirical act of
perturbing pays. DET control still pending to close the interaction (predict Delta_DET ~ 0).

**Auth-death wave, and the guard holding.** Mid-run, an OAuth token rotation (operator `/login`
refreshed local creds) killed the agent EMPTY in <180s on **62 instances** (secs 30-132), recorded as
LOSS. The infra-fault guard (`MIN_REAL_SECS=180`) **quarantined all 62 out of Delta** -- so the n=31
UNDER read above is uncontaminated; the guard did exactly its job. Re-pushed fresh creds to all 4
boxes; recovery confirmed (current instances running 498s/1050s post-push, vs the ~40s death
signature). The wave was a rotation transient, not persistent multi-box contention.

**Two follow-on fixes (runner-side):** (1) resume now treats fast-LOSS (<MIN_REAL_SECS) as
**non-terminal** so the 62 auto-retry on the next pass with good creds (previously LOSS was terminal
-> they'd be quarantined from Delta but never re-run -- a silent hole). Commit `7d3d2e6`. (2) the
per-instance `PINST_TIMEOUT` from the prior entry is live fleet-wide.

## 2026-06-05 -- SCORED RUN hit the NodeBB craft-hang; runner-level per-instance timeout added; relaunched

First scored fleet (4 boxes, full ordered shards) ran clean for ~5h then **3 of 4 boxes wedged** --
each frozen 3-4h on a single heavy-suite instance (NodeBB), zero log output, zero progress. abl1
stayed healthy (9 graded); abl2/3/4 stalled at 3 graded apiece. Total harvested: **18 graded
(12 WIN / 6 LOSS), 0 INCOMPLETE** -- no infra deaths, just the hang.

**Diagnosis: the documented craft-hang, and a missing outer timeout.** Heavy test suites hang the
gate's `docker exec` *below* rung5's per-stage caps (RECON 2000 / CRAFT 3600 / gate 1800, MAX_OUTER 5),
and those caps did not reap the wedged process tree. `feynman_run.py` ran the arm via
`subprocess.run(...)` with **no timeout**, so a wedged `pro_feynman` froze the box indefinitely.
Killing it would have written a *false LOSS* (ran >3h, so the fast-LOSS infra guard can't catch it),
polluting the Delta -- so the wedged instances were never let through as losses.

**Fix (runner-side; harness untouched): `PINST_TIMEOUT` (3600s).** `run_one` now `Popen`s the arm in
its own session, `SIGKILL`s the whole process group on timeout, and `docker kill`s the container the
dead process left wedged on the suite (the runner is sequential per box, so that's safe). A TIMEOUT is
**quarantined, not a LOSS** (a hang is not a capability failure) and **re-runnable**: resume now skips
only terminal WIN/LOSS and auto-retries INCOMPLETE/TIMEOUT. Commit `afd3ad4`, pushed.

**Relaunch.** Terminated all 4 (old runner would re-wedge), staged the 18 verdicts as per-shard resume
checkpoints (`runs/scored/shards/feynman_{i}of4.jsonl`), relaunched a fresh patched 4-box fleet that
resumes past them. Watchdog 420m (~7h -> ~$5.6 more; ~$9.8 total, within the $10 ceiling the operator
green-lit "let them exhaust their budgets if that's what it takes"). With the cap, a hang now costs at
most 60 min + a quarantine instead of wedging a box for the night.

## 2026-06-05 -- PILOT validated the `ask-feynman` arm; classifier ID bug found+fixed; freezing + launching the scored run

Piloted before freeze (the intended order: piloting finds faults). **The pilot earned its keep --
it caught a sampling bug that would have silently zeroed the whole run.**

**Bug: the strata classifier emitted lossy IDs.** First pilot: 3/3 `make_task` `StopIteration` in 2s
each. Root cause -- `perturbation_strata.py` read instance IDs out of Claude's *project-dir* path
encoding (`...recon-instance-flipt-io--flipt-<sha>-d0`), which replaces every `_` with `-`, so it
emitted `flipt-io--flipt-<sha>` instead of the canonical dataset ID `instance_flipt-io__flipt-<sha>`.
`make_task` looks up the canonical ID -> no match -> StopIteration. Two distinct faults: (1) no
dir-form -> canonical mapping; (2) a non-greedy `(.+?)-d(\d)` that truncated any SHA beginning
`d<digit>` (e.g. `flipt-d966...`) at the SHA's own `-d9` rather than the trailing depth marker.

**Fix (runner-side only; harness untouched).** `canonical_map()` re-encodes each `run.jsonl` ID the
same `_`->`-` way and matches (the hex SHA makes it injective); regex made greedy + anchored to the
trajectory filename. Re-ran the classifier: **682 instances classified, zero unmatched**, strata
corrected **UNDER 99 / MID 31 / DET 552** (was a mis-parsed 102/31/533). The ~81% DET share -- Pro's
diagnostically-determined majority -- holds.

**Re-dispatched; the arm validated end-to-end on flipt (the most perturbation-rich UNDER, e=26):**
`make_task` passes, full recon->craft->audit->grade loop in **699s** (real, >> the 180s infra-death
floor), **read-only box enforced (`refusals=1` -- feynman tried to execute once during diagnosis, the
guard blocked + logged it)**, **official verdict WIN**. flipt is a `/recon`-WIN too, so this pair is a
tie cell (no Delta) -- pure apparatus validation, not signal. (Aside worth a footnote: feynman *won*
the hardest UNDER case by reasoning alone after one denied perturbation -- the "perturbative abduction
in its head" outcome the prereg flags as the deeper null. n=1; the scored run decides.)

**Controller built.** `driver/feynman_bayes.py` pairs the `feynman` ledger vs frozen `/recon`,
computes **per-stratum** Delta = pi(recon-only) - pi(feynman-only) under Dirichlet(1,1,1,1), and
prints the **interaction** verdict (PROVEN-INTERACTION = `P(Delta_UNDER>0)>=0.95` AND DET within
ROPE). Flags existence cases (UNDER pairs recon-won/feynman-lost) and shares the fast-LOSS infra guard.

**Prereg finalized (§10 threats added):** CLI-drift disclosed-not-controlled (paired same-instance
Delta is robust to a uniform shift; the interaction would need a *differential-across-strata* CLI
effect to be faked), scoping (mechanism-enriched subgroup, proxy dilutes toward null), and the
pre-freeze classifier fix on the record. Counts synced to 99/31/552.

**Launching the scored run:** freeze `prereg-pro-v1-feynman`, then 4 boxes, ordered shards
(UNDER-first), self-terminating watchdog (~9h -> <=~$7 EC2, under the $10 ceiling). UNDER is the
primary endpoint; boxes roll into MID/DET control as they clear UNDER.

## 2026-06-05 -- PERTURBATION ABLATION registered-ready (`ask-feynman` vs frozen `/recon`); codex-sniffed; pilot next

The successor experiment is designed, codex-red-teamed, and fixed. Prereg:
`docs/PREREGISTRATION-feynman-ablation.md` (tag `prereg-pro-v1-feynman`, not yet cut).

**The cut (Feynman vs Edison).** `ask-feynman` = `/recon` with **scoped diagnostic perturbation
removed, nothing else** (read-only diagnosis box, no gate-run, imagine-don't-execute; Peircean typing
+ emit + craft + gate all identical). Feynman = the Gell-Mann caricature ("write down the problem,
think real hard, write down the solution") = the *static* arm. Edison = the *perturb* baseline (try
the filament) = the frozen `/recon`. **One arm:** we already have the perturb baseline (frozen
`/recon`, 728); we build and run only the deprived static arm and pair against it. Single factor =
scoped diagnostic perturbation; the variable is **actual execution vs mental simulation of it.**

**Strata (frozen, `driver/perturbation_strata.py`).** Scored from `/recon`'s own trajectories by
decision-relevant perturbation (manufactured-diff + re-entry, navigation excluded):
**UNDER 102 / MID 31 / DET 533**. Ordered run list UNDER-first (`tasks/perturbation_sample.txt`).
Prediction = the **interaction**: feynman < recon on UNDER, feynman ~ recon on DET.

**Codex sniff (GPT-5.5) -- skill bugs FIXED.** (1) Leak: "proceed as if your predicted result held"
licensed invented evidence -> now imagined experiments are *predictions, not evidence* (rank
hypotheses, never confirm; the gate confirms). (2) Over-handicap: feynman now explicitly gets the
captured failure output (same symptom recon reproduces) -- deprived of *further experiments*, not of
the symptom. (3) Imagined experiments can't earn *induction* confidence. (4) Removed a "be exhaustive
in reasoning" line that made feynman *more* thorough than recon -- now matched verbatim.

**The CLI-drift confound, and its resolution.** Codex's strongest objection: fresh feynman vs
*frozen* recon could confound perturbation with agent-CLI version drift, and recommended a fresh-recon
arm. We can't pin the old CLI (`claude-code@2.1.150` unsupported). BUT the drift is `2.1.150 ->
2.1.162` -- **15 PATCH releases, same minor line, same Sonnet 4.5 model.** Changelog review: all
UI/UX, `claude agents` (background feature, unused), MCP/LSP, permissions, Windows, telemetry, bug
fixes -- **nothing touches the diagnosis loop, the Bash/Read/Grep tool semantics the harness uses, or
model reasoning.** The two brushing items (explicit Grep/Glob listing; parallel-Bash-failure
isolation) don't apply to our `claude --print --disallowedTools ...` invocation. CLI drift assessed
**negligible on documentary evidence**, disclosed; frozen `/recon` baseline retained (one-arm). A
30-instance fresh-recon calibration stays in the drawer as fallback.

**Scoping caveats on the record (codex #4/#5).** The stratifier selects on `/recon`'s own behavior,
so UNDER is a **mechanism-enriched subgroup** ("where recon used perturbation"), not a random
underdetermined sample. Headline evidence = the **per-pair discordant analysis** (recon-only-wins on
UNDER) -- which is itself the difficulty control (same instance, both arms, difficulty held per-pair).
Claim is scoped to "perturbation recovers instances static reasoning fails, concentrated where it was
used," NOT "perturbation helps all hard cases."

**Separate finding (distinct from the ablation verdict): Pro is diagnostically determined-heavy.**
533/666 (~80%) of Pro instances were resolved by `/recon` with zero scoped experiments -- the cause is
statically readable from the test-vs-code gap. Caveat: this proxies "recon didn't perturb," an upper
bound on "shallow" (a strong model abduces statically even on non-shallow causes). Scope it to
*diagnostic* shallowness, not difficulty (implementation can still be hard -> the 95.3% is real). The
implication: **Pro under-exercises the discovery/perturbation mode the methodeutic is built for** --
which is exactly why this ablation must stratify (the population average would wash the effect out
under 80% ties).

**Status:** skill + strata + prereg + classifier built; `ask-feynman` codex-clean. Next: build
`pro_feynman.py` (read-only diagnosis box + failbase-symptom provision) and run a PILOT on a few UNDER
instances (dev-mode, no-credit) before freezing `prereg-pro-v1-feynman`.

## 2026-06-05 -- SUCCESSOR DESIGN: the perturbation ablation, and a feasibility WIN on stratification

The typing null pointed at the next experiment: not the *names* of the inquiry (form, null) but a
specific *operation* (content). Settled on the cleanest, receiver-bias-immune cut.

**The experiment: `/ask` vs `/ask-static`.** Same skill, same schema, same downstream
(implement + codex + gate + loop), same model. The ONLY change: `/ask-static` may not run **scoped
diagnostic perturbation** -- the cheap experiments that manufacture a discriminating diff to *discover*
the cause (run the failing test for the live trace, drop a print, isolate-by-bypass). It keeps
deduction (trace), static abduction (read the gap), and -- crucially -- **imaginary perturbation**
(it may reason counterfactually about what an experiment *would* show; it just can't run it). So the
variable is precisely **actual execution vs mental simulation of it**, which is the paper's
§inquiry-frame claim ("kill conditions are executions"). Solution-attempting perturbation (craft
testing fixes) is unchanged in both arms, so the ablation stays coherent.

Why clean where the body-swap was dirty (codex red-team, this session): identical handoff shape ->
no receiver bias; one operation varied -> no confound bundle; same implementer/gate -> no mediator
problem. Budget: equal *ceiling*, early-return allowed -- under-utilization is a failure mode of the
static arm, not a confound to launder; identical thoroughness exhortations so an early return means
static inquiry genuinely bottomed out. Theory prediction (the result is the *interaction*):
perturb >> static on **underdetermined-cause** instances, perturb ~ static on **determined-cause**
instances (where the gap already names the cause; flipt/openlibrary-style).

**Feasibility WIN -- perturbation is machine-countable, and the strata are large.** Inspected the
frozen typed `/recon` evidence to build the determinacy stratifier:
- The hgraph `.md` files mostly died at teardown (only 4 survived), BUT the **1,048 pulled recon
  trajectories** carry the *actual execution record* -- a better stratifier than the prose graphs.
- Classified 666 Pro instances by scoped executions in diagnosis: **48% perturbation-rich (>=2 execs),
  40% light, 11% pure-static**; per-instance count runs 0 -> 51 (ansible). Clean gradient.
- Surprise that helps power: the typed run perturbed on **~89%** of instances -- perturbation was the
  norm, not a thin tail, so the underdetermined stratum is ~320 instances, not a sliver.
- Deployment graphs (382) corroborate the signal is real: explicit-experiment 10%, isolation 17%,
  induction-closed 16%, re-diagnose/kill 7%.

**Refinements before freeze (the raw signal is a bit too abundant, which is its own tell):**
(1) sharpen "execution" to *manufactured-diff* perturbation (print-injection / running modified code /
isolating bypass), not navigation runs; (2) stratify on **decision-relevant** perturbation
(re-entry / kill / hypothesis-flip = "perturbation broke a tie"), not raw "perturbation happened" --
89%-perturbed overestimates 89%-needed. Headline stratifier = decision-relevant perturbation.

**Status:** design + feasibility confirmed, NOT frozen. Next: build the sharpened classifier, emit the
pre-registered determined/underdetermined instance lists, draft the `/ask` vs `/ask-static` prereg
(own tag). This is the successor node; the typing artifact (`prereg-pro-v1-untyped`) stays terminal.

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
