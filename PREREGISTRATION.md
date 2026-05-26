# Pre-registration — SWE-bench Pro

A living development document **until we commit to a scored run**, at which point it is frozen
(§13). Exploratory work on public is not bound by this; a **measurement** (a claimed number) is.
Companion to `PRO_PORT.md` and `FAILURE_ATTRIBUTION.md`.

## 0. Goal & posture (what the public number is *for*)

The public number is an **audition**, not the deliverable. The held-out (12 repos *different* from
the 11 public, Scale-run for overfit detection) is the real exam; goal = earn a held-out run and
**survive it**. Consequences:

- **Overfitting public is self-defeating.** The split permits public iteration (held-out absorbs
  it), but overfitting just earns the held-out run and then *fails it* on different repos — one shot
  spent. So "general / instance-blind" is **our** discipline, enforced for our reasons, not a rule.
- **Can't rehearse the held-out** (one-shot, Scale-run; iterating = leakage). Detect our own
  overfit *before* the audition on a self-carved public holdout (§8) — weaker (same repos) but the
  only generalization signal we control.
- **Deliverable = credible, reproducible, generalization-worthy public result + a methodology
  pitch**, not a maximal %. The pitch's asset: most baseline failures are scaffold-navigation, not
  reasoning (a fact about Scale's baseline an eval lab cares about).

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
- **Run order is pre-registered** so it cannot become a lever — relevant because token-exhaustion is
  special-cased and hard instances may burn more budget. The frozen order is the committed file
  **`tasks/run_order.txt`**: the lexicographic sort of all 731 `instance_id`s, generated from the
  pinned dataset revision (PROCEDURE §3). The eligible run follows that order, **skipping defects in
  place**, so the order is fixed independently of the §6 audit's outcome. Order does not affect a
  *completed* measurement; it is fixed only to remove the degree of freedom from partial runs. Shard
  assignment (when the batch driver lands) must be a deterministic function of this order, committed
  with it.

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

- **INCOMPLETE requires an enumerated fault code**, not "the agent didn't finish." Endogenous
  no-patch = LOSS. "Before a gradeable diff" = before the loop produced *any* diff.
- **Timeout = LOSS** (stage cap is part of the budget). Sole exception: a hang *proven* an emulation
  artifact (repros on Mac, completes on native EC2) is INCOMPLETE → rerun on EC2 — both logs shown,
  never asserted.
- **Token-exhaustion resume** (`QUOTA_EXHAUSTED`): legit pause-resume ONLY if (a) artifact
  byte-identical on resume and (b) **no inspection of partials** to decide anything. Peek-then-tweak
  = optional-stopping leakage ⇒ new version ⇒ whole-set restart (§3). Un-attempted-at-exhaustion =
  un-run ⇒ run is non-headline until completed (§5).
- **Never** move LOSS→INCOMPLETE after logs are visible; **never** exclude an instance because we
  failed it (defects come only from the §6 audit).

### 4a. Overnight / unattended runs — interruption & recovery protocol

A 731-set run is multi-hour and runs unattended; **box death is expected, not exceptional.** It is a
platform fault (INCOMPLETE, verdict-independent), never a LOSS. Enumerated modes, all `BOX_DEATH`-class:
self-termination **watchdog fired** (a +Nmin shutdown backstop — *this killed a 54%-complete audit on
2026-05-26 when the fleet inherited a +180min default shorter than the run*), spot reclaim, host
failure, `DISK_FULL`, `SETUP_NETWORK_FAIL`.

**Recovery = §3 "re-run only the aborted instances under the byte-identical artifact" — made
crash-safe by two mechanisms the driver must provide:**
1. **Checkpoint.** Per-instance verdicts are flushed to a durable store off the box on a bounded
   cadence (the fleet monitor pulls each shard ledger to local every poll). Max loss on a death =
   one checkpoint interval, not the whole run.
2. **Resume-seed.** On relaunch, each box is seeded with its checkpoint ledger; the driver skips any
   instance already recorded (`pro_run` resume) and grades only the remainder. Verdicts never
   recompute; completed ones stand (§3).

**Watchdog sizing:** the shutdown backstop must exceed expected wall-time **with margin** (≥ ~1.5×);
a watchdog firing mid-run is a known INCOMPLETE fault, recovered by resume — it never reclassifies an
instance. A run is a headline number only once the full eligible set is *completed* (§5), across
however many resume cycles that took.

**Leakage guard on resume (ties to Q22).** For the **scored `--mode run`**, resume is legitimate
ONLY under the `QUOTA_EXHAUSTED` discipline above: artifact **byte-identical**, and **no inspection
of partial verdicts** to decide anything (continue / order / artifact). A box dying is verdict-
independent, so resuming after it is not optional-stopping — but peeking at partials and then tweaking
is, and converts a clean resume into leakage ⇒ new version ⇒ whole-set restart (§3). The **§6 audit
is exempt** from the optional-stopping concern (it grades *gold*, not our model — partials carry no
result signal, and eligible/defect classification is mechanical and order-independent), but its
resume must still be byte-identical.

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
>
> **Pinned mechanics (a re-run must match):** dataset revision and eval-repo/grader commit per
> PROCEDURE "Pinned versions"; gold patch = the dataset `patch` field; grader command = the §3
> `swe_bench_pro_eval.py` invocation; one worker; per-instance grade artifact = `eval_results.json`
> + captured grader log. **Audit-time platform faults are not defects:** a gold-patch grade that
> fails with an enumerated §4 fault code (`DISK_FULL`/`AWS_API`/`OOM`/image-pull failure/`BOX_DEATH`)
> is *audit-incomplete* → retried to a verdict, never silently dropped. Only a gold patch that
> *grades not-RESOLVED*, or a genuinely missing/broken image or parser, is a defect.

This closes the post-hoc-exclusion hole (codex): exclusions are decided by gold-patch behavior,
which is independent of our model's results.

## 7. Reported metrics — SYSTEM-vs-SYSTEM only (until the §12 control runs)

- **Headline:** resolved / eligible (official), per frozen tag. Stated as a *system* result: "our
  frozen system resolved X / Y." The system is **multi-model and contaminated** (Sonnet 4.5 generates
  + GPT-5.5 craft challenger; both postdate these repos) — never a single-model or capability claim.
  See §12 for why this is the only budget-viable config and what it costs the claim.
