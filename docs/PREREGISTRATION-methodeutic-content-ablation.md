# Pre-registration — SWE-bench Pro, methodeutic-content ablation (`methodeutic` vs `generic-rigor` vs `minimal`)

The three-arm, single-factor ablation that tests whether the **methodeutic content of the framing
prose** is the causal ingredient in the harness's lift, or whether generic good prompting explains it.
Successor to the perturbation ablation (`prereg-pro-v1-feynman`) and the typing null
(`prereg-pro-v1-untyped`). Ships under the shared Zenodo DOI.

**Status: DRAFT, not yet frozen.** Freezes only when (a) the perturbation recovery has landed, (b) the
three prompts are line-matched and committed with hashes, and (c) the behavioral-signature rubric is
written. Nothing below is run before the freeze tag exists.

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

## 1. Import

Inherits every discipline from `PREREGISTRATION.md` at the `prereg-pro-v1` SHA (predicate, two-mode
state machine, eligible denominator 728, provenance, freeze), the **infra-fault guard** and the
**post-outage hardening** from the feynman run (`no verdict (endogenous)` = INFRA → non-terminal retry,
verdict-type not wall-time; see `docs/WORKLOG-untyped.md` 2026-06-05 retraction). Deltas below override
only what is named.

## 2. The three arms — one factor varied (framing-prose content), everything else held fixed

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
