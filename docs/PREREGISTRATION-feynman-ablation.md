# Pre-registration -- SWE-bench Pro, perturbation ablation (`ask-feynman` vs `recon`)

The one-arm, single-factor ablation under §4.5c of *The Methodeutic Harness on SWE-bench Pro*.
Sibling to `prereg-pro-v1` (the frozen `/recon` headline, which is the **baseline here**) and to
`prereg-pro-v1-untyped` (the typing null). All ship under the shared Zenodo DOI.

**One arm this run.** The perturbation baseline already exists -- the frozen `/recon` run (728,
`runs/scored/run.jsonl`), which perturbs. We build and run **only the deprived static arm**
(`ask-feynman`) and pair it against that frozen baseline. No second arm.

## 0. What this tests (the most central operation)

The typing null (`prereg-pro-v1-untyped`, Delta = -0.013 [-0.062, +0.030]) showed the inquiry's
*labels* are inert; the model performs the inquiry without them. The surviving question is whether
a specific *operation* matters. This run tests the most theoretically central one: **scoped
diagnostic perturbation = perturbative abduction.** The paper's §inquiry-frame rests on it -- "kill
conditions are not approximations; they are executions"; code is a privileged inquiry substrate
because it is *perturbable*. If perturbation at diagnosis is inert, that frame is decorative; if it
is load-bearing, it is the mechanism.

**The cut (Feynman vs Edison).** `recon` may run scoped experiments to *discover* the cause -- drop a
print, run a narrowed test, bypass-a-component-to-isolate (the dimmer move): **Edison**, try the
filament. `ask-feynman` may not run anything during diagnosis; it reasons statically and may only
*imagine* what an experiment would show: **Feynman's algorithm**, "write down the problem, think real
hard, write down the solution." So the variable is precisely **actual execution vs mental simulation
of it.** Solution-attempting perturbation (craft testing fixes against the gate) is unchanged in both
arms; only *diagnostic* perturbation is removed.

**What the estimand isolates -- directed, not arbitrary, perturbation.** Both arms carry `craft`
unchanged, and craft already perturbs: it writes a fix, runs the suite, reads the failure, retries.
Blind search *is* perturbation, and it is held constant across arms. This ablation therefore does NOT
test "perturbation vs none" -- it cannot, craft is frozen in both. It removes only the stage where
perturbation is *aimed*: recon's scoped diagnostic probe, perturbing *to discriminate between
hypotheses* rather than to stumble onto a passing test. The treatment is **scoped *diagnostic*
perturbation (the directed probe); arbitrary search-perturbation is a held-constant covariate, not
the manipulated variable.** This is why the predicted interaction is mechanistic, not cosmetic:
directed perturbation should pay exactly when arbitrary perturbation has run out of road (UNDER:
craft thrashed -- re-entry/experiments>=2) and collapse toward zero when it has already converged
(DET: `experiments==0 AND no re-entry`, no remaining fork for a probe to resolve).

## 1. Import

Inherits every discipline from `PREREGISTRATION.md` at the `prereg-pro-v1` SHA: predicate (§1), two
modes (§2), failure-mode state machine (§4), eligible denominator (§6, 728), provenance (§10),
confound discipline (§12), freeze (§13). Inherits the **infra-fault guard** from
`prereg-pro-v1-untyped` (fast-LOSS quarantine, `MIN_REAL_SECS`). Deltas below override only what is named.

## 2. The arm -- one capability removed

`ask-feynman` (`skills/ask-feynman/skill.md`) is **`/recon` with scoped diagnostic perturbation
removed, and nothing else** -- same goal, same Peircean typing, same hypothesis graph, same `git log`
blame, same suspect-set pruning, same emit schema (`# Recon:`), same re-entry, same downstream
implement + codex + gate + outer loop. Derived from `/recon` (not `/ask`) so **typing is held
constant** against the frozen `/recon` baseline; the single factor is perturbation alone.

The diff vs `/recon`, concentrated in one policy:

| | `/recon` (baseline, frozen) | `ask-feynman` (this arm) |
|---|---|---|
| diagnosis box | full (read + execute) | **read-only** (cat/grep/`git log`; no execution) |
| reproduce failure | runs the gate | reads the provided failing-test source + error |
| distinguish hypotheses | runs cheap experiments (print, isolate) | **imagines** them; states predicted result, may not run |
| typing / graph / emit / craft / gate | -- | identical |

Receiver-bias-immune (codex red-team, 2026-06-04): identical handoff shape and downstream, so the
implementer/challenger/gate cannot be biased toward one arm's structure. Single operation varied, so
no confound bundle.

## 3. Sampling -- stratified by decision-relevant perturbation, ordered

The stratifier is **pre-committed and read from the frozen `/recon` trajectories** (the baseline's
own execution record), via `driver/perturbation_strata.py`. An instance is scored by manufactured-diff
perturbation (print-injection / modified-code runs / isolating bypass, navigation excluded) + re-entry
(a depth>=1 recon trajectory = the first diagnosis was killed -> perturbation was decision-relevant):

- **UNDERDETERMINED** (`re-entry OR experiments>=2`): **99** instances. Primary endpoint.
- **MID**: 31.
- **DETERMINED** (`experiments==0 AND no re-entry`): **552**. Control.

(682 instances classified from 1048 frozen `/recon` trajectories. The DET majority -- ~81% -- is a
separate finding: Pro's failures are mostly statically resolvable; perturbation has a minority of
cases to bite on, which is exactly why the strata split is load-bearing rather than cosmetic.)

`tasks/perturbation_sample.txt` is the **ordered** run list -- UNDER first (highest perturbation
first), then MID, then DET -- committed at freeze with its hash. The Bayesian run front-loads the
discriminating cases ("bayesian, ordered properly").

