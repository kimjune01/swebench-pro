# Pre-registration — SWE-bench Pro, cheap-model ablation

A planned ablation under §4.5a of *The inquiry loop on SWE-bench Pro*. Sibling run to the headline
`prereg-pro-v1` Sonnet+codex artifact, **not a restart of it** — both runs ship under the same Zenodo
DOI bundle, two model-pair receipts.

## 0. Import

This document **inherits every discipline from `PREREGISTRATION.md` at the `prereg-pro-v1` SHA**:
predicate (§1), two modes (§2), restart scope (§3), failure-mode state machine (§4), overnight
recovery (§4a), stopping rule (§5), eligible denominator (§6, **728**), provenance (§10), Q1–Q22
checklist (§11), confound discipline (§12), freeze mechanism (§13). The deltas below override only
what is explicitly named; everything else is in force unchanged.

## 1. What changes (deltas vs. parent)

### 1.1 Model pair — role-specialized, cross-family preserved

Replaces parent §7 / §12 "Sonnet 4.5 generator + GPT-5.5 craft challenger" with:

- **Recon (abduction):** Gemini Flash 3.5 + Cursor Composer 2.5, blind-blind pushout per §3.3 of
  the paper. Cross-family preserved (Google × Cursor).
- **Craft (deduction):** Cursor Composer 2.5 writes the patch (impl strength); Gemini Flash 3.5
  adversarially critiques the diff against the spec.
- **Audit:** deterministic, unchanged.

Stage assignment is **role-specialized** by design: Composer is code-specialized (impl strength
where it pays); Flash is fast and general-purpose (cheap divergent hypothesis brainstorming where
it pays). This is methodologically distinct from the parent's symmetric strong-model pair — if it
holds, the publishable heuristic is *match model to stage, not symmetric pair*.

Auth: Composer via `CURSOR_API_KEY`; Flash via `GEMINI_API_KEY` (env vars in operator shell, not
committed to repo).

### 1.2 Scope — Pro only

Parent ran both Verified (`swebench-verified` companion) and Pro. This ablation runs **Pro only**
(728 eligible). Verified is contaminated for every submitter and ports cleanly under any reasonable
model pair; the contamination-resistant tier is where the cheap-model question is informative. No
Verified rerun.

### 1.3 Parallelism — higher than parent

Per-instance cost projection is **~$0.40 combined** (Composer ~$0.23/problem per SWE-rebench + Flash
near-zero increment), against the parent's ~$2.50/instance Sonnet-API rate. The budget headroom is
the lever: where the parent ran on ~4 boxes serialized by API spend, this run can sustain **up to
32 boxes in parallel** (~8× concurrency), bottleneck-shifted from API cost to box-hours and Cursor /
Google API rate limits.

Concrete: shard the 728 eligible into 32 stripes of ~23 instances each from `tasks/run_order.txt`
(parent §3, frozen order unchanged). Wall-clock target: 728 / 32 ≈ 23 instances/box × ~15 min/instance
(cheap models are faster as well as cheaper) ≈ **~6 hours**, against the parent's multi-day run.

Higher parallelism does **not** alter the measurement contract: the run remains a single scored
artifact under one frozen tag, with the same fault-class state machine (§4), the same checkpoint /
resume mechanism (§4a), and the same one-shot held-out discipline (§9).

### 1.4 Budget cap

**$500 hard cap** (projection ~$290; cap absorbs cost overruns from retries within INCOMPLETE
re-runs per §4 and EC2 spend ~$30-50 per memory). At cap, the run is `PAUSE`(`QUOTA_EXHAUSTED`) per
parent §4; results published per parent §10 as a non-headline partial if completion is impossible.

### 1.5 Freeze tag

This artifact is frozen as **`prereg-pro-v1-cheap`** (annotated tag). SHA recorded in this doc's
worklog before the scored run begins. Subsequent amendments follow parent §13 (new commit + new
tag + timestamped rationale; old tags never move).

## 2. What does NOT change (explicit)

- **Eligible denominator:** 728 (parent §6 audit; no re-audit, defects list inherited).
- **Run order:** `tasks/run_order.txt` from parent (lexicographic, frozen). Shard stripe assignment
  is a deterministic function of this order per parent §3.
- **Grader:** official SWE-bench Pro harness; no bespoke graders (parent §1.3, §4).
- **State machine:** WIN / LOSS / INCOMPLETE / PAUSE exactly as parent §4, including INCOMPLETE
  corroboration discipline. A run-time fault on Cursor or Google APIs is a provider-class incident
  cross-checked against the relevant statuspage (Cursor + Google Cloud); no overlap → LOSS, not
  re-roll.
- **Provenance contract:** per-instance trajectories, captured source-only diff, official grader
  output, agent logs, fault codes, cost ledger — all pulled off-box continuously per parent §14
  amendment.
- **Headline discipline:** a partial run is non-headline (parent §5). The cheap-ablation headline
  is the full-eligible-set resolve rate under this frozen artifact, reported alongside the
  Sonnet+codex headline under the shared Zenodo DOI.

## 3. The §4.5a three-outcome reading (carried over from the paper)

Pre-committed interpretations of the resolve rate, against the Sonnet+codex headline (97.1% / N=278
in-flight at preregistration time):

| Cheap-pair rate | Reading |
|---|---|
| Comparable | Loop is the lever; model selection is not. Strongest possible read. |
| Modestly lower | Loop is necessary but not sufficient; frontier capability matters on hard-tail repos. |
| Collapses | Frontier capability does most of the work; loop helps marginally. |

Whichever outcome lands, **the receipts publish per §10** — the answer is the answer.

## 4. Why this is a sibling run, not a restart

Parent §3 ("Artifact changed → whole-set restart under a new frozen tag") governs restarts within
*one* scientific track — i.e., when a methodological change makes prior verdicts stale and the
prior headline should be retired. This run does **not** retire the Sonnet+codex headline; both
headlines stand, side by side, under the shared Zenodo DOI. The motivation is §4.5a of the paper
(isolate loop contribution from model contribution), not a result-driven restart.

The §3 accountability discipline still binds: this doc's worklog opens with the failure-class
motivation ("model selection is unablated hyperparameter" — see §4.5a of the paper), written before
the scored run begins. Both headlines remain auditable independently.

## 5. Operational checklist (pre-run gate)

- [ ] `CURSOR_API_KEY` and `GEMINI_API_KEY` available in operator shell; tested with a single-instance
      smoke run.
- [ ] Shard plan committed (`tasks/shards-v1-cheap.txt` — 32 stripes of ~23 instances).
- [ ] Fleet provisioning script updated for 32 boxes; preflight checks (parent §13.3) confirmed
      green on each.
- [ ] Watchdog wall-clock cap sized ≥1.5× expected per-instance wall-time at the new model rate
      (parent §4a).
- [ ] This doc committed and `prereg-pro-v1-cheap` tag cut; SHA recorded in worklog.
- [ ] First-day cost ledger smoke-test on a 4-box subset (~92 instances) to verify per-instance
      cost lands near projection before scaling to 32 boxes.

---

**Preregistered:** 2026-05-28. **Run start:** [TBD, post-checklist]. **Expected wall-clock:** ~6h
on 32 boxes. **Budget cap:** $500. **Tag:** `prereg-pro-v1-cheap`.
