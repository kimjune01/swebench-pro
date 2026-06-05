# For skeptics: verify it yourself

This is a **public, contamination-prone** split and a **system/harness** result, not a
model-capability claim. So this page does not argue. [`OBJECTIONS.md`](OBJECTIONS.md)
argues. This page hands you the **prompt to check each doubt yourself**: paste it into
your own coding agent (codex, Claude Code, Cursor, Gemini CLI, whatever), point it at a
clone of this repo, and let it confirm or refute the claim against the committed
artifacts. Trust is the one axis an AI can't win against a human; verifiability is the
answer, so here are the means.

Each section is a question a skeptic *should* ask, followed by a ready-to-paste prompt.
Run them on your own machine and tokens. If any check fails, that's a finding. Open an
issue with the transcript.

---

## "It gamed the grader / weakened the tests."

> Clone github.com/kimjune01/swebench-pro. Pick 10 random WIN instances from
> `runs/scored/run.jsonl`. For each, extract its captured **source-only** diff from
> `runs/scored/artifacts.tar.zst`, apply it to a fresh clean checkout, restore the
> instance's **gold** tests, and run the **unmodified** official SWE-bench Pro grader
> (pinned commit `ca10a60`) in Docker. Report resolved/10 and whether each matches the
> recorded verdict. Confirm the captured diff touches no test files.

## "95.3% is just contamination — the models memorized these repos."

> Contamination is conceded in `docs/OBJECTIONS.md` #1 (it's model-side, universal to
> every leaderboard entry). Don't re-litigate it; check the **contamination-free**
> evidence instead. (1) Run the GraphQL in `docs/pr-receipts.VERIFY.md` and confirm the
> cold-repo OSS results (~81 merged into ~73 repos the models had no priors for). (2) In
> `docs/RESULTS.md`, check the development-overlap split: the dev language (Python)
> resolves *lower* than never-developed languages, the opposite of what contamination-
> by-familiarity predicts. Report both.

## "It's just the strong model, not the harness."

> In this repo, check three things and report. (1) The open-weight run
> (`runs/flash-composer/`) swapped the entire model pair to a cheap open-weight
> generator and still resolved 678/728 (93.1%) on the same grader. (2) The control grid
> in `docs/DISCUSSION.md`: same model (Sonnet 4.5), standard SWE-Agent scaffold scores
> ~43.6% vs ~95.3% in this harness. (3) The "induce to the stronger model" bound: even
> bare GPT-5.5 (~58.6%) or the Pro board leader Opus 4.7 (~64.3%) sit 31–37 points below
> 95.3%. Note the disclosed confounds (generator ran thinking-on; the lift bundles
> structure with generic agent-engineering), with turn budget excepted: the median
> win stays inside the baseline's 250-turn cap by both model calls and executed
> actions (`runs/scored/turn_budget.jsonl`, OBJECTIONS §12). Tell me whether the
> attribution claims are stated as bounded (they should be), not as proof.

## "You attribute the lift to 'perturbation', but your craft loop perturbs too." *(in-flight result)*

> The mechanistic claim is that **directed diagnostic** perturbation is load-bearing — not
> perturbation-in-general, since the `craft` stage already perturbs (blind try-and-rerun) in
> every arm. Check that the pre-registered ablation actually isolates the directed probe and
> nothing else. (1) Diff `skills/ask-feynman/skill.md` against `skills/recon/skill.md` and
> confirm the **only** removed capability is *execution during diagnosis* (read-only box:
> cat/grep/`git log` allowed, python/pytest/print-and-run refused) — same typing, hypothesis
> graph, emit schema, and identical downstream `craft`+gate in both arms
> (`docs/PREREGISTRATION-feynman-ablation.md` §2, §6). (2) Confirm the strata are
> **pre-treatment**: `driver/perturbation_strata.py` classifies each instance off the *frozen
> `/recon`* trajectories (re-entry OR experiments≥2 → UNDERDETERMINED), never off this arm's
> outcome — no collider. (3) Recompute the per-stratum delta yourself: pair the `feynman`
> ledger (`runs/scored/feynman*.jsonl`) against the frozen `/recon` verdicts
> (`runs/scored/run.jsonl`) with `driver/feynman_bayes.py status`, and confirm UNDER shows
> `Delta≈+0.278, P(Delta>0)≈0.996` while DET trends toward zero. Report whether the DET control
> has reached the registered ROPE-close (±0.03) yet — at time of writing it has **not**, so the
> interaction is stated as in-flight and the difference-of-differences (`P≈0.981`) is labeled
> supplementary, not substituted for the registered rule. Flag it if you find that swap.

