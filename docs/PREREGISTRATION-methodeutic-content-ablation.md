# Pre-registration — SWE-bench Pro, methodeutic-content ablation (`methodeutic` vs `generic-rigor` vs `minimal`)

Tests whether the **methodeutic content of the framing prose** is the causal ingredient in the
harness's lift, or whether generic good prompting explains it. Successor to the perturbation ablation
(`prereg-pro-v1-feynman`) and the typing null (`prereg-pro-v1-untyped`). Ships under the shared Zenodo DOI.

**This is a MECHANISM paper; the benchmark numbers are already established.** The 95.3% headline is done,
graded, and published — this study does NOT re-prove a rate. It asks *what operation produces the lift*.
That reframing sets the evidence hierarchy: a mechanism is established by **deductive necessity proofs**
(this operation reaches outcomes its absence cannot) and **exhibited process** (the operation is visible,
in execution, in the trace) — not by a confidence interval on a win rate. The prior round proved the win-
rate Δ is the *weakest* instrument here: it bottomed out at "suggestive" against the benchmark's own
resolution floor (`prereg-pro-v1-feynman` recovery: UNDER Δ=+0.105, CI straddling zero, n capped at ~99).
So this prereg is **tiered**: cheap deductive/constructive evidence first (and sufficient to carry the
paper), expensive statistics last and explicitly *corroborative*, run only if budget and Tier-1 results
warrant. We do not spend a fleet to estimate a magnitude the benchmark cannot resolve.

**Status: DRAFT, not yet frozen.** Freezes only when (a) the perturbation recovery has landed [DONE,
2026-06-05], (b) the three prompts are line-matched and committed with hashes, and (c) the behavioral-
signature rubric is written. Nothing below is run before the freeze tag exists.

## 0. What this tests (the keystone, not one more component)

The prior ablations established a stack: Peircean **labels** are null (`prereg-pro-v1-untyped`,
Δ=−0.013); directed **perturbation** (executed vs imagined diagnostic experiment) is small and
conditional (`prereg-pro-v1-feynman`), and — critically — its static arm was *imagined*-methodeutic,
not non-methodeutic, so it never tested inquiry-vs-not. What remains untested is the thing the theory
most depends on: **the methodeutic content of the prose itself** — the epistemic stance installed by
the framing ("maintain rival hypotheses," "a fix is unconfirmed until you've tried to kill it,"
"choose tests for their discriminating power"), centered on **abduction**.

This is not one component among many. Decompose the Peircean triad as the harness instantiates it:
**abduction** = generate and *hold* rival hypotheses; **deduction** = derive what each predicts
(discriminating tests); **induction** = test and revise commitment between rivals. Deduction and
induction *in their generic forms* (predict what a fix does, run it, revise on failure) are exactly
what careful engineering already does. The part generic rigor lacks is the **hypothesis space** —
maintaining rivals against premature commitment instead of committing to the first plausible cause.
That is abduction, and it is the methodeutic-distinctive content. Ablating it does not subtract a
parallel part; it removes the keystone and the frame collapses to generic rigor (discriminating tests
have nothing to separate; between-rivals revision has nothing to revise). **So "is methodeutic content
load-bearing" reduces to "does abduction-maintenance beat generic rigor at matched compute, staging,
and tools."** That is the experiment.

**The goal is a clean three-way attribution.** The experiment exists to assign the lift to exactly one of:

- **(A) inquiry framing** — M ≫ G: the methodeutic content is the active ingredient (the thesis).
- **(B) generic rigor** — M ≈ G, both ≫ T: the lift is *inquiry disposition*, elicited by any rigorous
  framing; Peircean specificity is not load-bearing. The credit relocates, honestly.
