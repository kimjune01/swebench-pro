# Methodology — how the 95.33% was measured

This is the auditor's-eye summary: what the system is, what one instance goes
through, how a verdict is decided, and how the run was billed. It synthesizes
and points; it does not restate the rules. The authoritative documents are
[`PREREGISTRATION.md`](PREREGISTRATION.md) (the predicate, the failure-mode
state machine, the contamination accounting) and [`PROCEDURE.md`](PROCEDURE.md)
(the exact commands, pinned versions, and reproduction contract). Where this
file and those disagree, those win.

## The system

A multi-model agent pipeline, frozen as `prereg-pro-v1`:

| component | value | knob |
|---|---|---|
| generator | `claude-sonnet-4-5` | `RCA_MODEL` |
| craft challenger | `gpt-5.5` (codex) | `CRAFT_CODEX_MODEL` |
| agent CLI | `@anthropic-ai/claude-code@2.1.150` | pinned dep |
| craft CLI | `@openai/codex@0.134.0` | pinned dep |
| outer loop | `MAX_OUTER=5` | `rung5_driver.py` |
| stage caps (s) | recon 2000 · craft 3600 · audit 1200 | `*_CAP` |

The harness is **model-agnostic by construction** — no code path branches on
model identity (grep-verified), so the frozen-config block, not the code,
records what the headline ran under. The result is a *system* claim: a
contaminated Sonnet-4.5 + GPT-5.5 ensemble in this scaffold. It is **not** a
single-model or capability claim, and the scaffold-vs-model confound is
permanently open because the same-model control isn't budget-viable
([`PREREGISTRATION.md`](PREREGISTRATION.md) §7, §12).

## Per-instance pipeline

Each of the 728 instances runs the same loop, independent of every other
instance (no cross-instance state):

```
recon ──▶ craft ──▶ audit ──▶ source-only capture ──▶ official re-grade
 (read)   (patch)  (verify)    (git diff, blobs and       (fresh container,
          ▲ GPT-5.5 challenger   test files stripped,        gate == grader)
          └─ loops on craft       >256 KB single-file
             until gate green        diffs dropped)
```

- **recon** (read-only) diagnoses the failure and hands a structured hypothesis
  to craft.
- **craft** generates the patch; a GPT-5.5 codex subagent challenges it; the
  gate arbitrates. The gate reads `FAIL_TO_PASS` as the *stopping signal* —
  legal only because public-set tests are visible (on the held-out private set
  this flips to a blind gate, PROCEDURE §0).
- **audit** runs the full suite and classifies regressions against the captured
  baseline.
- **capture** is **source-only**: `git diff` minus test files, build/runtime
  blobs (`node_modules`, redis `appendonly.aof`, build dirs), and any single
  file diff over 256 KB.

## What counts as a verdict

**The agent's internal gate is never the verdict.** The number is the official
SWE-bench Pro grader (`swe_bench_pro_eval.py`, pinned eval-repo commit) run on
the *captured source-only diff* on a fresh container — the same grade a third
party runs in PROCEDURE §3/§6. The gate is only a stopping signal that can
disagree with the grader (it did once, a PATH bug that made it false-negative
on Go while the gold patch graded RESOLVED); because the verdict is always the
official re-grade of the captured diff, a lying gate can only waste budget, not
manufacture a WIN.

Every instance terminates in exactly one state. Full state machine in
[`PREREGISTRATION.md`](PREREGISTRATION.md) §4; the short form:

| state | meaning | counts | rerun? |
|---|---|---|---|
| WIN | official grader RESOLVED | win | no |
| LOSS | loop completed, not resolved — incl. graded-fail, empty capture, any failure endogenous to the method (errored, no patch, looped, hit a stage cap) | loss | no, stands |
| INCOMPLETE | an enumerated platform fault fired *before* a gradeable diff, with matching corroboration | not scored | yes, byte-identical artifact |
| PAUSE | Max quota hit before a gradeable diff | not scored, un-run | resume, no peek |

The single anti-cheat lever that matters: an INCOMPLETE must carry
corroborating fault evidence matched to its class, or it is mechanically
reclassified LOSS and **stands** — committed in advance so it can't be
selectively invoked after seeing which losses we'd want to re-roll. The
`PROVIDER_CRED_REJECT` class used in this run's recoveries
([`RUN_NOTES.md`](RUN_NOTES.md)) has four required invariants for exactly this
reason.

The final tally has **0 INCOMPLETE**: every instance, including all
auth-stalled ones, was re-dispatched to a terminal WIN/LOSS.

## Operating modes — subscription vs API

The harness drives the `claude` and `codex` CLIs, which resolve credentials
from standard env vars, so a reproducer plugs in their own token source with no
code change. Two modes were used in this run:

- **Subscription (`AUTH_MODE` default, ~83% of verdicts):** Max OAuth pushed to
  each box, `CLAUDE_SUBSCRIPTION=1` in the dispatch env so `plan_env()` drops
  any stray `ANTHROPIC_API_KEY` and the run bills **Max/$0**. The guard matters
  because an API key *overrides* the subscription in the credential precedence
  order — a leaked key would silently bill PAYG.
- **API (`AUTH_MODE=api`, final ~17%):** after the third Max-quota stall, Sonnet
  billed via `ANTHROPIC_API_KEY` (paid PAYG), codex stayed on subscription,
  `CLAUDE_SUBSCRIPTION` unset. The switch traded $0-but-flaky for paid-but-
  reliable and ended the stall waves (see [`RUN_NOTES.md`](RUN_NOTES.md)).

The verdict is **dispatch- and billing-independent** — the official grader runs
per-instance with no cross-instance state, so any path that drains the full
eligible set yields the identical 728-verdict set. The operator used a dynamic
`coordinator.py` dispatcher for box utilization; the canonical reproduction path
is the static `pro_run.py --mode run --shard i/N` stripe with zero custom infra
(PROCEDURE "Execution paths").

## Eligible denominator

728 = 731 dataset instances − 3 §6 gold-patch defects (one per language: a
NodeBB JS name-collision, a future-architect Go case, an ansible Python case),
each a gold patch the official grader scored NOT-RESOLVED on a clean base. The
defect list was frozen *before* any scored model run; no defect may be added
after model results are visible
([`PREREGISTRATION.md`](PREREGISTRATION.md) §6).

## Reproducing a verdict

A third party derives the number rather than trusting it: take any committed
`pro_patch_*.diff`, build `pred.json`, run the grader on a clean container
(PROCEDURE §3/§6). The grade is a deterministic function of the diff — no agent
re-run needed. Aggregate reproduction (re-running the agent) reproduces the
resolve-rate within sampling variance over the 728 set, **not** a per-instance
replay; the agent is stochastic, so an individual instance flipping WIN/LOSS
between runs is expected (PROCEDURE "Reproduction contract").
