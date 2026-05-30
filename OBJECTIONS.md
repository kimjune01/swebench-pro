# Objections — reading the 95.33% honestly

95.33% on SWE-bench Pro-public is a striking number, and a striking number on a
contaminated public split should be assumed overfit until it survives the obvious
attacks. This document states the attacks plainly and bounds each one against the
evidence in this repo. Where an objection lands, it is conceded.

The stance up front: **this is a system result on a contaminated public split,
and it is the weakest evidence in the program.** Do not use 95.33% for capability
inference. The load-bearing evidence for the method is elsewhere — out-of-
distribution OSS deployment, cross-model transfer, and the legibility of the
trail. Pro-public is an audition: "a frozen, instance-blind system resolved
694/728 under the official grader," and nothing stronger.

## 1. "It's contamination — the models memorized these repos."

Conceded as unexcludable, which is why there is **no capability claim**. Sonnet
4.5 and GPT-5.5 both postdate every repo here; recall cannot be ruled out. The
narrower thing on record: the reference baselines (Sonnet 4 + gpt4o in SWE-Agent)
were contaminated on the same repos and still failed the cells our system
resolves. So recall-only is a weaker explanation than against a clean baseline —
weaker, not eliminated ([`PREREGISTRATION.md`](PREREGISTRATION.md) §12, C2).

## 2. "How much is the scaffold vs just stronger models?"

Not separable, and we do not claim to separate it. Our system is Sonnet 4.5 +
GPT-5.5 in the recon/craft/audit scaffold; the baseline is Sonnet 4 + gpt4o in
SWE-Agent — so a we-resolve cell changes **both** scaffold and model class at
once. The clean control (same models through a vanilla scaffold) is not
budget-viable and was not run, so scaffold-only attribution stays **permanently
open**, by disclosure, not deferral ([`PREREGISTRATION.md`](PREREGISTRATION.md)
§12, C1). The cross-model transfer evidence that bears on this lives outside this
repo; within Pro-public, the scaffold/model split is unidentified.

## 3. "You developed the harness on these repos, so you overfit."

The sharpest objection. The harness was developed on **SWE-bench Verified**, not
Pro ([`METHODOLOGY.md`](METHODOLOGY.md)). Three checks reduce specific overfit
stories — they do not close the question (see #9):

- **Zero repo overlap.** None of the 11 Pro-public repos appear in Verified's dev
  set. No instance- or repo-level path from development into this run.
- **The dev-language is not advantaged.** The only shared channel is language
  (Verified is all Python). The three Python repos resolve **94.7%**; the
  never-developed-against Go/TS/JS repos resolve **95.7%** — the dev-language is a
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
pipeline bug outside them — which is what #6 tests empirically.

## 6. "Local-green, official-red — your WINs are capture artifacts."

We re-graded 6 WINs (3 Go / 2 Python / 1 TS) from their committed diffs on fresh
containers with the **unmodified** upstream grader (pinned commit `ca10a60`) —
**6/6 reproduced RESOLVED** ([`RESULTS.md`](RESULTS.md) "Independent re-grade
spot-check"). This rules out a trivial capture bug on the sampled wins. It does
**not** estimate the full-set error rate: n=6 of 694, and a skeptic can fairly
ask for a complete independent re-grade, which is feasible and unrun here.

## 7. "You cherry-picked the denominator."

728 = 731 minus three instances whose **own gold patches** fail the official
grader on a clean base — defective bench instances, named with grader output
([`RESULTS.md`](RESULTS.md) "Excluded instances"). The list was frozen before the
scored run and keys only on gold-patch behavior. **0 INCOMPLETE** in the scored
set; all 34 losses carry non-empty graded patches.

## 8. "The auth stalls let you re-roll losses into wins."

The `PROVIDER_CRED_REJECT` recovery requires four invariants, the binding one a
**0-byte captured patch** — only instances where no submission occurred can be
re-dispatched; a real patch graded `not resolved` stays a LOSS mechanically
([`PREREGISTRATION.md`](PREREGISTRATION.md) §14, [`RUN_NOTES.md`](RUN_NOTES.md)).
Stripped rows go to a parallel ledger. All stalls recovered with 0 instances
lost.

## 9. "This isn't a clean holdout."

This is the **decisive unresolved limitation**, not one item among many. Pro-
public is a clean repo-level holdout relative to *harness development* (zero
shared repos with Verified) but **not** clean relative to *model pretraining*
(the models saw these repos). Held-out Pro grading from Scale (12 different repos,
server-run) was sought and is unavailable. So the one test that would settle it —
cross-repo generalization on unseen repos — cannot be run, and **split-specific
overfit cannot be ruled out empirically on Pro-public.** The checks in #3 reduce
some overfit stories; they do not establish that 95.33% reflects generalizable
task-solving rather than split-specific optimization plus contamination.

## 10. "95% here vs 53% on novel OSS — which number is real?"

They measure different things. Pro-public hands the loop a visible test suite (an
oracle the gate can stop on) and curated, known-solvable instances; live OSS
gives neither. That difference could plausibly account for much of the 95→53 gap
before contamination is invoked — but we have **not** decomposed the gap and do
not claim a specific split. For a posterior on real-world performance, use the
OSS deployment, not 95.33%.

## 11. "Is the OSS 53% inflated by pre-PR filtering?"

A fair and currently open question, and the reason the OSS number is not yet
load-bearing here. The honest denominator is merged / *attempted*, with any
issue-selection or pre-PR filtering disclosed; that audit (the full
sampled-issue → attempted → PR'd → merged/closed log) is **pending** and called
out as such. Until it lands, 53% is a pointer, not a result.

## 12. "What did it cost? How many model calls?"

Per instance: median **139 Claude turns** (recon + craft + audit, all retries;
mean 193, p90 294), 13.7% over SEAL's 250-turn reference cap — **plus** a GPT-5.5
challenger on top, so total model calls exceed a single 250-turn agent. Two cost
figures, kept separate because they are not the same thing:

- **Observed cash outlay this run:** dominated by EC2 (~$58, ~$0.08/instance),
  because Claude billed on the Max plan ($0 marginal) until a paid-API tail for
  the last ~17% of instances.
- **Replicable marginal cost under public API pricing:** **not yet estimated.**
  The Max-plan subsidy makes this run's cash outlay non-portable; a reproducer
  paying PAYG for ~139 Claude turns + the codex challenger per instance would pay
  materially more, and we have not computed that figure.

Turn stats cover the 681/728 instances whose trajectories survived teardown.

---

**Net.** The contamination caveat is calibrated, the grading pipeline blocks the
intended gate/test-weakening exploits, the denominator is honest, and the
repo-level and language-split checks reduce specific development-overfit stories.
The genuine unclosed limitation is decisive: **without a clean held-out Pro
evaluation, split-specific overfit cannot be ruled out** — the checks here narrow
some overfit stories but do not close the question. Treat Pro-public as the
audition it is.