## "You developed the harness on these repos, so you overfit."

> The harness was built on SWE-bench Verified, not Pro. Verify the three overfit checks
> in `docs/OBJECTIONS.md` #3 against the repo: (1) zero repo overlap between the 11
> Pro-public repos and Verified's dev set; (2) the dev-language-not-advantaged language
> split in `docs/RESULTS.md`; (3) the git history of `skills/{recon,craft,audit}` between
> repo init and the `prereg-pro-v1` freeze. Confirm Pro-driven changes were
> adapter/capture plumbing only, not reasoning-loop tuning. Report what you find.

## "The 34 losses are fake or capture artifacts."

> In `runs/scored/run.jsonl`, find the 34 LOSS instances. Confirm each has a **non-empty**
> captured patch in `runs/scored/artifacts.tar.zst` (no 0-byte/empty captures padding the
> win column). Then re-grade a sample of them on fresh containers with the official grader
> and confirm they reproduce as `not resolved`. Cross-check against the loss anatomy in
> `docs/RESULTS.md`.

## "The cost numbers are hand-waved."

> Recompute the cost from scratch. Follow `docs/COST_BASIS.md`: sum the per-message token
> usage in the committed Claude Code session logs and codex rollouts inside
> `runs/scored/artifacts.tar.zst`, and the Cursor CSV in `runs/flash-composer/`, then
> multiply by the published API rates in that doc. Confirm the economic figures
> (~$5.14/instance frontier, ~$0.41 open-weight) and the cash-vs-economic reconciliation.
> Flag any leg whose rate is imputed rather than first-party (the Composer leg is priced
> at its open-weight K2.5 base rate, and should say so).

## "The OSS merge rate is inflated by filtering or by how closes are counted."

> Run the verification block in `docs/pr-receipts.VERIFY.md`: the GraphQL queries against
> live GitHub (use the **full epoch timestamp** `2026-05-09T00:34:00Z`, not a bare date or
> midnight; the doc explains why), and the Python recompute from `docs/pr-receipts.jsonl`.
> Confirm ~81 merged / ~50% merge rate among decided PRs. Then check the close-reason
> breakdown: confirm most closures are non-merit (no-AI policies, withdrawals, duplicates),
> so the merge rate is a floor on correctness.

## "The auth stalls let you re-roll losses into wins."

> Read `docs/PREREGISTRATION.md` §14 (`PROVIDER_CRED_REJECT`) and `docs/RUN_NOTES.md`.
> Confirm the recovery rule re-dispatches **only** instances that captured a **0-byte
> patch** (no submission occurred), while any non-empty patch graded `not resolved` stays
> a LOSS mechanically. Check that no real-output verdict was reclassified. Report whether
> the rule could, even in principle, convert a graded loss into a win.

## "The re-grade was too small to mean anything."

> Two re-grades are committed. The frontier run: a 6-WIN cross-language spot-check (6/6).
> The open-weight run: a 60-WIN stratified sample, ledger `runs/scored/regrade_win.jsonl`,
> reported 60/60 with 0 flips. Inspect the ledger, then run your own re-grade on any sample
> size you like with the official grader and report the flip rate. Same-grader re-grade is
> deterministic, so a 0 flip rate on 60 implies ~0 on the rest. Confirm or refute.

## "Reproduce the headline rate, not just the recorded verdicts."

> The strongest check. Following `CLAUDE.md` and `docs/PROCEDURE.md`, run the
> **harness-under-test** on a random ~20-instance sample from `runs/audit/eligible.txt`
> (print your seed and ids), grade each with the **unmodified official** grader, and report
> resolved/20 with a confidence interval and whether it's consistent with 95.3%. Inspect
> `driver/bootstrap.sh` first and confirm it only pulls the pinned official eval repo, runs
> the grader in Docker, and uses your credentials locally.

---

If a check comes back against us, that is the most valuable thing you can send: open an
issue with the transcript and the instance ids. The losses and the methods are committed
precisely so this is possible.
