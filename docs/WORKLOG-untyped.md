# swebench-pro worklog -- `prereg-pro-v1-untyped` (typed-mode ablation)

Newest first. Scored-run trail for the frozen artifact `prereg-pro-v1-untyped`: the clean
single-factor ablation isolating the methodeutic typing (`/ask` vs `/recon`). Sibling to the
`prereg-pro-v1` headline; the typed verdicts (`runs/scored/run.jsonl`) are the frozen paired
comparator, read but never re-run. Pre-registration: `docs/PREREGISTRATION-untyped-ablation.md`.

## 2026-06-04 -- FREEZE: `prereg-pro-v1-untyped` cut, ablation run begins

**What this run measures.** `Delta_typing = p_typed - p_untyped`, paired on a seeded-random sample
of the 728 eligible. The untyped arm is the full headline pipeline (Sonnet 4.5 generator + GPT-5.5
codex challenger + deterministic gate + outer loop) with **one factor removed**: the `inquire`
stage runs the `/ask` skill (same diagnosis goal, no applied epistemology) instead of `/recon`
(Peircean abduction/deduction/induction, typed hypothesis graph, confidence-by-mode). Everything
else is byte-identical. If `Delta` is materially positive, the typing encodes reasoning (the paper's
central promise); if `Delta ~ 0`, the encoding claim fails. The answer is the answer.

**Single-factor diff, audited.** `/ask` = `/recon` minus exactly three things (mode labels,
confidence-by-mode, typed graph nodes), identical in goal, process, `git log` blame, suspect-set
pruning, imperative phases, and handoff shape. Codex-sniffed twice (GPT-5.5): first pass flagged
non-typing confounds (`/ask` was missing `git log`, softer pruning, lower procedural force); all
fixed; second pass confirmed *"Delta is now a clean measurement of the typing intervention alone."*
The demand-characteristic self-reference was then stripped so `/ask` reads as a plain standalone
skill, symmetric with `/recon`. `/ask` lives in the repo as a real file (skeptics get a real copy).

**Frozen harness untouched.** The measurement contract (`pro_pilot` setup/gate/capture/grade,
`rung5` craft/audit, `skills/recon|craft|audit`) is byte-identical and unmodified -- `git status`
clean. The new code is the arm (`pro_untyped.py`, imports the frozen harness, swaps only the skill)
and the runner (`ablation_run.py`, `ablation_fleet.sh`, `ablation_bayes.py`).

**Sample.** Seeded-random draw of the 728 eligible, `seed=20260604`, `sha256[:16]=a6e6a099d4660d49`,
`tasks/ablation_sample.txt`. Fair across all 11 repos. 728/728 pairable against the frozen typed
ledger (694 WIN / 34 LOSS = 95.3%).

**Bayesian stopping (estimation, not test).** Dirichlet(1,1,1,1) on the 2x2 paired table;
`Delta = pi(typed-only-win) - pi(untyped-only-win)`. Stop on PROVEN `P(Delta>0) >= 0.95` / NULL
(95% CI within +/-0.03) / CONVERGED (95% CI width <= 0.10); else continue to the 728 census. Tokens
are subscription/$0, so `n` is open. Pre-data prediction (recorded, not a prior): `Delta` small and
positive (~2-8 pts), since `/ask` keeps codex + loop and lands high.

**Infra-fault guard (learned from the headline run).** `ablation_bayes.py` quarantines any untyped
LOSS faster than `MIN_REAL_SECS=180s` out of the `Delta` table (auth-rotation / quota deaths die
empty in <400s and the parser mis-records them as LOSS; a real loss runs 764-3025s). Verdict-
independent, so it cannot launder a real loss. WINs never quarantined (the grader cannot pass an
empty patch). Fast-LOSS clusters trigger the `PROVIDER_CRED_REJECT` runbook (halt -> re-push creds
-> `--redo`).

**Smoke (pre-freeze, no-credit telemetry).** 1 box, 1 instance (`ansible-be2c376a`): the untyped
pipeline ran end-to-end (`/ask` -> craft+codex -> gate -> official grade) and resolved **WIN @ 777s**
(healthy regime). Validates fleet install + Max/codex auth + the skill swap + the grade path. The
result is NOT counted toward the scored `Delta` (the post-freeze fleet re-runs ansible).

**Run plan.** <=8 EC2 boxes (`m7i.xlarge`, us-west-2), `ablation_fleet.sh provision 8`, monitor via
`ablation_fleet.sh delta` until a terminal verdict, pull trajectories + diffs before teardown.

**Freeze tag:** annotated `prereg-pro-v1-untyped` points at this commit.
