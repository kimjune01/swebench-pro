# Fan-out research log: harness-evaluation leaderboard prior art + Pro baselines

Status: 4/4 subagents returned, internally convergent. NOT codex-converged yet.
NOT polished (Composer 2.5 swaperoo run in flight). Working notes.

## Question
(1) What do bare models / minimal harnesses score on SWE-bench Pro? (2) Does a
"harness is the contestant, model controlled, good+cheap+fast" leaderboard exist?

## H1: Pro baselines (verified, source-anchored)
**Verdict:** our 95.3% is ~2× the standardized baseline and ~18pt over the live leader.
- Paper reference harness (SWE-agent, 250-turn), Sept 2025: GPT-5 **23.3%**, Opus 4.1 **23.1%** public; ~15-18% commercial. [arXiv 2509.16941, scale.com/blog/swe-bench-pro]
- SEAL standardized (2026 models): gpt-5.4 **59.1%**, opus-4-5 45.9%, gemini-3.1-pro 46.1%; top "Claude Mythos" ~77.8% (UNVERIFIED). [labs.scale.com/leaderboard/swe_bench_pro_public]
- Custom scaffolds buy **+5 to +15pt** over standardized (morphllm). That's the documented "harness contribution" ceiling, far below our +36pt over the 59% leader.
- mini-swe-agent: ~65-74% on Verified (NOT Pro); no Pro number exists.
- No bare/no-agent Pro number exists.

**CORRECTION (operator, 2x):** (1) Pro public gives no prose problem statement; ALL
entries work from the tests; test-visibility is not our differential. (2) Iterating
to green against the tests is the LEGITIMATE task, not a permissive regime; a human
vibe coder does exactly this (read failing test → write code → iterate to green). So
"iterate-to-green inflates it" is RETRACTED; solving the real task well is a real
result. The gap over the standardized harness (95 vs 59) is a legitimate harness-
contribution claim. Genuine remaining open questions (NOT "we saw the tests"):
  - **same-model harness-vs-harness control:** the 59% leader is gpt-5.4; ours is
    Sonnet4.5+GPT5.5 ensemble. Clean harness-delta needs our harness vs the standardized
    harness on the SAME model. (For a fixed model, contamination is shared → cancels in
    the delta. The Composer 2.5 swaperoo is the cross-model transfer evidence.)
  - **+36pt exceeds the +5-15pt custom-scaffold ceiling** → either genuinely-better
    harness OR ensemble-vs-single-model; attribution needs the control above.
  - **held-out split** (different repos, possibly blind gate) is the untested generalization.
  - **contamination** qualifies absolute CAPABILITY, not the harness delta.

## H2: academic scaffold-as-unit prior art (verified)
**Verdict:** the bullseye exists but stops short of "harness alone is the unit."
- **SWE-Effi** (arXiv 2509.09853, Sep 2025): CLOSEST. 5 scaffolds × 3 fixed models,
  proposes a public leaderboard, holistic metrics (Effectiveness-under-Token-Budget/
  -Cost/-CPU-Time/-Inference-Time = AUC of resolve-vs-resource). KEY FINDING that cuts
  at our thesis: *"effectiveness is not an inherent property of the scaffold but emerges
  from synergy with the base LLM."* Unit = scaffold×model pair, not scaffold alone.
- SWE-agent ACI ablation (arXiv 2405.15793): cleanest single-scaffold model-fixed
  ablation (+10.7pp from ACI). Not cross-scaffold.
- Agentless (2407.01489), AutoCodeRover (2404.05427): scaffold-vs-scaffold arguments,
  but as leaderboard entries, model not controlled.
- "Agent Harness Survey" (preprints.org 2026, NOT peer-reviewed): explicit "harness is
  the primary determinant" thesis; no leaderboard.

## H3: industry harness leaderboards (verified)
**Verdict:** harness-as-contestant leaderboards already exist; cost rarely reported.
- **HAL** (Princeton, arXiv 2510.11977, ICLR 2026): STRONGEST infra. Models×scaffolds×
  benchmarks 3D, 21,730 rollouts, cost-aware (token + $). Scaffold is first-class axis
  but model stays the headline unit. [hal.cs.princeton.edu]
- Official SWE-bench: (system, model) pairs; scaffold NAMED + filterable; no cost.
- Terminal-Bench 2.0: [agent]/[model] pairs, same model under many agents → scaffold is
  differentiator; no cost/speed columns.
- OpenHands Index + SWE-bench Bash-Only: the INVERSE (harness fixed, model varies).

## H4: cost-aware / 3-axis prior art (verified)
**Verdict:** cost-vs-accuracy Pareto is established; unified 3-axis good+cheap+fast is open.
- "AI Agents That Matter" (Kapoor 2024, arXiv 2407.01502): originating thesis: evals must
  control for cost; accuracy-vs-$ Pareto. Two-axis (no speed).
- HAL: token + $ cost, Pareto frontiers. No speed axis.
- Artificial Analysis Coding Agent Index: ONLY one tracking all 3 (score, $/task, wall-time/
  task), but as 3 separate 2-axis scatters, varying model not harness.
- "$/successful-fix" surfaced (TokenMix) but UNVERIFIED as an established metric.

## Convergence (across subagents)
- **HAL** independently surfaced in H2, H3, H4 → strongest/most-cited anchor. Convergent.
- **SWE-Effi** = the academic bullseye (H2), corroborated as the fixed-model×scaffold design.
- No contradiction across agents.

## White space (the gap this work could occupy)
A standing leaderboard where: **the harness is the sole scored unit**, the **model is
controlled** (proven by cross-model transfer, the Composer 2.5 swaperoo), measured on a
**unified good+cheap+fast** frontier (speed is the consistently-dropped 3rd axis), **open
to outside submissions**, with reproducible per-instance receipts. SWE-Effi + HAL own the
nearest ground; none combines all four + an open invitation.

