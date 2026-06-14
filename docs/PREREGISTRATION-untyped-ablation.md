# Pre-registration — SWE-bench Pro, typed-mode ablation (`/ask` vs `/recon`)

The clean single-factor ablation under §4.5b of *The Methodeutic Harness on SWE-bench Pro*. Sibling
to the headline `prereg-pro-v1` (Sonnet+codex) and the `prereg-pro-v1-cheap` (open-weight) runs —
**not a restart of either**. All ship under the same Zenodo DOI bundle as independent receipts.

**One arm this run:** the untyped (`/ask`) arm. This pre-registration covers that arm and no other.

## 0. The promise this run pays off

The paper's central claim is **"reasoning can be encoded at the harness layer, and the encoding is
typing"** (Abstract; §grounding). The ~50-point lift over the bare standardized baseline is, by the
paper's own admission, still bundled: §limitations — *"the ~50-point lift over the bare standardized
baseline still bundles structure, generic agent-engineering, and the generator's thinking-on
config"*; §claim — *"We do not attribute the lift to any specific part of the harness."* The paper
names the resolving experiment for itself, twice:

- §limitations: *"separating structure from generic agent-engineering is the per-factor ablation
  (**typed-mode on/off, blind-blind on/off, gate determinism on/off**)."*
- §future-work: *"**Clean-room ablation** … with and without the typed-mode constraint on one
  fixed model and one fixed inner agent (the bare vendor CLI versus that same CLI inside the
  harness)."*

This run is the **typed-mode on/off** row, with **blind-blind ON and gate ON** held fixed. It is
the proof obligation for the promise: if removing only the typing drops the resolve rate, the
typing is what encodes the reasoning. If it does not, the encoding claim fails — honestly.

## 1. Import

Inherits every discipline from `PREREGISTRATION.md` at the `prereg-pro-v1` SHA: predicate (§1),
two modes (§2), restart scope (§3), failure-mode state machine (§4), overnight recovery (§4a),
eligible denominator (§6, **728**), provenance (§10), confound discipline (§12), freeze mechanism
(§13). The deltas below override only what is explicitly named.

## 2. What changes (deltas vs. the headline)

### 2.1 The arm — one skill swapped, nothing else

The arm is the **full headline pipeline** — same Sonnet 4.5 generator, same GPT-5.5 codex
challenger in `implement`, same deterministic gate, same outer loop, same model pair — with **one
factor removed: the methodeutic typing of the `inquire` stage.**

| | Typed headline (`prereg-pro-v1`) | Untyped arm (this run) |
|---|---|---|
| inquiry stage | `/recon` skill — abduction/deduction/induction, typed hypothesis graph, kill predicates, credence-by-mode | **`/ask` skill** — same goal (find the source root cause, hand a fix-plan to `implement`), **no applied epistemology** |
| `implement` (+ codex challenge) | identical | identical |
| `attest`, deterministic gate, outer loop | identical | identical |
| model pair | Sonnet 4.5 + GPT-5.5 | identical |

Implementation: `driver/pro_untyped.py` mirrors `pro_pilot.py`'s loop and imports `craft`, `audit`,
`pro_setup`, `install_gate`, `pro_capture`, `official_grade` **verbatim from the frozen harness**;
its `untyped_recon` is a verbatim copy of `rung5.recon`'s adapter that injects `ASK_SKILL`
(`skills/ask/skill.md`) where `recon` injects `RECON_SKILL` (`skills/recon/skill.md`). **The entire
ablation is one skill file.** The `/ask` skill keeps `/recon`'s goal, environment contract, and
handoff shape (`Failure summary → Suspect set → Root cause → Edit sites`); it removes the Peircean
mode typing, the typed hypothesis graph, the kill-condition predicates, and confidence-by-mode. The
model diagnoses in free-form prose with no prescribed method — the *collapsed-modes* baseline the
paper describes (§application: *"the modes collapsing into one undifferentiated pass"*).

**Harness frozen, runner flexible** (prior-prereg posture): the measurement contract and the typed
skills are byte-identical and untouched (`git status` clean on `pro_pilot.py`, `rung5_driver.py`,
`pro_run.py`, `skills/recon|craft|audit`). The new arm and runner only *call* them.

### 2.2 Sampling — seeded random draw, fair across repos

The headline runs the whole 728 in frozen lexicographic order; this ablation samples **randomly** so
the Bayesian stopping rule (§3) sees a fair cross-section of the 11 repos, not an alphabetic prefix.

- **Frame:** the 728 eligible ids (parent §6 audit, inherited; no re-audit).
- **Draw:** `seed = 20260604`, committed **before any data**. Eligible ids sorted lexicographically,
  then permuted by `random.Random(seed).shuffle`, written to `tasks/ablation_sample.txt`
  (`sha256[:16] = a6e6a099d4660d49`) and committed — fully replayable.
