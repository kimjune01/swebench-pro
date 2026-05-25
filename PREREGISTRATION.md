# Pre-registration — SWE-bench Pro

A living development document **until we commit to a scored run**, at which point it is frozen
(§13). Exploratory work on public is not bound by this; a **measurement** (a claimed number) is.
Companion to `PRO_PORT.md` and `FAILURE_ATTRIBUTION.md`.

## 0. Goal & posture (what the public number is *for*)

The public number is **not the deliverable** — it is an **audition**. The held-out set (12
repositories *different* from the 11 public ones, run by Scale for overfitting detection) is the
real exam. The goal is to earn a held-out run and **survive it**, then make an honest claim.

Consequences that govern everything below:

- **Overfitting public is admissible to the benchmark, inadmissible to our claim, and fatal to
  our goal.** The split *permits* public iteration (no rule against it; the held-out exists to
  absorb it). But the public number is permitted *because it isn't believed* — admissibility and
  worthlessness are the same coin. For us, overfitting is self-defeating: it earns the held-out
  run and then *fails it* on different repos, after we've spent credibility and likely our one
  shot.
- **We cannot rehearse on the held-out.** It is one-shot and Scale-run; iterating against it is
  leakage. So we must detect our own overfitting *before* the audition, on a self-carved public
  holdout (§8) — weaker than Scale's cross-repo holdout (same repos), but the only generalization
  signal we control. The "general / instance-blind" discipline is therefore **ours, enforced for
  our reasons** (a one-shot exam we can't retake), not a benchmark rule.
- **The deliverable is a credible, reproducible, generalization-worthy public result + a
  methodology pitch that earns a held-out verification** — not a maximal percentage. A gamed high
  number is counterproductive. The pitch's strongest asset is the finding that most baseline
  failures are scaffold-navigation, not reasoning (a fact about Scale's own baseline, which an
  evaluation lab cares about). Rigor here is a sales asset, not paperwork.

## 1. Predicate (a result is admissible iff all hold)

1. **General** — every artifact change is instance-blind, motivated by a failure *class*.
2. **No leakage** — held-out grades are never a stopping signal or iteration input; one frozen
   version, one held-out submission.
3. **Official-attested** — a win is the official Pro grader's verdict on the captured source-only
   diff, nothing else.
4. **Honest denominator** — exclusions are documented defects only, from the §6 pre-run audit.
5. **Reproducible** — frozen tag, re-derivable from committed per-instance artifacts, and
   **runnable by a third party** (Scale must be able to execute the pipeline on unseen instances).

## 2. Two modes

- **Exploratory (development):** run any subset (hardest-first curriculum, anchors, differential
  probes). No scoreboard. Partial is fine. Not bound by §3.
- **Measurement (a "run"):** freeze the artifact → run the **whole eligible set** → that is the
  number. A measurement that does not complete the full eligible set under one frozen artifact is
  an **aborted run, not a headline run** (§5).

## 3. Restart scope & run order

- **Artifact changed** → whole-set restart under a new frozen tag. Prior verdicts are stale, never
  merged across versions. Same eligible denominator each run.
- **Artifact unchanged, infra aborted some instances** → re-run *only the aborted instances* (§4);
  completed verdicts stand.
- **Run order is pre-registered** (fixed instance order, committed before the run) so it cannot
  become a lever — relevant because token-exhaustion is special-cased and hard instances may burn
  more budget. Order does not affect a *completed* measurement; it is fixed only to remove the
  degree of freedom from partial runs.

## 4. Failure-mode catalog — a fixed state machine (DECIDED IN ADVANCE)

Every instance terminates in **exactly one** state. **No instance may be reclassified after its
logs are visible.** The only legitimate rerun trigger is a logged platform fault, observable
**independent of the verdict** — this is *verdict*-independence (note: token-exhaustion is
verdict-independent but **not** difficulty-independent, hence §3's fixed order).

| state | trigger | counts as | rerun? |
|---|---|---|---|
| **WIN** | loop completed; official grader RESOLVED | win | no |
| **LOSS** | loop completed but not resolved — incl. completed-failed, empty/0-byte capture, **and any failure endogenous to the method** (agent errored, produced no patch, looped, hit a stage wall-clock cap) | loss | **no — stands** |
| **INCOMPLETE**(fault) | a logged platform fault fired before a gradeable diff: `BOX_DEATH` / `AWS_API` / `OOM` / `DISK_FULL` / `SETUP_NETWORK_FAIL` / `QUOTA_EXHAUSTED` | not scored; instance incomplete | **yes** — same frozen artifact, to completion; fault code logged |

**Tightening the infra hole (codex):** INCOMPLETE requires an **enumerated platform fault code**,
not "the agent didn't finish." A method that fails to emit a patch for endogenous reasons is a
**LOSS**. "Before a gradeable attempt" means before the loop produced *any* diff — not "before we
liked the diff."

**Timeout = LOSS, not infra.** A stage wall-clock cap is part of the artifact's budget. The sole
exception: a hang **proven** to be an emulation artifact (reproduces on Mac emulation, completes
on native amd64 EC2) is `INCOMPLETE` and reruns on EC2 — demonstrated with both logs, never
asserted. Default = LOSS.

**Token-exhaustion / resume (Ramdas, Q22 — the dangerous part).** `QUOTA_EXHAUSTED` mid-run is a
legitimate *pause-and-resume* ONLY if (a) the artifact is byte-identical on resume, and (b) **you
do not inspect partial results to decide anything** — not whether to continue, not the artifact,
not order. Peeking then tweaking converts a clean resume into optional-stopping leakage; any
change ⇒ new version ⇒ whole-set restart (§3). Un-attempted instances at exhaustion are **un-run**
and (per §5) the run is then **non-headline** until completed.

**Never** move a LOSS to INCOMPLETE after logs are visible. **Never** exclude an instance as a
defect because we failed it — defects come only from the §6 pre-run audit.

## 5. Stopping rule

- **Exploratory:** stop a thread when it stops being informative.
- **Measurement:** **no early stop.** A run is a headline number **only if the full eligible set
  completes** under one frozen artifact. A budget-capped or quota-stopped partial run is
  **explicitly invalid for headline claims** and non-comparable to a completed run — its partial
  numerator may not be floated as a result. Un-run instances are disclosed; the denominator is
  always the full eligible set.

## 6. Eligible denominator & pre-run defect audit

Public eligible = the 731 `ScaleAI/SWE-bench_Pro` test instances **minus defects found by a
pre-run audit, frozen before any scored model run**:

> **Defect audit:** grade every instance's **gold patch** through the official grader on a clean
> base (the validated `$0` path). Any instance whose *gold* patch does not grade RESOLVED, or
> whose image/parser is missing/broken, is a documented defect — excluded, listed with its grader
> output. This list is committed *before* the model run. **No defect may be added after model
> results are visible.**

This closes the post-hoc-exclusion hole (codex): exclusions are decided by gold-patch behavior,
which is independent of our model's results.

## 7. Reported metrics — SYSTEM-vs-SYSTEM only (until the §12 control runs)

- **Headline:** resolved / eligible (official), per frozen tag. Stated as a *system* result:
  "our frozen system resolved X / Y public Pro instances."
- **Differential:** report cells where **our system** resolves and **both reference *systems***
  (sonnet-4, gpt4o — both run in the **SWE-Agent** scaffold, 200-turn) failed, and cells where we
  fail and both passed (`tasks/pro/strata.json`). The baselines' scaffold is specifically
  SWE-Agent; the differential is against *that*, not a generic agent.
  Against the **sonnet-4** baseline the model axis is *mostly controlled* — we run **Sonnet 4.5**,
  same family, one version bump (§12, C1) — so the differential is **largely scaffold**, the 4→4.5
  bump the only residual (closed by the same-model control). Writeups may say "largely scaffold,
  residual = one minor model version, control pending"; they may **not** claim a *clean* scaffold
  advantage until that control runs, and the gpt4o half stays cross-family (system-vs-system).

## 8. Curriculum & self-holdout (development only — NOT a measurement strategy)

Hardest-first on public to maximize information per token: the 31 `hardest_both_reasoning` first,
salted with `easy_anchors`; watch the 172 `edge_both_scaffold`. Batch general fixes, then —
before any pitch to Scale — validate the freeze candidate on a **self-carved public holdout**
(public repos held out of development). This is *weaker* than Scale's held-out (it shares repos
with training/dev, so it does not test cross-repo generalization), but it is the only
generalization check we control. Ordering never affects a completed measurement.

## 9. Held-out discipline

The held-out is **Scale-run, 12 different repos, reserved for internal overfitting detection** —
there is **no published external submission mechanism** (Scale *runs the agent*, it does not accept
held-out predictions; baselines used the **SWE-Agent** scaffold, 200-turn limit). So a held-out run
for us is **relationship-gated** (a SEAL ask), not a self-serve submission, and is **not the
load-bearing result** — our defensible claim is the public number + self-built controls (§7, §8,
§12). The held-out, if granted, is clean cross-repo *confirmation*, not the linchpin.

If granted, the mechanism is **Scale runs our self-contained EC2 box/driver on their instances**
(our driver takes a `task.json`, data-source-agnostic), *not* us packaging into their harness —
see `PROCEDURE.md`. Residual: model credentials + sandbox-trust on secret data. Discipline holds
regardless: the held-out F2P verdict is an oracle, never a stopping signal; one pass, no iterating
against it; the firewall is physical (held-out repos/tests are not in hand, and cannot be rehearsed
on — §0).

## 10. Provenance

Every instance (WIN, LOSS, INCOMPLETE) is committed as its own artifact under the run's frozen
tag — ledger, captured diff, official report, agent logs, fault codes. Losing runs stay in
history. Versions never comingle. The number is re-derivable from the commits, not asserted.

## 11. The 22-question checklist ([the-prereg-checklist](https://june.kim/the-prereg-checklist))

| # | Source | Answer for this run |
|---|---|---|
| 1 | Bacon | Whole eligible set; curriculum ordering is **dev-only** (§8) and never selects the measured sample. |
| 2 | Bacon | This document, frozen at run-commit (§13). Amendments only pre-run, timestamped. |
| 3 | Descartes | Invalidating-if-false: (a) the official grader is correct; (b) source-only capture faithfully reproduces what the agent ran (bit us once — the repo-field bug; guarded by always re-grading the captured diff on a fresh container); (c) the self-holdout predicts held-out (weak — different repos). |
| 4 | Hume | Mechanism: the loop emits patches the official grader accepts. Claim = **capability of the loop to emit a passing fix**, not "the model reasoned it" (§ contamination). |
| 5 | Hume | Generalization is the design: public (11 repos) → held-out (12 *different* repos). Our self-holdout shares repos, so it under-tests this — disclosed. |
| 6 | Mill | **Honest limit:** we batch general fixes per version, so we cannot causally attribute the number to a single change. We measure the artifact holistically, version-vs-version. |
| 7 | Mill | Controls: gold-patch oracle (positive control the grader works); reference baselines as the differential arm; §12 same-model arm is the *only* scaffold control. |
| 8 | Chamberlin | "Resolved" alternatives: real fix / recall / variance / gate-lying. Gate-lying excluded by construction (gate == official grader). Recall-vs-reason not separable (Q19). |
| 9 | Peirce | Strata + comparative hypothesis built from **others'** error data, registered before our runs — not retrofit. |
| 10 | Fisher | No assignment confound — full set, not a split. |
| 11 | Popper | Falsifiers: F1 (anchors, §P1) and F2 (§P2 one-sided test). |
| 12 | Popper | Official F2P+P2P is a high bar — can't be passed by weakening a test (gold tests restored). |
| 13 | Kuhn | gold patch + F2P *define* "correct"; a better-than-gold fix that changes F2P reads as a loss. Accepted, flagged. |
| 14 | Platt | The §12 same-model control excludes "our edge is just the model." Without it, the differential excludes nothing about scaffold. |
| 15 | Meehl | §P2 is a one-sided test with a decision rule, not "we do better." |
| 16 | Feynman | Self-deception routes: capture ≠ what ran (→ always official-regrade the captured diff); contamination read as capability; variance dressed as a wall (→ FAILURE_ATTRIBUTION probes); model strength laundered as scaffold credit (§12). |
| 17 | Pearl | No causal claim beyond "the artifact produces grader-accepted patches." |
| 18 | Ioannidis | N=731 powers the headline; subgroups (31 / 94 / 172) are **low-power** (n=31 → ±~18% CI) — §P2 carries a three-way verdict (confirm/refute/**inconclusive**) for exactly this. |
| 19 | Mayo | For our actual claim (the **scaffold differential**) the test **is severe**: contamination is symmetric across arms, so "recall not reasoning" can't explain why we resolve a cell the *same-family* baseline failed — both recall equally; scaffold is the only differing cause. "Not severe against recall" applies only to an **absolute model-capability** reading, which we don't make (§12, C2). |
| 20 | Gwern | Full trail: per-instance commits, losing runs kept, audit-defects listed, version history in git. |
| 21 | Gwern | Predictions timestamped + specific below. |
| 22 | Ramdas | No optional stopping (§5); fixed order (§3); only early stop is enumerated infra. No peek-and-stop. |

### Registered predictions (2026-05-24, before any scored Pro run)

Scored against the **frozen-artifact full-set run**, not pilots.

- **P1 (smoke alarm — not a clean falsifier):** ≥ 90% of the 94 `easy_anchors` resolve. Below
  that flags a problem — but the diagnosis is open (pipeline bug *or* misclassified strata *or*
  anchors not actually easy for our system); we halt and investigate which, before any claim. P1
  is a gate, not an inferential result.
- **P2 (PRIMARY — pre-registered hypothesis test):** resolve-rate on `edge_both_scaffold` (172) >
  resolve-rate on `hardest_both_reasoning` (31). **Test:** one-sided two-proportion test (Fisher's
  exact, small-n), α = 0.05, H₀: p_edge ≤ p_hard. **Three-way verdict:** *confirmed* if H₀
  rejected; *refuted* if p_edge < p_hard with the one-sided test rejecting the reverse; otherwise
  **inconclusive** (low power at n=31 — an honest non-result, not a pass). Effect size + CI
  reported regardless. This claim is **system-vs-system** (§7, §12).
- **E1 (descriptive estimate — NOT a prediction):** the resolve fraction on `edge_both_scaffold`
  with its CI. Reported, not pass/failed against a guessed bar. (Renamed from "P3" — it was never
  a prediction.)

## 12. Confounds, controls, contamination (the part most likely to embarrass us)

**C1 — scaffold vs model (a *small* confound, not a chasm).** We run **Sonnet 4.5**
(`RCA_MODEL=claude-sonnet-4-5`, verified in the live process); the baseline ran **`claude-sonnet-4`**
+ gpt4o in `SWE-Agent`. So against the sonnet-4 baseline this is **same model family, a single
version bump (4 → 4.5)** — *not* a different/larger model. A we-resolve/sonnet-4-fails cell is
therefore **largely a scaffold result**, especially given most baseline failures are navigation/
context-overflow (a scaffold property). The model axis is **mostly controlled by construction**;
the **only residual** is the 4→4.5 improvement.
- **(closes the residual) same-model control arm:** run **Sonnet 4.5** through vanilla
  `mini-swe-agent` on the same instances. our-scaffold ≫ vanilla-scaffold *at fixed Sonnet 4.5*
  removes the 4→4.5 gap entirely and licenses a clean scaffold claim. Budget-gated — but the
  headline is no longer *locked* to system-vs-system: it is "largely scaffold (same family),
  residual = one minor version, control pending." (The gpt4o comparison remains cross-family.)

**C2 — contamination is not a confound for the scaffold claim; it *isolates* it.** Both arms are
contaminated (Sonnet 4.5 and the sonnet-4 baseline have both seen these repos), so recall **cannot**
explain a we-resolve / sonnet-4-fails cell — the contaminated baseline had the same recall and
*still failed* (SWE-Agent overflowed before applying what it "knew"). Symmetric contamination
removes model-knowledge as the variable, leaving **scaffold** as the differing cause. Our claim is
scaffold navigation/execution, not model capability; contamination bears **only** on reading the
*absolute* number as "the model reasons," which we don't claim. (We *may* report the clean-cutoff
subset for the absolute number — not load-bearing.) The held-out's different repos test cross-repo
generalization, orthogonal to contamination.

## 13. Freeze mechanism

This document is a **living dev doc until we commit to a scored run**. At that point it is frozen:
(1) commit, (2) annotated tag `prereg-pro-vN`, (3) SHA recorded in `WORKLOG.md`. Pre-run
amendments are new commits + new tags with timestamped rationale; old tags never move. Every
scored-run artifact cites the tag it ran under. Post-hoc edits are detectable as commits *after*
the run's first result commit — that ordering is part of the trail (Q20). **No tag is cut now** —
we are still in development.