- **Differential:** cells where **our system** resolves and **both reference systems** (sonnet-4,
  gpt4o, both in **SWE-Agent** 200-turn) failed — and the reverse (`tasks/strata.json`). This is a
  **system+ensemble** advantage, *not* a clean scaffold result: our system adds GPT-5.5 the baselines
  lacked, so scaffold-only attribution needs the unrun §12 control. Permitted phrasing: "system
  advantage (better scaffold + GPT-5.5 craft volley), scaffold-only pending control." The gpt4o half
  stays cross-family.

## 8. Curriculum & self-holdout (development only — NOT a measurement strategy)

Hardest-first on public to maximize information per token: the 31 `hardest_both_reasoning` first,
salted with `easy_anchors`; watch the 172 `edge_both_scaffold`. Batch general fixes, then —
before any pitch to Scale — validate the freeze candidate on a **self-carved public holdout**
(public repos held out of development). This is *weaker* than Scale's held-out (it shares repos
with training/dev, so it does not test cross-repo generalization), but it is the only
generalization check we control. Ordering never affects a completed measurement.

## 9. Held-out discipline

Held-out = **Scale-run, 12 different repos, internal overfit detection**, **no external submission
mechanism** (Scale runs the agent). So for us it's **relationship-gated** (a SEAL ask), **not the
load-bearing result** — our defensible claim is the public number + self-built controls (§7/§8/§12);
held-out, if granted, is clean cross-repo *confirmation*. Mechanism: Scale runs our self-contained
EC2 box/driver (data-source-agnostic `task.json`), not us packaging into their harness (PROCEDURE).
Residual: model creds + sandbox-trust on secret data. Discipline holds: held-out verdict is an
oracle never a stopping signal; one pass; the firewall is physical (repos/tests not in hand, §0).

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
| 8 | Chamberlin | "Resolved" alts: real fix / recall / variance / gate-lying. **Internal gate ≠ official grader** — it's a fast stopping signal that *can* disagree (2026-05-25 PATH bug made it false-NEGATIVE on Go while gold graded RESOLVED). Verdict is *always* the official regrade of the captured diff on a fresh container (Q3b/Q16), never the gate. So gate-lying can only waste budget, not manufacture a WIN. Recall-vs-reason: see Q19. |
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
| 19 | Mayo | **Partial severity.** Symmetric contamination makes recall-only a *far weaker* explanation (the contaminated baseline had comparable exposure and still failed) — severe-ish against recall-only. **Not** severe for scaffold-only: our system adds GPT-5.5, so the differing cause is scaffold + ensemble (§12, C1). No absolute-capability claim. |
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