- The posterior is exchangeable in graded outcomes, so a fixed permutation costs nothing in rigor
  and buys full replay.

### 2.3 Compute — identical by construction

The untyped arm is the same pipeline with the same per-stage caps (`RECON_CAP`, `CRAFT_CAP`,
`AUDIT_CAP`, `MAX_OUTER`), so per-instance compute is **identical to the headline by construction**,
not "matched" after the fact. Neither arm is handed more budget; the only thing that differs is what
the inquiry stage is told to do.

## 3. The Bayesian run — estimating `Δ_typing`

### 3.1 The estimand

The estimand is **`Δ_typing` = `p_typed − p_untyped`**, the resolve-rate difference between the
typed headline and the untyped arm **on the same instances**. The typed verdicts are read from the
frozen `prereg-pro-v1` ledger (`runs/scored/run.jsonl`) — never re-run (§5). So the data are
**paired**: each sampled instance has a frozen typed verdict and a fresh untyped verdict.

Model the 2×2 paired table (McNemar cells) under a Dirichlet(1,1,1,1) posterior:

```
  a = both win        b = typed-only win (typing helped)
  c = untyped-only win (typing hurt)      d = both lose
  Δ_typing = π(b) − π(c)   [ = p_typed − p_untyped ]
```

`Δ` is sampled from the Dirichlet posterior (`ablation_bayes.py`, fixed MC seed for a reproducible
interval). `Δ > 0` means the typing earns resolves the untyped control does not.

### 3.2 Stopping rule (evaluated after each completed instance)

Tokens are subscription/$0 — `n` is not budget-bound, and a Bayesian posterior is immune to the
optional-stopping penalty, so we collect until a threshold crosses and stop then.

```
  PROVEN:     P(Δ_typing > 0) ≥ 0.95               (typing carries the lift — the encoding holds)
  NULL:       95% CI of Δ within [−ROPE, +ROPE], ROPE = 0.03   (typing is practically zero)
  CONVERGED:  95% CI width of Δ ≤ W_TARGET = 0.10   (precise estimate of a middling Δ)
  otherwise   CONTINUE → up to the full 728 census
```

**PROVEN** is the payoff to the promise: a sign-decisive positive `Δ` means *the reasoning is
encoded in the typing*, with the magnitude (the CI) reporting how much. **NULL** is the honest
falsification: `/ask` matches `/recon`, so the typing named nothing the model wasn't already doing.
`N_soft = 100` is a review checkpoint, not a cap.

**Full-set backstop.** If `Δ` neither proves nor nulls within the draw, the run continues to all 728;
at the population the paired table is exact and `Δ` is a census, not a sample. `W_TARGET` controls
only how early we may short-circuit; it cannot move the final number.

### 3.3 Pre-data prediction (recorded, not a prior)

Because the untyped arm keeps codex + gate + loop, it should land high (well above a bare run), so
`Δ_typing` is expected to be **small and positive (~2–8 points)** — the typing earns a real but
modest margin over an already-strong scaffold. Prior stays uninformative Dirichlet(1,1,1,1); this is
recorded for calibration. A small-but-sign-decisive `Δ` still proves the encoding; a zero `Δ` falsifies it.

### 3.4 Parallel-overshoot rule

The fleet runs ≤8 boxes, so up to ~8 instances may be in flight when a threshold crosses. All
in-flight instances run to completion, are graded, and counted; the stop is re-confirmed on the
final `n`. Pre-registered so the overshoot cannot read as cherry-picking.

## 4. Runner — ≤8 EC2 boxes (runner flexible, harness frozen)

The untyped arm is the full pipeline, so it needs codex: same fleet as the headline.

- `driver/pro_untyped.py` — the untyped **arm** (imports the frozen harness; the only new logic is
  `untyped_recon`, which swaps the skill).
- `driver/ablation_run.py` — the **runner**: shards `tasks/ablation_sample.txt`, owns the
  ledger / resume / platform-fault state machine (WIN | LOSS | INCOMPLETE exactly as parent §4),
  shells to `pro_untyped.py`, emits `RESULT_JSON`. Ledger: `runs/scored/untyped[_iofN].jsonl`.
- `driver/ablation_bayes.py` — `sample` (seed-permute → `ablation_sample.txt`) + `status`
  (paired `Δ_typing` posterior + PROVEN / NULL / CONVERGED / CONTINUE). Run after each checkpoint
  pull; on a terminal verdict, tear the fleet down.