This is a proxy for cause-determinacy, and **pre-treatment** (it conditions on the *prior frozen*
run, not on this arm's outcome -- no collider). Headline is scoped to the strata, not "all of Pro."

## 4. The Bayesian run -- the interaction is the result

Estimand per stratum: **Delta_perturb = p_recon - p_feynman** (paired vs the frozen `/recon` verdict
for the same instance), Dirichlet(1,1,1,1) on the 2x2 paired table, same machinery as the typing run.

```
  PRIMARY  (UNDERDETERMINED stratum):  predict Delta > 0  (recon perturbs and resolves what feynman, thinking only, cannot)
  CONTROL  (DETERMINED stratum):       predict Delta ~ 0  (static reasoning suffices; the gap names the cause)
  HEADLINE = the INTERACTION: Delta_UNDER > 0  AND  Delta_DET ~ 0
```

Ordered stopping: run UNDER first; stop the primary on `P(Delta_UNDER > 0) >= 0.95` (PROVEN),
`95% CI within +/-0.03` (NULL), or `CI width <= 0.10` (CONVERGED). Then run a DET control sample to
confirm the tie (CI within the ROPE). Tokens subscription/$0; `n` open; full-728 backstop per stratum.

A clean PROVEN-on-UNDER + NULL-on-DET interaction vindicates the inquiry-frame's perturbation claim,
scoped. A NULL even on UNDER is the deeper finding: the model performs perturbative abduction *in its
head* (mental simulation suffices), so the empirical act is internalized too.

## 5. Budget -- equal ceiling, early return allowed

`ask-feynman` gets the **same per-instance budget ceiling** as `/recon` and **may return early**.
Under-utilization is `ask-feynman`'s own failure mode, NOT a confound to launder by forcing spend:
the skill carries *identical thoroughness exhortations* (read deeply, trace fully, don't give up
early), so an early return means static reasoning genuinely bottomed out, not that the prompt
under-drove it. Utilization (tokens / tool-calls / wall-time) is logged as the **mechanism trace** --
an early, low-utilization static loss on the UNDER stratum is the smoking gun.

## 6. Enforcement

The `ask-feynman` diagnosis runs against a **read-only box helper**: `cat`/`grep`/`ls`/`git log`
permitted; any execution (python/node/pytest/go/print-and-run/the gate) refused. Craft (downstream)
gets the full box + gate, identical to the baseline. The static constraint binds the *diagnosis stage
only*.

## 7. Runner

`driver/pro_feynman.py` (the arm) = `pro_pilot` with the recon stage swapped for `ask-feynman` and a
read-only diagnosis box; craft/audit/capture/grade imported frozen. `driver/feynman_run.py` shards
`tasks/perturbation_sample.txt` in order. `driver/feynman_bayes.py` pairs the `feynman` ledger vs the
frozen `/recon` `run.jsonl`, computes per-stratum Delta, prints the interaction verdict. Fleet reuses
`ablation_fleet.sh` (claude + codex). The baseline is NOT re-run.

## 8. What does NOT change

Grader (official, no bespoke), state machine + infra-fault guard (parent §4 + untyped guard), the
frozen `/recon` comparator (`run.jsonl`, read never re-run), provenance pulled before teardown,
surface = Pro.

## 9. Freeze tag

`prereg-pro-v1-feynman` (annotated). SHA + `perturbation_sample.txt` hash + the `perturbation_strata.py`
classifier (frozen) recorded in the worklog before the scored run.

## 10. Threats & disclosures

- **CLI drift (disclosed, not controlled).** The frozen `/recon` baseline ran on `claude-code@2.1.150`;
  that version is no longer installable, so this arm runs `2.1.165` (codex held at `0.134.0`). The
  intervening changelogs are patch-level (no agent-loop or tool-semantics change); reviewed and taken
  on faith per operator direction rather than re-running a fresh `/recon` control. A reader who rejects
  this can discount the absolute rates; the **paired, same-instance** Delta is far more robust to a
  uniform CLI shift than either arm's level is, and the interaction (UNDER vs DET) is robust still --
  a CLI delta would have to act *differentially across strata* to manufacture the predicted pattern.
- **Scoping.** The headline is scoped to the perturbation strata read off Pro's own `/recon`
  trajectories, not "all code" and not "all benchmarks." The strata proxy is pre-treatment (conditions
  on the prior frozen run, never on this arm's outcome) but is still a *proxy* for cause-determinacy;
  a misclassified instance dilutes toward the null, it cannot manufacture the interaction.
- **Classifier fix during pilot (pre-freeze).** The 3-instance pilot caught two bugs in
  `perturbation_strata.py`: it emitted Claude's lossy project-dir ID encoding (`flipt-io--flipt-<sha>`)
  instead of the canonical dataset ID, and a non-greedy regex truncated SHAs beginning `d<digit>`.
  Both fixed before freeze (canonical IDs resolved by re-encoding `run.jsonl` and matching; greedy
  match anchored to the trajectory filename). Piloting-finds-faults is the intended order; the frozen
  classifier is the corrected one, and the strata counts above are post-fix.

---

**Preregistered:** 2026-06-05. **Arm:** `ask-feynman` (static), one arm; baseline = frozen `/recon`.
**Estimand:** `Delta_perturb = p_recon - p_feynman`, paired, per stratum. **Headline:** the interaction
(Delta_UNDER > 0, Delta_DET ~ 0). **Strata:** UNDER 99 / MID 31 / DET 552, ordered UNDER-first.
**Budget:** equal ceiling, early-return allowed. **Tag:** `prereg-pro-v1-feynman`.