- **(C) the scaffold, not the prose** — T ≈ M ≈ G: **the real surprise.** A one-line task ("resolve the
  issue, pass the tests") elicits the same performance as either elaborate frame, so the framing prose
  is nearly inert and the lift lives entirely in the held-constant factors — staging, tools, gate-retry,
  models. This is the most deflating outcome for a prose-centric thesis and the most striking standalone
  finding: prompt content barely matters when the scaffold is strong. It is the limit case of the
  typing-null and the imagined-inquiry results — the inquiry so internalized that even the framing is
  redundant — and a separate structure ablation would then decompose *which* scaffold factor carries it.

The typing null gives outcomes (B) and (C) a non-trivial prior (the model already did the inquiry
without the labels). The design is falsifiable by construction: the strong thesis (A) can lose to either
(B) or (C), and all three are pre-committed clean findings (§4). T is therefore a co-equal arm, not a
floor.

## 0b. The tiers — cheap deductive evidence first, statistics last and corroborative

Each claim is matched to the *cheapest instrument that can actually establish it*. Necessity and
existence are deductive/constructive — one airtight case settles them, no n, no CI. Comparison and
magnitude are irreducibly statistical and (here) resolution-capped. We run the tiers **in order** and
stop when the paper's mechanism claim is carried; the statistical tier is corroboration, not the spine.

| tier | claim | instrument | cost | gates next tier? |
|---|---|---|---|---|
| **T1 — necessity** | directed perturbation reaches bugs static inference cannot | **existence proof + K-reps**: run the static arm K times across ≥2 models on each of the 9 gate-confirmed existence cases; K/K static failure + perturbation success = deductive necessity | ~9 instances × K reps; no fleet | sufficient alone for the *necessity* claim |
| **T2 — mechanism exhibited** | the model performs abduction (holds rival hypotheses, manufactures discriminating tests, revises commitment) | **trace exhibition**: read the committed `/recon` trajectories, exhibit the hypothesis graph + the discriminating experiment + the revision, per case; blind-rate the behavioral signature | reading committed traces; ~0 compute | carries the *mechanism* claim |
| **T3 — comparison (corroborative, optional)** | methodeutic framing beats generic rigor (M vs G vs T) | **statistics**: the 3-arm paired Δ from §2–§5 | ~310 fresh runs; **resolution-capped** (UNDER ≤~99, resolves only Δ≳0.13) | only if budget allows AND a comparative claim is needed |

**T1 + T2 are the paper.** Necessity (T1) proves directed perturbation is *required* on a characterizable
class; mechanism-exhibited (T2) shows the abductive operation *in execution*, which no win-rate can show.
Together they discharge "methodeutic inquiry is the mechanism" at the level a mechanism paper owes —
**constructively, not statistically** — and they cost a handful of reps + trace-reading, no fleet.

**T3 is corroboration, scoped and capped.** The comparative claim ("Peircean content beats generic
rigor") is the only one that *needs* a population, and the benchmark cannot resolve it below Δ≈0.13. So
T3 runs ONLY if (a) budget is free and (b) a reviewer would demand the head-to-head; it is reported as
supporting, never as the headline, and its resolution limit is stated up front (§4b). If T3 is not run,
the paper stands on T1+T2 and says so. **Do not let T3's expense or its inevitable "suggestive" verdict
gate the mechanism claim** — that inversion (statistics as spine) is exactly what the feynman round
showed to be the weak move.

**The bench is a representative sample, not the territory — so breakdowns are signposts, not verdicts.**
SWE-bench Pro is an *attempt at a representative sample* of software tasks; it is not the object of
study. Two consequences. (1) Finer within-bench statistics over-index on the proxy: chasing decimals on
a sample's stratum is measuring the sample, not the mechanism — another reason T3 is corroborative, not
load-bearing. (2) The *useful* product of any delta breakdown is **generalization-suggestive**: a
stratum where perturbation bites (underdetermined cause, blind search exhausted) is a *signpost* toward
where the mechanism should matter in use cases **outside this bench** — debugging regimes that are
underdetermined-cause-heavy (concurrency, heisenbugs, integration failures, root-cause-unknown
production incidents). The breakdown's value is hypothesis-generating for the broader domain, reported
as "this points to where it would matter," explicitly out-of-sample, never as a within-bench effect
estimate. That is the proper job of a mechanism paper: locate the phenomenon and point at where it
generalizes, leaving the magnitude to whoever studies those domains directly.

**How + when generalize; attribution does not — and real life is dirtier, which favors how+when.** The
attribution breakdown is the *least* transferable product: it is a property of this clean, curated,
oracle-bearing sample. Real deployment is dirtier — noisy signals, no test oracle to stop on, multiple
interacting faults, no pre-classified strata. Across that gap the percentages do not survive, but two
things do: the **mechanism** (HOW it works — hold rivals, manufacture a discriminating experiment,
revise on the evidence) and the **activation condition** (WHEN it works — the cause is underdetermined
and blind search has been exhausted). Those are invariant; the 6%-vs-94% split is sample-bound. So the
paper's transferable contribution is *how + when*, demonstrated (§0a centerpiece) and bounded (§0c
necessity), NOT the attribution magnitude. Dirtier real-world conditions make this *more* true, not
less: the messier the environment, the more a reader needs the operating mechanism and its trigger, and
the less a clean-sample percentage tells them. Lead with how-and-when; let attribution be a footnote
about one sample.

**Honest guard on T1 (existence is seductive).** Existence proofs always come out "in favor" — you need
only one. So every T1 claim ships with its scope: "perturbation is necessary on *these* cases," never
"perturbation explains the lift." A non-empty class is not a large class and not the mechanism behind the
headline rate. Bound the necessity claim exactly as the 9 cases are bounded; state both the strength and
the narrowness.

## 0a. [THE CENTERPIECE — run first, ~0 compute] The side-by-side reasoning exhibit

The single artifact that carries a mechanism paper: a **two-column side-by-side on the SAME instance** —
the static (`ask-feynman`) arm's reasoning trace in one column, the perturbing (`/recon`) arm's in the
other — chosen from the existence cases (recon won, static lost) so the *outcome* difference is real and
the *reasoning* difference is visible. The reader sees, directly:

| static reasoning (lost) | perturbing reasoning (won) |
|---|---|
| commits to a plausible cause from reading alone | holds ≥2 rival causes |
| predicts what an experiment *would* show | runs the experiment that discriminates them |
| fix addresses the imagined cause | revises to the cause the evidence actually selected |
| gate: not resolved | gate: resolved |

**Why this is sufficient for a mechanism paper.** The job of a mechanism paper is to show a phenomenon is
**real, legible, and worth further exploration** — not to bound its effect size. A vivid same-instance
contrast does exactly that: it exhibits the abductive mechanism operating, on a case where its absence
demonstrably failed, in a form a reader can verify by eye. No CI, no n, no fleet. One or a few such
exhibits *is* the result; everything below (necessity K-reps, statistics) is optional hardening, not the
deliverable. This is the cheapest and strongest evidence we have, and it should lead the paper.

**Honesty bounds (so the exhibit is evidence, not anecdote):** (1) the cases are real gate-confirmed
existence cases, IDs frozen, traces committed and reproducible; (2) present them as "here is the mechanism
operating, worth investigating," scoped to the class — never "this explains the lift"; (3) show a
*representative* case and disclose how many existence cases the pattern holds across (the m/9 from §0c),
not a hand-picked outlier; (4) if a case's contrast is ambiguous on inspection, say so — a clean negative
exhibit (static and perturbing reasoned similarly yet diverged) is itself informative.

## 0c. [TIER 1 — optional hardening] Necessity protocol (existence + K-reps)

**Instances.** The 9 gate-confirmed UNDER existence cases from the feynman recovery (recon won; the
static `ask-feynman` arm ran the full pipeline and the official gate confirmed a genuine failure — not
auth artifacts). IDs frozen from `runs/scored/feynman_*` at the `prereg-pro-v1-feynman` recovery SHA.

**Protocol.** For each case, run the **static-deprived arm** (read-only diagnosis, no perturbation) `K`
times (pre-commit `K=5`) across **≥2 models** (Sonnet 4.5 + one other), holding craft/audit/gate fixed.

**Deductive close (pre-committed):**
- **NECESSITY ESTABLISHED for a case** iff static fails **K/K across both models** AND directed
  perturbation (the frozen `/recon`) resolves it. Logic: "K independent static attempts across models
  cannot reach this fix; the perturbing arm does" → execution of a discriminating experiment is
  *required*, not merely helpful, on that instance. This is a proof by construction, not an estimate.
- **CASE RETRACTED** iff static succeeds on any rep — then it was never an existence case (static *can*
  reach it; the round-1 win was variance). Honest: a retracted case strengthens the surviving set.
- Report **m/9 cases with necessity established**, each with its K×model fail record. The claim is
  exactly "directed perturbation is necessary on these m instances," scoped, no extrapolation to the rate.

**Cost.** 9 × K × (#models) static runs ≈ 9×5×2 = 90 short runs, single box, no fleet. K reps also give a
free read on static-arm *variance* (does it fail reliably or flakily), which itself is mechanism evidence.

## 0d. [TIER 2 — run second] Mechanism-exhibition protocol (trace, ~0 compute)

**Source.** The committed `/recon` trajectories (`fc_hgraph_*` / recon emit logs) for the surviving
necessity cases and a stratified sample of UNDER wins. No new runs.

**Exhibit, per case** (the abductive signature made visible):
1. the **hypothesis graph** recon constructed (≥2 rival causes held simultaneously),
2. the **discriminating experiment** it manufactured (the perturbation chosen to separate the rivals,
   not to confirm one),
3. the **revision** — commitment moving to the surviving hypothesis after the experiment landed.

**Blind signature rating (pre-committed rubric, written before reading any trace; see §5):** distinct
live hypotheses before commitment; discriminating-test rate; revision-after-contrary-evidence rate;
premature-commit ("first green → stop") rate. Raters blind to provenance. A case **exhibits the
mechanism** iff all three of (1)–(3) are present in the trace and the signature scores positive.

**What T2 buys.** It shows the inquiry operating *in execution* — the Peircean abductive move, performed,
on a bug that needed it. For a mechanism paper this is stronger than any Δ: you are not estimating how
often the mechanism helps, you are exhibiting what it *is* and showing it on a case T1 proved it was
*needed*. T1 (it was required) + T2 (here it is, operating) is the constructive core.

## 1. Import

Inherits every discipline from `PREREGISTRATION.md` at the `prereg-pro-v1` SHA (predicate, two-mode
state machine, eligible denominator 728, provenance, freeze), the **infra-fault guard** and the
**post-outage hardening** from the feynman run (`no verdict (endogenous)` = INFRA → non-terminal retry,
verdict-type not wall-time; see `docs/WORKLOG-untyped.md` 2026-06-05 retraction). Deltas below override
only what is named.

## 2. [TIER 3 — corroborative, optional] The three arms — one factor varied (framing-prose content), everything else held fixed

*Sections 2–5 specify the statistical comparison tier. Run only per the §0b gate (budget free AND a
comparative claim demanded). Resolution-capped; reported as supporting, never headline.*

The manipulated variable is the **content of the framing prose ONLY**. Staging (recon → craft → audit
boundaries and externalized artifacts), models (Sonnet generator + GPT-5.5 critic), compute/token
budget, tool access, perturbation permissions, gate, seeds policy, and instances are **identical
across all three arms.** This isolates content from structure (the structure ablation is a separate
run); here structure is a held-constant covariate.

| arm | framing-prose content |
|---|---|
| **M — methodeutic** | the full inquiry frame: maintain multiple rival hypotheses; choose tests for *discriminating power between rivals*; treat a passing fix as unconfirmed until you've tried to kill it; revise commitment between rivals as evidence lands. (= the frozen `/recon` content.) |
| **G — generic-rigor** | steelmanned generic engineering: reproduce, read-before-write, localize, root-cause, smallest-fix, test-and-verify, regression/edge-case checks, revise-on-failure — **without** rival-hypothesis maintenance, discriminating-tests-between-rivals, or organized self-refutation. |
| **T — minimal** | task-only floor: resolve the issue, satisfy the test suite, report what changed. |

**Operational boundary (the manipulated variable, made precise).** The line between G and M is the
operational definition of "methodeutic content," authored by codex (a third party, so the experimenter
cannot sandbag the control — see §6). Allowed in G: reproduce, read-before-write, localize, root-cause,
plan, test/iterate, regression/edge-case checks, second-pass QA, revise-on-failure, smallest-fix.
**Exclusive to M (deny-list for G):** maintain multiple rival explanations simultaneously; compare
hypotheses against each other; choose tests *because they discriminate among rivals*; frame work as
trying to *kill/falsify* the fix; update commitment *between rivals* as evidence lands; seek
disconfirming evidence *as such*. The three smuggling hazards to police (where the control accidentally
becomes methodeutic): "consider alternative causes," "challenge your fix," "design decisive tests" —
each has an allowed (generic) and forbidden (methodeutic) phrasing committed in the control design doc.

**Pairing.** M = the frozen `/recon` harness (verdicts in `runs/scored/run.jsonl`, read not re-run);
G and T are the two new arms, paired per-instance against M (paired McNemar, same machinery as the
feynman run). CLI drift between frozen M (2.1.150) and fresh G/T (2.1.165) is disclosed, not
controlled (§11), consistent with the feynman run; a reader who rejects it can discount the absolute
levels — the paired same-instance Δ and the M≫G≫T *ordering* are robust to a uniform CLI shift.
Optional cleaner variant if budget allows: run M fresh alongside G/T on identical CLI.

## 3. Sampling — reuse the pre-treatment strata, ordered

Reuse the **pre-treatment** cause-determinacy strata from `tasks/perturbation_strata.tsv`
(re-entry OR experiments≥2 → UNDERDETERMINED), read off the frozen `/recon` trajectories, never off
any arm's outcome — no collider. UNDER-first ordering. Primary endpoint scoped to the strata, not
"all of Pro." The theory predicts the methodeutic advantage concentrates on UNDER (where holding a
hypothesis space matters) and vanishes on DET (statically determined).

## 4. Estimands and the pre-committed decision table

Per stratum, paired Dirichlet(1,1,1,1) on the 2×2, same as the feynman run:
- **Δ_MG = p_M − p_G** (primary — does methodeutic content beat generic rigor?)
- **Δ_GT = p_G − p_T** (does rigor priming help at all over the floor?)
- **Δ_MT = p_M − p_T** (total content effect over the floor.)

**Pre-committed fatal threshold (the kill condition for the strong thesis).** Methodeutic content is
load-bearing iff **Δ_MG ≥ +0.02 overall OR ≥ +0.05 on the UNDER slice, with consistent direction
across seeds, AND the behavioral signature (§5) is higher in M than G.** If Δ_MG's 95% CI sits within
the ROPE (±0.03) on both overall and UNDER **and** the signature does not differ, the strong thesis is
**rejected**: methodeutic-specific content is decoration or generic priming.

**Decision table (committed before running; every cell is a clean finding):**

| outcome | reading |
|---|---|
| **M ≫ G ≫ T**, signature M>G | **Peircean methodeutic content is load-bearing** (strong thesis confirmed). |
| **M ≈ G ≫ T** | inquiry *disposition* is load-bearing, Peircean *specificity* is not — relocate the credit (humbler, still clean). |
| **M ≈ G ≈ T** | framing content is decoration; the lift is structure/compute, not prose. |
| **M ≫ G, signature flat** | win-rate effect without behavioral mechanism — suspect a confound (length/forcefulness leak); investigate before claiming. |

Ordered stopping as in the feynman run (PROVEN / NULL / CONVERGED per stratum); UNDER front-loaded.

## 4b. Power & sample size (capped by the benchmark, not by budget)

The informative cases are UNDER (where M and G can diverge); DET is informationless for this contrast
(both arms solve determined causes, effective-n ≈ 0 — the lesson from the feynman DET stratum). **UNDER
is capped at ~99 instances** — the entire pre-classified stratum. You cannot manufacture more without
re-running recon to classify new instances, which would break the pre-treatment property. So the
win-rate primary is **power-capped by the benchmark**, and the honest numbers are:

- ~99 UNDER, with a plausible M-vs-G discordant rate 0.1–0.2, gives a 95% CI half-width of **±0.05 to
  ±0.09** on Δ_MG.
- **Detects** Δ_MG ≳ **0.13** at P>0.95 (Bayesian early-stop fires well before 99 if the effect is large,
  the way the feynman UNDER cleared P>0.95 by n≈30).
- **Cannot resolve** a small effect (Δ_MG ≈ 0.05) — indistinguishable from zero at this n.
- **Cannot prove the tight ROPE null** (±0.03) — that needs ~200–850 UNDER, beyond the stratum. Do not
  chase it (the DET-ROPE-close mistake). "No large effect on UNDER" is the informative negative.

**The behavioral signature carries the power when M≈G (the modal case).** Win rate is binary and
discordant-pair-limited; the signature (live-hypotheses count, premature-commit rate, discriminating-test
rate) is continuous and per-instance, so a difference in inquiry *behavior* is detectable at **~40–50
blind-rated traces per arm** even when the win-rate Δ is too small to resolve. The signature is what
separates outcomes B and C and surfaces the internalized-inquiry finding (§5).

**Sample plan.** Per arm: up to ~99 UNDER (Bayesian early-stop) + ~31 MID + ~25 DET (null-anchor +
outage tripwire) ≈ **~155 instances**. Two new arms (G, T); M is frozen `/recon` → **~310 fresh runs**.
Trace rating: ~40–50 per arm, stratified, blind to condition. **Disclosed limit:** the win-rate primary
resolves only Δ_MG ≳ 0.13 on UNDER; below that it is indeterminate by score, and the behavioral
signature is the deciding measure. This is a property of a mostly-easy benchmark, stated up front, not a
weakness to bury.

## 5. Behavioral signature — load-bearing vs internalized

Win rate alone cannot distinguish "methodeutic content adds behavior that wins" from "the model
abduces anyway and the prose is inert." So a **pre-defined, blind-rated behavioral signature** is a
co-primary outcome. Rubric (written and committed *before* any trace is read):
- distinct live hypotheses maintained before commitment,
- rate of discriminating-test proposals (tests chosen to separate rivals, not confirm),
- rate of commitment revision after contrary evidence,
- "first fix passed a visible test → stop" rate (premature commitment),
- audit catch rate for false-positive fixes.

Raters (independent humans and/or a model grader) score a stratified sample of traces **blind to arm**
(Prompt A/B/C). Interpretation: if the signature is high in **all** arms — including T — the model does
the inquiry regardless of framing (the **deeper null**: abduction internalized, echoing the typing-null
and the imagined-inquiry finding), which is reported as such, not buried.

## 6. Bias guards (the experimenter authors the prompts — maximum bias leverage here)

- **Pre-register everything before running:** the three prompts (frozen, hashed), hypotheses, metrics,
  strata, the fatal threshold, the signature rubric, exclusion rules, analysis plan.
- **Third-party control:** the generic-rigor control (G) is authored by codex, not the experimenter,
  and adversarially edited until an independent reader agrees it is the strongest non-methodeutic
  alternative. Run ≥2 generic control variants if feasible — beating one weak control proves nothing.
- **Blind analysis:** arms labeled Prompt A/B/C through the entire statistical and trace-rating
  pipeline; unblinded only after the analysis is frozen.
- **Mechanical parity:** committed checklist — word count ±5%, imperative count ±2, modal-force markers,
  section count/headings identical, equal mentions of testing/verification/scope/context, same
  persistence-to-completion strength, same closeout. Banned-word check: M holds the only mentions of
  rival/competing/discriminate/decisive-between/falsify/disconfirm; G and T contain zero.
- **Steelman the control:** G must carry every strong generic-rigor technique (codex's evidence-based
  inventory); a crippled control invalidates the result.

## 7. Budget

Two new arms (G, T) over the strata sample, same per-instance ceiling and early-return policy as the
feynman run. M is the frozen baseline (no re-run) unless the fresh-M variant is chosen. Subscription
models ($0 marginal); EC2 is the only marginal cost; self-terminating watchdog.

## 8. Runner & enforcement

Reuse the feynman fleet/runner (`ablation_fleet.sh`, hardened `feynman_run.py` with no-verdict→INFRA
retry, `PINST_TIMEOUT`). Each arm is `pro_pilot` with the framing-prose swapped and everything else
frozen; the swap is the *only* diff. Ledgers under distinct names per arm
(`methG_iofN.jsonl`, `methT_iofN.jsonl`) so they merge without colliding with `feynman_*`. Official
grader only; no bespoke scoring.

## 9. What does NOT change

Grader (official, pinned), staging, models, compute budget, tools, perturbation permissions, the
infra-fault guard + post-outage hardening, the frozen `/recon` comparator (M), the pre-treatment strata,
surface = Pro.

## 10. Freeze tag

`prereg-pro-v1-methcontent` (annotated). SHA + the three prompt hashes + the parity checklist result +
the signature rubric + the strata `.tsv` hash recorded in the worklog before the scored run.

## 11. Threats & disclosures

- **The model may do it anyway (internalized).** The typing-null gives a real prior that M ≈ G because
  the model abduces from any rigorous frame. This is why the behavioral signature is co-primary and
  why T is included — to locate the effect even if the win-rate Δ is null. Disclosed as the most
  likely "uncomfortable" outcome, with its clean reading pre-committed (§4).
- **Control fairness.** The whole result hinges on G being a genuine steelman; a weak control
  manufactures a methodeutic effect. Mitigated by third-party authorship, ≥2 variants, and the parity
  checklist — but a reader who finds G weak should discount the result, and we invite that check.
- **CLI drift** (M frozen 2.1.150 vs G/T 2.1.165): disclosed not controlled; the paired Δ and the
  M/G/T ordering are robust to a uniform shift; the fresh-M variant removes it at extra cost.
- **Multiple comparisons / forking paths:** three arms, two strata, two co-primary outcomes — all
  pre-registered with a single committed fatal threshold; no post-hoc estimand swaps (the standing
  rule from the retraction).
- **Scoping:** the claim is about the methodeutic *content of the framing prose at fixed staging*, not
  about all of methodeutics and not about "all code." Structure is held constant, not tested here.

---

**Pre-registered:** TBD (on freeze). **Arms:** M (frozen `/recon`) vs G (steelman generic, codex-authored)
vs T (minimal). **Factor:** framing-prose content only; staging/models/compute held fixed.
**Estimands:** Δ_MG (primary), Δ_GT, Δ_MT, paired per stratum + a blind behavioral signature.
**Fatal threshold:** Δ_MG within ROPE on overall AND UNDER, with no signature difference → methodeutic
content is decoration. **Strata:** pre-treatment UNDER-first. **Tag:** `prereg-pro-v1-methcontent`.