- Provisioning reuses `provision_box.sh` + the `run_fleet.sh` pattern (EC2 `m7i.xlarge`, us-west-2),
  dispatching `ablation_run.py --shard i/8`. Installs claude **and codex**, pushes Max OAuth +
  codex auth, git-inits the repo root (codex trust) — same as the headline fleet.

Auth: claude via Max OAuth + codex (subscription mode). Token cost Max/$0; only marginal cost is EC2
(~$0.20/box-hr; expected stop well under the census → a few box-hours).

## 5. What does NOT change (explicit)

- **Eligible denominator:** 728 (parent §6; defects inherited, no re-audit).
- **Grader:** official SWE-bench Pro harness; no bespoke graders (parent §1.3).
- **State machine:** WIN / LOSS / INCOMPLETE exactly as parent §4, incl. the FAULT_RE provider-
  incident discipline (INCOMPLETE cross-checked against the Anthropic/OpenAI statuspage; no overlap → re-run, never silently a LOSS).
- **Infra-fault guard on the paired table (verdict-independent, learned from the headline run,
  `WORKLOG.md` 2026-05-27..29).** Auth-token rotation and quota exhaustion make the agent die *empty
  in <400s*, which the verdict parser mis-records as LOSS. Paired against a clean frozen typed WIN, a
  false untyped LOSS becomes a false typed-only-win and inflates `Δ_typing`. Guard: `ablation_bayes.py`
  quarantines any untyped LOSS faster than `MIN_REAL_SECS = 180s` out of the `Δ` table (a genuine loss
  runs the full Sonnet+codex pipeline; headline real losses ran 764–3025s), flags it for `--redo`, and
  never quarantines a WIN (the official grader cannot pass an empty patch). The rule keys on wall-time
  only, never the verdict, so it cannot launder a real loss — a re-run under healthy auth reproduces it.
  Fast-LOSS *clusters* during the run trigger the headline's `PROVIDER_CRED_REJECT` runbook (halt → re-push
  creds from keychain → `--redo` the window).
- **The typed comparator:** typed per-instance verdicts read from the frozen `prereg-pro-v1`
  `run.jsonl` — **never re-run**. This run produces only the untyped ledger.
- **Provenance:** per-instance trajectories, source-only diff, official grader output, agent logs,
  cost ledger — pulled off-box continuously (parent §14).
- **Surface = Pro.** §future-work names SWE-rebench, but the within-model `Δ` cancels recall (parent
  argument: *"the harness-versus-bare lift on a fixed model, where recall is equally available to
  both sides and cancels"*), and Pro lets us reuse the frozen typed comparator. SWE-rebench is left
  as an optional clean-room confirmation, not this run.

## 6. Freeze tag

Frozen as **`prereg-pro-v1-untyped`** (annotated tag). SHA + the `ablation_sample.txt` hash recorded
in this doc's worklog before the scored run begins. Amendments follow parent §13 (new commit + new
tag; old tags never move).

## 7. Operational checklist (pre-run gate)

- [ ] `tasks/ablation_sample.txt` generated from `seed=20260604`, committed (`sha256[:16]=a6e6a099d4660d49`).
- [x] `skills/ask/skill.md` codex-sniffed (GPT-5.5, 2026-06-04) as a fair single-factor control:
      not strawmanned, not secretly re-typed. Confounds it flagged are fixed -- `/ask` now carries
      `/recon`'s `git log` blame step, suspect-set pruning pressure, and imperative phase force, so the
      ONLY remaining difference is the three typing elements (mode labels, confidence-by-mode, typed
      graph nodes). Lives in the repo as a real file (not symlinked), so skeptics get a real copy.
- [ ] `pro_untyped.py --selftest` green on one instance (gate RED-on-base, GREEN-on-gold) — $0.
- [ ] One real untyped instance smoke-run end-to-end (`/ask` → `craft`+codex → gate → official grade) on 1 box.
- [ ] `ablation_bayes.py status` reproduces a hand-checked `Δ_typing` posterior on the smoke ledger.
- [ ] Fleet provisions 8 boxes via `provision_box.sh` (claude + codex); `ablation_run.py --shard i/8` preflight green on each.
- [ ] This doc committed and `prereg-pro-v1-untyped` tag cut; SHA recorded in worklog.

---

**Preregistered:** 2026-06-04. **Run start:** [TBD, post-checklist]. **Seed:** 20260604.
**Arm:** untyped (`/ask`), one arm this run. **Estimand:** `Δ_typing = p_typed − p_untyped` (paired).
**Stop:** PROVEN `P(Δ>0)≥0.95` / NULL (CI ⊂ ±0.03) / CONVERGED (CI width ≤ 0.10) / else 728 census.
**Boxes:** ≤8. **Surface:** Pro. **Tag:** `prereg-pro-v1-untyped`.
