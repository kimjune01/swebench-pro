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
- **Restarts are unbounded but accountable: the *motivation* for every restart is the opening entry
  of the new tag's worklog (§13 per-tag rotation), written before that tag's run.** This is the guard
  against restart-as-optional-stopping, not a numeric cap. A restart must be motivated by a **failure
  class** (§1.1), and that motivation is written down and timestamped — a reviewer judges integrity by
  reading the trail, not by trusting a self-asserted rule. A restart whose only honest motivation
  would be "the last headline was low" has no failure-class entry to write, so it has nowhere to hide:
  the new worklog either opens with a legitimate reason or exposes its absence. Every tag that
  completed a full-set run keeps its own worklog in history (§10, §13); the sequence is the record of
  *why* each version exists.
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

Every instance **terminates in exactly one terminal state** (WIN / LOSS / INCOMPLETE); `PAUSE`
(`QUOTA_EXHAUSTED`) is the one non-terminal stop — it always resumes to a terminal state, never
scored on its own. **No instance may be reclassified by discretion
after its logs are visible** — the sole reclassification permitted is the *pre-registered, mechanical*
anti-cheat check below (INCOMPLETE→LOSS when no corroborating fault evidence exists), which is
committed in advance and applied uniformly, not chosen after seeing which losses we'd re-roll. The
only legitimate rerun trigger is a logged platform fault, observable **independent of the verdict** —
this is *verdict*-independence (note: token-exhaustion is verdict-independent but **not**
difficulty-independent, hence §3's fixed order).

| state | trigger | counts as | rerun? |
|---|---|---|---|
| **WIN** | loop completed; official grader RESOLVED | win | no |
| **LOSS** | loop completed but not resolved — incl. completed-failed, empty/0-byte capture, **and any failure endogenous to the method** (agent errored, produced no patch, looped, hit a stage wall-clock cap) | loss | **no — stands** |
| **INCOMPLETE**(fault) | a logged platform fault fired before a gradeable diff: `BOX_DEATH` / `AWS_API` / `OOM` / `DISK_FULL` / `SETUP_NETWORK_FAIL` | not scored; instance incomplete | **yes** — same frozen artifact, to completion; fault code logged |
| **PAUSE**(`QUOTA_EXHAUSTED`) | our Max budget hit its ceiling before a gradeable diff — not a fault, the expected end of budget | not scored; instance simply un-run (§5) | **resume** — byte-identical artifact, no peek (not a re-roll; see below) |

- **INCOMPLETE requires an enumerated fault code**, not "the agent didn't finish." Endogenous
  no-patch = LOSS. "Before a gradeable diff" = before the loop produced *any* diff.
- **A fault *after* the diff is captured but before the official grade is NOT INCOMPLETE.** Grading is
  deterministic from the captured source-only diff on a fresh container (Q3b/Q16) and requires no
  agent re-run — so a box death or grader-infra hiccup post-capture is recovered by simply re-grading
  the captured diff (same artifact); the resulting WIN/LOSS stands. The only way this becomes
  INCOMPLETE is if the **captured diff itself is lost or corrupt** (an infra fault on the capture
  step), which routes back through §4a recovery. Capture, not grade, is the INCOMPLETE/terminal
  boundary.
- **Timeout = LOSS** (stage cap is part of the budget). Sole exception: a hang *proven* an emulation
  artifact (repros on Mac, completes on native EC2) is INCOMPLETE → rerun on EC2 — both logs shown,
  never asserted.
- **Token-exhaustion resume** (`QUOTA_EXHAUSTED`): legit pause-resume ONLY if (a) artifact
  byte-identical on resume and (b) **no inspection of partials** to decide anything. Peek-then-tweak
  = optional-stopping leakage ⇒ new version ⇒ whole-set restart (§3). Un-attempted-at-exhaustion =
  un-run ⇒ run is non-headline until completed (§5).
- **Never** move LOSS→INCOMPLETE after logs are visible; **never** exclude an instance because we
  failed it (defects come only from the §6 audit).
- **Corroboration of platform faults (pre-registered anti-cheat).** The exploitable move in this
  state machine is laundering a capability LOSS as an INCOMPLETE to earn a free re-roll (§3 re-runs
  INCOMPLETEs, never LOSSes). To foreclose it we commit *in advance*: every instance records UTC
  `started_at`/`ended_at`, and **every INCOMPLETE must carry corroborating fault evidence matched to
  its fault class**, else it is **reclassified LOSS and stands** (not re-run). The corroboration
  source differs by class — this is the fix for the gap that infra faults don't appear on provider
  statuspages:
  - **Provider-incident-class** (provider API 5xx / `AWS_API` against an Anthropic/OpenAI endpoint,
    i.e. the provider failing *on its side* while we were within budget): cross-checked against the
    **provider incident timelines** (Anthropic + OpenAI Statuspage history, snapshotted during the
    run so a later page edit can't move the goalposts). No overlapping documented incident → no
    external fault to stand on → LOSS.
  - **Infra-class** (`BOX_DEATH`, `DISK_FULL`, `SETUP_NETWORK_FAIL`, `OOM`, watchdog/spot-reclaim):
    corroborated by their **own on-box / AWS logs** (watchdog fire, dmesg OOM, CloudTrail spot
    reclaim, disk/df, network error) — these never surface on a provider statuspage and are *not*
    subject to the incident-overlap test; the on-box log **is** the independent evidence. An
    infra-class INCOMPLETE with no such log → LOSS.
  - **`QUOTA_EXHAUSTED` is neither** — it is the *expected* end of our Max budget, self-evident from
    the agent CLI's own quota-error response in the log. It is **not** incident-overlap-checked (it
    won't appear on a statuspage) and **not** a re-roll lever: it is a legitimate **pause-resume**
    under the byte-identical / no-peek discipline above, never a LOSS-vs-INCOMPLETE judgement call.
    An un-attempted-at-exhaustion instance is simply *un-run* until the run completes (§5).

  This is bidirectional: corroboration establishes the fault's **existence and timing** *and* shows
  we didn't fabricate it. It does **not** by itself prove the fault was exogenous — an infra event
  *induced by the method* (disk filled by our own runaway logging, OOM from our memory blowup) is
  **endogenous → LOSS**, not a platform fault. (Watchdog sizing is **not** in this bucket: it is
  pinned in the frozen config at ≥1.5× expected wall-time, §4a/§13, so a mid-run fire is the
  correctly-sized operational backstop interrupting in-flight work, not an undersizing defect —
  INCOMPLETE/resume, per §4a.) The corroborating
  log must show an external cause (spot reclaim, host failure, network partition, provider 5xx), not
  merely that a resource ran out. Mechanism: `driver/uptime_correlate.py`; report lands in
  `FAILURE_ATTRIBUTION.md`. Committing pre-run is the point — the rule cannot be selectively invoked
  after seeing which losses we'd re-roll.

### 4a. Overnight / unattended runs — interruption & recovery protocol

A 731-set run is multi-hour and runs unattended; **box death is expected, not exceptional.** A
**corroborated** box death (its on-box/AWS log present, per §4's infra-class rule) is a platform fault
(INCOMPLETE, verdict-independent), never a LOSS; an uncorroborated one reclassifies LOSS (§4).
Enumerated modes, all `BOX_DEATH`-class:
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

**"Completed" = durably checkpointed, not merely finished on the box.** An instance whose verdict
reached the off-box ledger is final and never recomputed (§3). An instance that finished locally but
died *before* its verdict was checkpointed has **no durable verdict to stand on** — it is treated as
**aborted → re-run** under the byte-identical artifact, exactly like one that never started. Re-running
it is safe because the pipeline is deterministic up to the captured diff and the official grade is a
pure function of that diff, so a re-run reproduces the same WIN/LOSS. This is the *only* recompute the
protocol permits, and it touches solely uncheckpointed work — never a recorded verdict.

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

> **RESULT (2026-05-26): eligible = 728 / 731.** Audit ran on all 731 gold patches; **3 defects**
> (gold patch graded NOT-RESOLVED by the official grader, deterministic on re-grade), one per
> language: `instance_NodeBB__NodeBB-00c70ce7…` (JS — 4/681 F2P tests absent, name-collision/flaky),
> `instance_future-architect__vuls-bff6b755…` (Go), `instance_ansible__ansible-de5858f4…` (Py).
> Committed: `runs/audit/{eligible.txt,defects.jsonl}` + per-shard ledgers. This list is frozen
> **before** any scored model run; no defect may be added after model results are visible.

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

## 7. Reported metrics — SYSTEM-vs-SYSTEM only (scaffold is permanently confounded, §12)

- **Headline:** resolved / eligible (official), per frozen tag. Stated as a *system* result: "our
  frozen system resolved X / Y." The system is **multi-model and contaminated** (Sonnet 4.5 generates
  + GPT-5.5 craft challenger; both postdate these repos) — never a single-model or capability claim.
  See §12 for why this is the only budget-viable config and what it costs the claim.
- **Differential:** cells where **our system** resolves and **both reference systems** (sonnet-4,
  gpt4o, both in **SWE-Agent** 200-turn) failed — and the reverse (`tasks/strata.json`). This is a
  **system+ensemble** advantage, *not* a clean scaffold result: our system adds GPT-5.5 the baselines
  lacked, and the §12 same-model control that would isolate scaffold **will not be run** (not budget-
  viable) — so scaffold-only attribution is **permanently confounded**, not pending. Permitted
  phrasing: "system advantage (better scaffold + GPT-5.5 craft volley); scaffold-only not isolated."
  The gpt4o half stays cross-family.

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
| 7 | Mill | Controls: gold-patch oracle (positive control the grader works); reference baselines as the differential arm. The §12 same-model arm is the *only* scaffold control and **will not be run** (not budget-viable) — scaffold attribution stays confounded. |
| 8 | Chamberlin | "Resolved" alts: real fix / recall / variance / gate-lying. **Internal gate ≠ official grader** — it's a fast stopping signal that *can* disagree (2026-05-25 PATH bug made it false-NEGATIVE on Go while gold graded RESOLVED). Verdict is *always* the official regrade of the captured diff on a fresh container (Q3b/Q16), never the gate. So gate-lying can only waste budget, not manufacture a WIN. Recall-vs-reason: see Q19. |
| 9 | Peirce | Strata + comparative hypothesis built from **others'** error data, registered before our runs — not retrofit. |
| 10 | Fisher | No assignment confound — full set, not a split. |
| 11 | Popper | Falsifier: F1 (anchors, §P1 smoke alarm). F2 (the §P2 one-sided test) is **retired** — `p_hard≈1.0` made it unconfirmable and the reviving ablation is out of budget (§P2, §12). The inferential claims are now descriptive; the falsifiable surface is F1 + the official headline denominator. |
| 12 | Popper | Official F2P+P2P is a high bar — can't be passed by weakening a test (gold tests restored). |
| 13 | Kuhn | gold patch + F2P *define* "correct"; a better-than-gold fix that changes F2P reads as a loss. Accepted, flagged. |
| 14 | Platt | The §12 same-model control *would* exclude "our edge is just the model" — but it **will not be run**, so the differential excludes nothing about scaffold. We accept this confound (§12, C1); the claim never asserts scaffold-alone. |
| 15 | Meehl | §P2 *was* a one-sided test with a decision rule; demoted to a descriptive contrast (`p_hard≈1.0`, no budget for the reviving ablation). Reported with CIs, not asserted as "we do better." |
| 16 | Feynman | Self-deception routes: capture ≠ what ran (→ always official-regrade the captured diff); contamination read as capability; variance dressed as a wall (→ FAILURE_ATTRIBUTION probes); model strength laundered as scaffold credit (§12). |
| 17 | Pearl | No causal claim beyond "the artifact produces grader-accepted patches." |
| 18 | Ioannidis | N=731 powers the headline; subgroups (31 / 94 / 172) are **low-power** (n=31 → ±~18% CI) — which is why §P2 is reported descriptively (CIs, not a pass/fail) rather than as an underpowered test. |
| 19 | Mayo | **Partial severity.** Symmetric contamination makes recall-only a *far weaker* explanation (the contaminated baseline had comparable exposure and still failed) — severe-ish against recall-only. **Not** severe for scaffold-only: our system adds GPT-5.5, so the differing cause is scaffold + ensemble (§12, C1). No absolute-capability claim. |
| 20 | Gwern | Full trail: per-instance commits, losing runs kept, audit-defects listed, version history in git. |
| 21 | Gwern | Predictions timestamped + specific below. |
| 22 | Ramdas | No optional stopping (§5); fixed order (§3); only early stop is enumerated infra. No peek-and-stop. Restart-via-versioning (the subtle form) is guarded not by a cap but by **logged motivation** — every restart's failure-class rationale is written to `WORKLOG.md` before its run, so a result-motivated restart has no honest entry to write (§3). |

### Registered predictions (2026-05-24, before any scored Pro run)

Scored against the **frozen-artifact full-set run**, not pilots.

- **P1 (smoke alarm — not a clean falsifier):** ≥ 90% of the 94 `easy_anchors` resolve. Below
  that flags a problem — but the diagnosis is open (pipeline bug *or* misclassified strata *or*
  anchors not actually easy for our system); we halt and investigate which, before any claim. P1
  is a gate, not an inferential result.
- **P2 (DESCRIPTIVE — demoted from a hypothesis test, 2026-05-26):** report resolve-rate on
  `edge_both_scaffold` (172) and on `hardest_both_reasoning` (31), each with its CI, and the gap.
  **Originally** a one-sided test (H₀: p_edge ≤ p_hard) for the scaffold-vs-reasoning story, but the
  pre-freeze sweep observed `p_hard ≈ 1.0` (hardest arm fully resolved, see below), which makes
  `p_edge > p_hard` mathematically unreachable — the test could only ever land inconclusive. We
  **will not run the ablation that would revive it** (not budget-viable, same constraint as §12), so
  P2 is reported as a descriptive contrast, not a pass/fail. This is **system-vs-system** (§7, §12).
- **E1 (descriptive estimate — NOT a prediction):** the resolve fraction on `edge_both_scaffold`
  with its CI. Reported, not pass/failed against a guessed bar. (Renamed from "P3" — it was never
  a prediction.)

### Known exploratory exposure before freeze (full disclosure)

Registered 2026-05-24, but by freeze we'd already run instances under the real config — so the
predictions are *confirmatory on the frozen run*, not naive:

- **2026-05-25:** **23 of the 31 `hardest_both_reasoning`** ran end-to-end, **all OFFICIAL RESOLVED**
  (4 light local + 13 heavy EC2 + 6 prior; dev-mode); the other 8 were not run. So P2's `p_hard` arm
  is **not blind** — `p_hard ≈ 1.0` on everything seen. That observed ceiling is what makes
  `p_edge > p_hard` unreachable, hence P2's demotion to descriptive (above) — flagged, not hidden.
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
  — is **not budget-viable** (shifts all load onto Claude). **Decision (committed): we will not run
  it.** Scaffold-only attribution therefore stays **permanently open** — not "pending," not a deferred
  TODO. Honest headline = contaminated multi-model system (§7).
- **What carries the scaffold claim instead: others' published benchmark numbers, not our own
  ablation.** We don't run an in-house same-model arm; the differential is against the *reference
  baselines* (Sonnet 4 + gpt4o in SWE-Agent, 200-turn) on the same instances. Those published numbers
  are the comparison surface — when our system resolves a cell the documented baseline missed, the
  attribution leans on *their* measured ceiling, not on a control we ran. This is weaker than an
  internal ablation (different model versions confound it, C2) but it is the available evidence, and
  it is the standard way scaffold/harness work is attributed on a public leaderboard.
- **Footnote (the one ablation worth naming):** the cleanest thing a same-model control *could* still
  show is not scaffold-vs-model but **complementarity** — that Claude + GPT-5.5 are stronger as a pair
  than either alone, i.e. neither dominates. That's a genuine, narrower question the differential
  doesn't answer. We flag it and leave it unrun; it's a footnote, not a load-bearing gap.

**C2 — symmetric contamination weakens recall, doesn't eliminate it.** Both sides saw these repos and
the baseline *still failed* (SWE-Agent overflowed before applying what it "knew"), so recall-only is a
**much weaker** explanation than against a clean baseline — but **not ruled out** (Sonnet 4/4.5/GPT-5.5
differ in memorization/cutoff/priors). Hence **no absolute-capability claim**; defensible reading =
"better execution under a stronger multi-model system," recall down-weighted, not excluded. The
held-out's different repos test cross-repo generalization, orthogonal to contamination.

## 13. Freeze mechanism

This document is a **living dev doc until we commit to a scored run**. At that point it is frozen:
(1) commit, (2) annotated tag `prereg-pro-vN`, (3) SHA recorded in `WORKLOG.md`, (4) **worklog
rotation** (below). Pre-run amendments are new commits + new tags with timestamped rationale; old
tags never move. Every scored-run artifact cites the tag it ran under (artifacts are committed
*after* the tag and cite the prereg SHA they ran from — the tag is immutable, so per-instance results
necessarily post-date it; that commit ordering is itself the trail, Q20). **FROZEN as
`prereg-pro-v1` (2026-05-26).** The freeze commit's SHA is recorded in the fresh post-freeze
`WORKLOG.md`; this document no longer changes except by the pre-run amendment mechanism above (new
commit + new tag + timestamped rationale, old tags never move).

**Worklog rotation — one fresh worklog per tag.** When the first tag `prereg-pro-v1` is cut, the
development worklog is archived intact to **`WORKLOG_PREFREEZE.md`** (the frozen record of how the
artifact was built). Thereafter **each scored tag gets its own worklog**: the active tag writes to
`WORKLOG.md`, and when the next tag `vN+1` is cut, the outgoing tag's worklog is archived to
**`runs/scored/<tag>/WORKLOG.md`** (committed under that tag's frozen trail, §10) and a fresh
`WORKLOG.md` is opened for the new tag. Each per-tag worklog:
- **opens with the restart motivation** — the failure class (§1.1, §3) that justified abandoning the
  prior tag and changing the artifact. This is the §3 accountability entry: a result-motivated
  restart has no legitimate opening entry to write.
- then carries **only that tag's scored-run trail**: run/resume events, fault classifications, the
  tag's headline.

So the trail is one worklog per version, each self-contained and each opening with *why it exists*;
the sequence `WORKLOG_PREFREEZE.md → runs/scored/v1/WORKLOG.md → runs/scored/v2/WORKLOG.md → …` is the
full honest history of restarts, never comingled across versions (mirrors §10's "versions never
comingle").

**Pre-freeze gate (all must be committed before the `prereg-pro-vN` tag):**
1. **§6 defect list** — ✅ **DONE (2026-05-26).** Full 731 gold-patch audit run (4-box fleet);
   committed: `runs/audit/eligible.txt` (**728**), `runs/audit/defects.jsonl` (**3**), per-shard
   ledgers. **Eligible denominator = 728** (731 − 3 defects); 0.4% defect rate.
2. **Batch/sharding driver** — ✅ **DONE (2026-05-27).** Whole-eligible-set runner `pro_run.py
   --mode run --shard i/N` (resume + deterministic stripe from `tasks/run_order.txt`, §3) plus
   multi-box orchestration (`audit_fleet.sh` static shards; `coordinator.py` operator-path dynamic
   dispatch). Validated on real boxes: provision → auth → bootstrap → agent → official grade →
   ledger, all green; coordinator 2/2 WIN with clean teardown.
3. **Frozen config block** — ✅ **DONE (2026-05-27).** Exact model IDs (Sonnet 4.5 generator +
   GPT-5.5 craft), stage wall-clock caps, retry policy, EC2 instance type + **100 GB EBS**, dataset
   + grader digests (PROCEDURE "Pinned versions" + "Frozen run config"), and the env contract
   (non-login shell / PATH preserved, ledger dir created) — the three 2026-05-25 harness faults
   pinned as **preflight** checks that run **before any instance is attempted** on a box: if a check
   fails, the box does not run instances (it's a `SETUP_*` INCOMPLETE → re-provision), so no instance
   is scored against a broken harness. This scope is the point — a harness fault caught *by preflight,
   before attempts* is platform/INCOMPLETE; the same fault somehow recurring *mid-run despite passing
   preflight* is **endogenous to our frozen harness → LOSS**, not an excuse. Model-agnostic harness
   (no code path branches on model identity, grep-verified).
4. **§13 self-update + worklog rotation** — ✅ **DONE (2026-05-26).** Declared FROZEN as
   `prereg-pro-v1`; `WORKLOG.md` archived → `WORKLOG_PREFREEZE.md`; fresh `WORKLOG.md` opened for the
   scored-run trail with the freeze SHA.

**Not a freeze gate: the §8 self-carved public holdout.** It is a pre-Scale-pitch overfit check, not
a prerequisite for this public scored run — and the run is structurally overfit-proof anyway: we
freeze one instance-blind artifact and run the *whole* eligible set in one pass (§2, §3), with no
held-out signal fed back (§1.2). There is no sample-selection or iteration-on-results lever to
overfit *with*, so a holdout to detect overfit adds nothing here. (The §8 holdout still matters
before pitching Scale's held-out, as a cross-repo generalization rehearsal — but that's downstream of
this run, not a gate on it.)

All four gate items are committed. **The gate is cleared and the artifact is frozen as
`prereg-pro-v1`** — an *executable* preregistration, not a promise. The scored run proceeds under this
tag; results are committed after it, citing the freeze SHA (§13).