## SWE-Effi limit → load-bearing for our framing
SWE-Effi's "effectiveness emerges from scaffold×model synergy" IS our C1 confound. A
credible harness leaderboard must control for model. The Composer 2.5 swaperoo run is
exactly that control (same harness, different model) and is the evidence that answers it.

## Submission-hostility inference (operator, load-bearing)
Prominent boards (Scale held-out = relationship-gated, not self-serve) are submission-
HOSTILE. Therefore the public leaderboard UNDER-samples the frontier: strong harnesses
may exist that never published / got gated / didn't bother. Consequences:
- "No published competitor near us" is WEAK evidence we're the best: sparse top =
  partly submission friction, not absence of rivals. Calibration guard: do NOT claim
  frontier/best.
- This is the strongest argument FOR the open invitation: a low-friction self-serve
  harness board (bring scaffold → run frozen set → submit receipts) is the *remedy*
  that surfaces hidden players and tells us where we actually stand.
- So the honest-challenge search (contamination-resistant + cost-controlled venues)
  AND the open-invitation board are the same move: find where we're genuinely contested.

## Agreed standing-claim framing (operator)
Headline: **"we haven't found a higher score in the universe yet."** States an
OBSERVATION (search came up empty), not a superiority claim; "yet" + "found" carry
the humility the submission-hostility point requires. Backing receipt under it:
"Across every public SWE-bench Pro leaderboard + paper surveyed as of 2026-05-30, no
higher score found; boards are submission-hostile so a stronger unpublished harness
may exist; if you have one, the invitation stands." Confident about observation,
honest that observation ≠ frontier. Refutable by one counterexample = the invitation.

## EXTEND cycle: where we're genuinely contested (the honest-challenge venues)

### Correctness challenge (contamination-free): SWE-rebench = the pick
- **SWE-rebench** [swe-rebench.com], LIVE/auto-refreshing post-cutoff, fixed ReAct scaffold,
  pass@1. Frontier ~**65%** (Opus 4.6 65.3%, GLM-5 62.8%, Sonnet 4.6 60.7%, as of 2026-05-28).
  NOT saturated at 95%; contamination gone → our 95% would NOT carry; we'd land contested.
  Legible, credible, self-measurable. **This is the honest live correctness board.**
- K-Prize 7.5% top (harshest contamination ceiling), but gated/intermittent, can't freely
  submit. Cite as the contamination ceiling, not a venue.
- Pro commercial <20% (right low numbers, right reason), but never published, can't enter.
- Terminal-Bench 2.0 top now 90%+ (vix/Opus4.7 90.2%), saturating + different domain (terminal).

### Cost challenge (Pareto): HAL + Artificial Analysis = where we get DOMINATED
- **HAL SWE-bench Verified Mini** [hal.cs.princeton.edu]: explicit $/task vs resolve Pareto.
  Frontier = LEAN single-model scaffolds (SWE-agent+Sonnet4.5-High 72% @ $464; Gemini-2.0-Flash
  24% @ $4.72). Expensive multi-model DOMINATED (Opus4.1-High 54% @ $1,600 < o4-mini @ $259).
  HAL thesis: "costliest rarely on frontier; simple scaffolds dominate complex." Aimed straight
  at a 2-model/5-loop ensemble.
- **Artificial Analysis Coding Agent Index**: real $/task. Composer 2.5 Standard ≈ **$0.07/task**.
  ⚠️ **CONFLATION GUARD (caught 2026-05-30):** AA's "62" is a NORMALIZED 0-100 COMPOSITE
  (Pro-Hard-AA + Terminal-Bench + QnA), **NOT a SWE-bench Pro resolve rate.** Do NOT say
  "Composer gets 62 on Pro"; Composer's raw Pro resolve rate is UNVERIFIED. DeepSWE (Datacurve)
  is yet a THIRD board (cost-vs-DeepSWE-score, top ~70% gpt-5.4 @ ~$7; Composer not listed).
- **FRAME = frontier, not head-to-head.** These are not directly comparable (different boards,
  normalizations, contamination). The honest model is a **cost-vs-correctness Pareto frontier**:
  every agent/model is a point; the question is *where our point sits*, not "we beat Composer."
  This is exactly how DeepSWE/HAL/AA present ("most efficient ↗"). Our concern stands: a
  $2.60 / 2-model / 5-loop point is unlikely to be on the cost-efficient part of the frontier
  unless its resolve rate is strictly higher. correctness>cost>speed is our lexicographic defense.

### MAJOR honesty implication for the scoreboard "cheap" claim
$2.60/task is cheap vs naive-API-everything, NOT vs the cheap end of the frontier (lean agents at
single-digit cents). "Cheap" got DROPPED → axis renamed **RESULT | COST | SPEED** (2026-05-30, per
codex + operator); cost is a neutral metric, no adjective. The Composer 2.5 swaperoo is the
load-bearing test: swapping Composer into our harness measures whether the scaffold's correctness
lift justifies its added cost, i.e., where the *harness-wrapped* point lands on the frontier vs
Composer-standalone.

## Known related benchmarks (acknowledge, don't conflate)
- **DeepSWE** (Datacurve, https://deepswe.datacurve.ai/): separate SWE benchmark; we're
  aware of it (see project_deepswe_submission). Related-work mention, not our target here.

## Flags (unverified)
- "Claude Mythos" 77.8% Pro top; 2026 blog figures (Opus 4.8 88.6% etc.), aggregators, not primary.
- SWE-Effi per-cell resolve rates; harness-bench WIP (neuralnoise, TLS fail).
- Agent Harness Survey not peer-reviewed.