### Known exploratory exposure before freeze (full disclosure)

Registered 2026-05-24, but by freeze we'd already run instances under the real config — so the
predictions are *confirmatory on the frozen run*, not naive:

- **2026-05-25:** all **31 `hardest_both_reasoning`** ran end-to-end, **all OFFICIAL RESOLVED** (4
  light local + 13 heavy EC2 + prior 6; dev-mode). So P2's `p_hard` arm is **not blind** (≈1.0 seen).
  Since p_edge > p_hard is impossible at p_hard=1, P2 can now only land *confirmed* or *inconclusive*
  — flagged, not hidden.
- `edge_both_scaffold` (172) and `easy_anchors` (94) were **not** run — genuinely out-of-sample for
  P1/E1.

## 12. Confounds, controls, contamination (the part most likely to embarrass us)

**C1 — multi-model config; scaffold-vs-model is a *real, unclosed* confound.** Our system = **Sonnet
4.5** generator (`RCA_MODEL=claude-sonnet-4-5`) **+ GPT-5.5 (codex) craft challenger**; baseline =
`claude-sonnet-4` + gpt4o in `SWE-Agent`. On the generator axis that's one version bump (4→4.5), but
our system **adds a second cross-family model the baseline lacked** — so a we-resolve cell is
scaffold **+ ensemble**, not scaffold alone. It's the only budget-viable config (codex offloads the
scarce Claude budget; no clean single-model arm).
- **The control that would isolate scaffold** — Sonnet 4.5 through vanilla `mini-swe-agent`, no codex
  — is **not budget-viable** (shifts all load onto Claude), so it's **unrun** and scaffold-only
  attribution stays **open** (not "pending"). Honest headline = contaminated multi-model system (§7).

**C2 — symmetric contamination weakens recall, doesn't eliminate it.** Both sides saw these repos and
the baseline *still failed* (SWE-Agent overflowed before applying what it "knew"), so recall-only is a
**much weaker** explanation than against a clean baseline — but **not ruled out** (Sonnet 4/4.5/GPT-5.5
differ in memorization/cutoff/priors). Hence **no absolute-capability claim**; defensible reading =
"better execution under a stronger multi-model system," recall down-weighted, not excluded. The
held-out's different repos test cross-repo generalization, orthogonal to contamination.

## 13. Freeze mechanism

This document is a **living dev doc until we commit to a scored run**. At that point it is frozen:
(1) commit, (2) annotated tag `prereg-pro-vN`, (3) SHA recorded in `WORKLOG.md`. Pre-run
amendments are new commits + new tags with timestamped rationale; old tags never move. Every
scored-run artifact cites the tag it ran under (artifacts are committed *after* the tag and cite the
prereg SHA they ran from — the tag is immutable, so per-instance results necessarily post-date it;
that commit ordering is itself the trail, Q20). **No tag is cut now** — we are still in development.

**Pre-freeze gate (all must be committed before the `prereg-pro-vN` tag):**
1. **§6 defect list** — the full-731 gold-patch audit run and its frozen exclusion list committed.
   *(Driver built: `pro_run.py --mode audit`, validated + deterministic; the **731-instance run is
   not yet executed** — the load-bearing blocker. First probe instance was a defect, so eligible<731.)*
2. **Batch/sharding driver** — the whole-eligible-set runner (§2, §5) with resume semantics and
   shard map deterministic from `tasks/run_order.txt` (§3). *(Per-shard loop built: `pro_run.py
   --mode run --shard i/N` (resume + deterministic stripe); **multi-box orchestration** — provision
   N boxes, dispatch shards, merge ledgers — still a thin wrapper to write.)*
3. **Frozen config block** — exact model IDs (Sonnet 4.5 generator + GPT-5.5 craft), stage
   wall-clock caps, retry policy, EC2 instance type + **100 GB EBS**, dataset + grader digests
   (PROCEDURE "Pinned versions"), and the env contract (non-login shell / PATH preserved, ledger
   dir created) — the three 2026-05-25 harness faults pinned as preflight/regression checks so a
   recurrence reads as INCOMPLETE, never a method LOSS.
4. **§13 self-update** — flip "No tag is cut now" to the cut tag + SHA when the gate clears.

Until 1–3 exist, freezing would freeze a *promise*, not an executable preregistration.
