# Objections: reading the 95.3% honestly

95.3% on SWE-bench Pro-public is a striking number, and a striking number on a
contaminated public split should be assumed overfit until it survives the obvious
attacks. This document states the attacks plainly and bounds each one against the
evidence in this repo. Where an objection lands, it is conceded.

The stance up front: this is a **system result on a public, contamination-prone
split**: an audition, not a capability claim. We don't ask you to trust it; we
hand you the means to check it. Every row below is a *handle* (something to verify
or a stated limit), never an argument.

## The short version

| The reaction | How it's handled: what *you* can check |
|---|---|
| "95% is 2× the leaderboard, theater" | An **audition** number on the public split. The test that would validate it (the private held-out) is Scale-run and **inaccessible to us**, so it's provisional by construction, not a 2× claim (#2, #9). |
| "The harness is overfit to the test" | **Read the skills** (`skills/{recon,craft,audit}`): legible, general, **zero per-instance priors**, carried over from Verified. Overfit is falsifiable by inspection (#3). |
| "It just memorized the repos" | Conceded: the **models** pretrained on these repos (model-side, **universal** across every leaderboard entry), not a harness property (#1). |
| "It gamed the grader" | **Unmodified official grader**, pinned commit; re-grade any verdict yourself (#5, #6). |
| "Cherry-picked instances" | Whole eligible set (728), **0 INCOMPLETE**, 3 gold-patch defects named; reproduce on a **random** sample (#7). |
| "Expensive brute force, not reasoning" | ~$5.14 / ~12.8 min each at API rates — and the **open-weight-generator pair does it for ~$0.41** — **plus** a hypothesis-graph reasoning trace per instance (hundreds of worked examples on real OSS in [`kimjune01/sweep`](https://github.com/kimjune01/sweep)) (#12). |
| "Why should I trust you?" | You don't: **one prompt** reproduces a random sample on your machine ([README](../README.md)). Trust is the one axis an AI can't win; verification is the answer. |
| "But it's AI" | A **values** call, not an evidence one, not litigated here. The work is real and reasoned; judge it on merit, or decline on principle. Both are fair. |

The sections below are the depth layer; scan the table, dig where you doubt.

## 1. "It's contamination: the models memorized these repos."

Conceded as unexcludable, which is why there is **no capability claim**. Sonnet
4.5 and GPT-5.5 both postdate every repo here; recall cannot be ruled out. The
narrower thing on record: the reference baselines (Sonnet 4 + gpt4o in SWE-Agent)
were contaminated on the same repos and still failed the cells our system
resolves. So recall-only is a weaker explanation than against a clean baseline;
weaker, not eliminated ([`PREREGISTRATION.md`](PREREGISTRATION.md) §12, C2). The
contamination-*free* corroboration is out-of-split: the same methodeutics lineage
merged 81 PRs into 73 cold repos (no training priors) at a ~50% maintainer rate, where
recall of a pretrained repo cannot inflate a merge decision (#10,
[`pr-receipts.VERIFY.md`](pr-receipts.VERIFY.md)).

**Direct check: how close are the wins to gold, and where is recall real?** The
failure mode that retired SWE-bench Verified was models reproducing the human
*gold patch* ([OpenAI, Feb 2026](https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/)).
[`driver/gold_divergence.py`](../driver/gold_divergence.py) measures it directly:
per win, the overlap between the model's changed lines/files and gold's (runtime
artifacts stripped; denominator is WIN rows, missing patches reported, not dropped).
Byte-identity is ~0 for any run — two diffs of the same change differ in git index
hashes, hunk numbers, and context — so the signal is graded line-overlap and the
near-gold tail, not identity.

| run | wins compared | median line-overlap w/ gold | near-gold (≥0.8) |
|---|---|---|---|
| frontier (Sonnet 4.5 + GPT-5.5) | 634 / 694 | 0.11 | 14 (2.2%) |
| open-weight (Composer 2.5 + Flash) | 672 / 672 | 0.31 | 158 (23.5%) |

The result is **not** uniformly exculpatory, and we report it as found. The
**frontier** wins are largely independent of gold (median overlap 0.11; 2.2%
near-gold) — evidence those wins are task-solving, not gold-recall. The
**open-weight** run carries a real recall tail: 23.5% of its wins reproduce gold's
changed lines at ≥0.8 and 18% at ≥0.9, including full-module and multi-file
refactors matching gold near-exactly (`ansible…icx_ping` 187/187 lines;
`ansible…play_iterator` the exact `IteratingStates`/`FailedStates` enum design,
230/232). These are **not** forced one-liners: on 108 of those instances the
frontier pair won the *same task* with a different patch (median overlap 0.16), so
an independent fix demonstrably exists. The cross-model asymmetry is the tell. If
gold-matching were task-forced (one reasonable diff) or capability-driven (better
models converge on the canonical fix), the *stronger* frontier pair would match
gold at least as often as the cheaper one. The opposite holds — the weaker model
matches gold ~10× more (23.5% vs 2.2%) — and a weaker model reproducing the human
gold patch more often than stronger models has one good explanation: it has seen
those solutions. You do not reproduce a 187-line gold diff by being terse. The honest reading is that Composer 2.5
(Kimi K2.5) recalls gold on a meaningful fraction of Pro instances — expected of an
open-weight model trained on public repositories — while the frontier pair does
not. This sharpens the model-side contamination concession rather than refuting it,
and it is exactly why **no capability claim rests on the open-weight resolve rate**
(its number is partly recall-inflated; the frontier run is the cleaner capability
signal). But recall explains the *tail*, not the body: discount the entire
near-gold set as memorized and the open-weight harness still genuinely resolves
≈520–555 of 728 (**~71–76%**) with independent patches — well above any bare model
(best bare ~64%). So the cheap-model result survives at an honest, lower number;
what does not survive is "the model tier is negligible" — the genuine-capability
gap to the frontier pair is ~17–22 points, not the ~2 the raw rates suggest.
Per-instance receipts (overlaps + gold/pred sha256) in
[`runs/scored/gold_divergence.jsonl`](../runs/scored/gold_divergence.jsonl) and
[`runs/flash-composer/gold_divergence.jsonl`](../runs/flash-composer/gold_divergence.jsonl);
recompute with the script and the public dataset.

## 2. "How much is the scaffold vs just stronger models?"

Not separable, and we do not claim to separate it. Our system is Sonnet 4.5 +
GPT-5.5 in the applied-methodeutics scaffold (recon/craft/audit); the baseline is Sonnet 4 + gpt4o in
SWE-Agent, so a we-resolve cell changes **both** scaffold and model class at
once. The clean control (same models through a vanilla scaffold) is not
budget-viable and was not run, so scaffold-only attribution stays **permanently
open**, by disclosure, not deferral ([`PREREGISTRATION.md`](PREREGISTRATION.md)
§12, C1). But the model-tier contribution is now bounded from above, in this repo:
a pre-registered open-weight ablation runs the **same frozen harness** with both
models swapped to a cheaper pair (Composer 2.5 + Gemini Flash 3.5) and resolves
**93.1% vs 95.3%**, a 2.2-point drop. That isn't the same-model control (so
strict scaffold-only attribution stays open), yet most of the result survives
dropping a frontier model class, which is the opposite of "it's just the model"
([`PREREGISTRATION-cheap-ablation.md`](PREREGISTRATION-cheap-ablation.md),
[`COST_BASIS.md`](COST_BASIS.md)). Stronger still, induce the model contribution to
the *strongest* constituent: GPT-5.5 (used here only as a reasoning-off challenger)
scores ~58.6% bare on Pro, and the board leader Opus 4.7 ~64.3%, so against the best
single model the harness still adds 31–37 points, an order beyond any reasoning-budget
lift. Two caveats held: the harnessed generator runs thinking-on against the baseline's
thinking-off, and the ~50-point lift bundles the typed structure with generic
agent-engineering (turns, tools, retries); separating them is future work
([`DISCUSSION.md`](DISCUSSION.md)). One of those bundled factors, turn budget, is
now bounded from the committed traces: the median win resolves in 137 model calls /
59 executed actions, inside the baseline's own 250-turn budget (88% / 96% of wins
under cap, both units; §12), so turn count is not the lever. Tools, retries, and
thinking-on stay bundled.

## 3. "You developed the harness on these repos, so you overfit."

The sharpest objection. The harness was developed on **SWE-bench Verified**, not
Pro ([`METHODOLOGY.md`](METHODOLOGY.md)). Three checks reduce specific overfit
stories; they do not close the question (see #9):

- **Zero repo overlap.** None of the 11 Pro-public repos appear in Verified's dev
  set. No instance- or repo-level path from development into this run.
- **The dev-language is not advantaged.** The only shared channel is language
  (Verified is all Python). The three Python repos resolve **94.7%**; the
  never-developed-against Go/TS/JS repos resolve **95.7%**; the dev-language is a
  point *lower*. Best group (Go, 98.6%) and worst (JS/NodeBB, 74.4%) are both
  novel. We do not see the signature this objection predicts
  ([`RESULTS.md`](RESULTS.md) "Development-overlap check").
- **The reasoning loop did not tune on Pro.** Git history: between init and
  freeze the recon/craft/audit skills got two 1-3 line edits, both anti-cheat
  capture rules; the diagnosis work ran on django/sympy (Verified). Pro-driven
  changes were adapter/capture plumbing only.

These bound the overfit story from the repo and language sides. They are indirect
checks on a post-exposure freeze, not a clean test.

## 4. "The freeze came after you saw Pro, so it doesn't defend."

Conceded on timing: the harness co-evolved with ~3 days of Pro pilots before the
`prereg-pro-v1` freeze (2026-05-26). A freeze after exposure does not by itself
defend against development-overfit, and we do not claim it does. The file-level
audit (#3) shows the co-evolution was confined to adapter plumbing; the empirical
backstop is the language split. The clean defense a freeze is meant to give was
not available here.

## 5. "Your gate lied / you weakened tests to pass."

Under the stated grading pipeline, a lying internal gate or a test edit should
not produce an official WIN: the verdict is recomputed from the captured
**source-only** diff against **restored gold tests** on a fresh container
(PROCEDURE §3), so the gate is never the verdict and a weakened test is restored
before grading. A pre-freeze skill edit also forbids test-editing (#3). This
rules out the intended manufacturing mechanisms; it cannot rule out an unknown
pipeline bug outside them, which is what #6 tests empirically.

## 6. "Local-green, official-red: your WINs are capture artifacts."

We re-graded 6 WINs (3 Go / 2 Python / 1 TS) from their committed diffs on fresh
containers with the **unmodified** upstream grader (pinned commit `ca10a60`):
**6/6 reproduced RESOLVED** ([`RESULTS.md`](RESULTS.md) "Independent re-grade
spot-check"). This rules out a trivial capture bug on the sampled wins. It does
**not** estimate the full-set error rate: n=6 of 694, and a skeptic can fairly
ask for a complete independent re-grade, which is feasible and unrun here.

## 7. "You cherry-picked the denominator."

728 = 731 minus three instances whose **own gold patches** fail the official
grader on a clean base: defective bench instances, named with grader output
([`RESULTS.md`](RESULTS.md) "Excluded instances"). The list was frozen before the
scored run and keys only on gold-patch behavior. **0 INCOMPLETE** in the scored
set; all 34 losses carry non-empty graded patches.

## 8. "The auth stalls let you re-roll losses into wins."

The `PROVIDER_CRED_REJECT` recovery requires four invariants, the binding one a
**0-byte captured patch**: only instances where no submission occurred can be
re-dispatched; a real patch graded `not resolved` stays a LOSS mechanically
([`PREREGISTRATION.md`](PREREGISTRATION.md) §14, [`RUN_NOTES.md`](RUN_NOTES.md)).
Stripped rows go to a parallel ledger. All stalls recovered with 0 instances
lost.

## 9. "This isn't a clean holdout."

This is the **decisive unresolved limitation**, not one item among many. Pro-
public is a clean repo-level holdout relative to *harness development* (zero
shared repos with Verified) but **not** clean relative to *model pretraining*
(the models saw these repos). Held-out Pro grading from Scale (12 different repos,
server-run) was sought and is unavailable. So the one test that would settle it,
cross-repo generalization on unseen repos, cannot be run, and **split-specific
overfit cannot be ruled out empirically on Pro-public.** The checks in #3 reduce
some overfit stories; they do not establish that 95.3% reflects generalizable
task-solving rather than split-specific optimization plus contamination.

## 10. "95% here vs ~50% on novel OSS: which number is real?"

They measure different things. Pro-public hands the loop a visible test suite (an
oracle the gate can stop on) and curated, known-solvable instances; live OSS
gives neither. That difference could plausibly account for much of the gap before
contamination is invoked; we do not decompose it precisely. For a posterior on
real-world performance, use the OSS deployment, not 95.3%: over a ~10-day run the
same lineage merged **81 PRs into 73 cold repos** (0 self-owned, median merged diff
49 lines) at a **~50% rate** (81 of 160 decided). That funnel is committed and
enumerated PR-by-PR in this repo ([`pr-receipts.jsonl`](pr-receipts.jsonl),
verifiable two ways via [`pr-receipts.VERIFY.md`](pr-receipts.VERIFY.md)).

## 11. "Is the OSS merge rate inflated by pre-PR filtering or by how closes are counted?"

The audit is done, and both effects are real and disclosed rather than nested.

- **Pre-PR funnel.** Of 368 triaged issues, 322 were submitted as PRs; 46 (12.5%)
  were throttled or rejected before submission. So the merge rate is conditioned
  on having PR'd, which a live builder facing raw issues is not; the funnel is
  published as a Sankey, not hidden.
- **Denominator.** The headline merge rate is merged / (merged + closed-unmerged)
  among *decided* PRs: **81/160 = 50.6% live** (the profile's "53%" is a dated
  May-20 snapshot of the same quantity, 80/150). It excludes a 129-PR open tail.
- **What "closed" contains.** A close-reason audit of all 79 closed PRs (verbatim
  evidence per PR) finds only **8 are maintainer rejections on the merits**; the
  rest are 28 author-withdrawals (mostly post-program), 13 superseded/duplicate,
  12 no-AI-policy closes, 6 bot/stale, and 12 silent/ambiguous (counted against us
  conservatively). So the merit-conditioned merge rate is 80–91%, while the raw
  rate is 50.6%. We lead with the raw rate; the decomposition is context, not a
  replacement, and every reclassification is mechanically checkable
  ([profile `CLOSE_REASONS.md`](https://github.com/kimjune01/kimjune01/blob/main/CLOSE_REASONS.md)).

## 12. "What did it cost? How many model calls?"

Per instance: median **137 Claude turns** (recon + craft + audit, all retries;
mean 193, p90 291), 13.7% over SEAL's 250-turn reference cap, **plus** a GPT-5.5
challenger on top, so total model calls exceed a single 250-turn agent. But model
calls are not the unit the 250-turn cap meters: a SWE-Agent turn emits one command,
while most Claude calls in these traces are reasoning-only and carry none. Counted
as executed actions, the median win spends just **59 tool calls**, with **96% of
wins under the 250 cap** (88% under even by raw model calls). Both units land the
typical win inside the budget the bare baseline was already granted, so the harness
does not out-resolve it by taking more steps; the right tail and the second model
are what push the total past one bare agent. The per-win, per-stage counts are a
committed receipt: [`turn_budget_audit.py`](../driver/turn_budget_audit.py) →
[`runs/scored/turn_budget.jsonl`](../runs/scored/turn_budget.jsonl). Two cost
figures, kept separate because they are not the same thing:

- **Replicable economic cost at API pricing: ~$5.14 / instance** for the frontier
  pair (Sonnet 4.5 leg $4.73 + GPT-5.5 ~$0.42, every leg metered at public rates incl.
  cache). The open-weight-generator pair does the same work for **~$0.41** (~12.6× cheaper). This
  supersedes an earlier "~$2.60" headline, which was *cash-per-billed-instance* and
  priced only the Claude leg; full line-by-line derivation in
  [`COST_BASIS.md`](COST_BASIS.md).
- **This run's actual cash outlay: ≈ $858 marginal + ~$58 EC2.** Most legs ran on flat
  subscriptions (Claude Max $200/mo, codex, Cursor) at ~$0 marginal, so the cash was
  far below the economic figure, non-portable by construction, which is why the
  **economic** rate is the one to quote. The cash-vs-economic reconciliation is in
  [`COST_BASIS.md`](COST_BASIS.md#cash-vs-economic).

And "fast" is **per instance**, not end-to-end: median ~13 min per instance, but
the full 728-instance run took **~3.5 days** of wall-clock, bounded by fleet size
(4–8 boxes), the three auth stalls, and quota pauses, not by per-instance speed
([`RUN_NOTES.md`](RUN_NOTES.md)).

Turn/token stats cover the 681/728 instances whose trajectories survived teardown
(median ~71k output tokens/instance). See [`SCOREBOARD.md`](SCOREBOARD.md).

---

**Net.** The contamination caveat is calibrated, the grading pipeline blocks the
intended gate/test-weakening exploits, the denominator is honest, and the
repo-level and language-split checks reduce specific development-overfit stories.
The genuine unclosed limitation is decisive: **without a clean held-out Pro
evaluation, split-specific overfit cannot be ruled out**: the checks here narrow
some overfit stories but do not close the question. Treat Pro-public as the
audition it is.
