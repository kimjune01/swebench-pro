# swebench-pro

A recon→craft→audit agent pipeline pointed at **SWE-bench Pro**, run end-to-end
under a frozen, pre-registered protocol. Sibling to
[`swebench-verified`](https://github.com/kimjune01/swebench-verified) — one repo
per benchmark so each run's artifacts and number stand on their own.

## Result

**694 / 728 eligible resolved = 95.33%**, official SWE-bench Pro grader, single
frozen instance-blind artifact (`prereg-pro-v1`), whole eligible set in one
measurement. 728 terminal verdicts: 694 WIN, 34 LOSS, **0 INCOMPLETE** — full
coverage, no instance left un-graded. Run window 2026-05-27 20:02Z →
2026-05-30 17:37Z (~72 h wall-clock). Every figure here is recomputable from
`runs/scored/run.jsonl`; every verdict is re-gradable from its committed
source-only diff under `runs/scored/artifacts/`.

This is a **system** number, not a capability claim. The system is a
Sonnet-4.5 generator plus a GPT-5.5 craft challenger — both contaminated on
these repos, the scaffold-vs-model axis a deliberately unclosed confound. The
defensible reading is "this frozen system resolved 694/728 under official
grading," not "the model can solve 95% of SWE-bench Pro." What the system is and
why the confound stays open: [`METHODOLOGY.md`](METHODOLOGY.md) and
[`PREREGISTRATION.md`](PREREGISTRATION.md) §7/§12.

| repo | W | L | %win |
|---|---:|---:|---:|
| navidrome | 57 | 0 | 100.0 |
| tutao | 20 | 0 | 100.0 |
| qutebrowser | 78 | 1 | 98.7 |
| gravitational | 75 | 1 | 98.7 |
| future | 60 | 1 | 98.4 |
| flipt | 83 | 2 | 97.6 |
| element | 54 | 2 | 96.4 |
| protonmail | 62 | 3 | 95.4 |
| ansible | 89 | 6 | 93.7 |
| internetarchive | 84 | 7 | 92.3 |
| NodeBB | 32 | 11 | 74.4 |
| **total** | **694** | **34** | **95.33** |

Ten of eleven repos land at or above 92%; NodeBB at 74.4% is the lone outlier
and carries 11 of the 34 losses. All 34 losses are real graded `not resolved`
verdicts on **non-empty** patches (median 3.6 KB, max 194 KB, none empty) — the
loop produced fixes the official tests rejected, not nothing. Full breakdown,
runtime distributions, and per-loss artifact pointers in
[`RESULTS.md`](RESULTS.md).

## How it was measured

The honest one-paragraph version: a frozen multi-model pipeline ran the full
728-instance eligible set (731 dataset instances minus 3 pre-audited gold-patch
defects), one instance at a time, each through recon → craft (with a GPT-5.5
adversary) → audit → source-only capture → an official-grader re-grade on a
fresh container. The agent's internal gate is only a stopping signal; the
verdict is always the official grade of the captured diff. The run was not
clean wall-clock: three OAuth-credential stalls and a mid-run switch from
Max-subscription billing to paid API billing are part of the methodology, all
recovered under the prereg's pre-committed `INCOMPLETE`-rewrite discipline with
zero instances lost. The provenance of those interruptions is documented, not
buried — see [`RUN_NOTES.md`](RUN_NOTES.md). Reproduction is aggregate (resolve-
rate within sampling variance over the 728 set), not per-instance replay; the
agent is stochastic.

## Navigation

Read in roughly this order depending on what you're here to do.

| if you want to… | read |
|---|---|
| see the result and audit the numbers | [`RESULTS.md`](RESULTS.md) — per-repo W/L, runtime distributions, loss analysis, how to re-grade any verdict |
| understand how the number was produced | [`METHODOLOGY.md`](METHODOLOGY.md) — system, per-instance pipeline, what counts as a verdict, billing modes |
| check the rules the run was held to | [`PREREGISTRATION.md`](PREREGISTRATION.md) — predicate, failure-mode state machine, contamination accounting, freeze gate (frozen `prereg-pro-v1`, 2026-05-26) |
| audit the run's provenance | [`RUN_NOTES.md`](RUN_NOTES.md) — the three auth stalls, recovery sequence, cost shape, the off-peak-streak vs on-peak-storm load pattern |
| reproduce a result from scratch | [`PROCEDURE.md`](PROCEDURE.md) — bootstrap → task → pilot → official grade; pinned versions; reproduction contract |
| read the chronological trail | [`WORKLOG.md`](WORKLOG.md) — the scored-run journal, newest first |
| know upstream-grader behaviors to expect | [`docs/bench-defects.md`](docs/bench-defects.md) — silent grader deadlocks, container leaks, indistinguishable losses, and the mitigations |
| understand why the adapter is shaped this way | [`PRO_PORT.md`](PRO_PORT.md) — the original port plan and background |

Supporting specs: [`PREREGISTRATION-cheap-ablation.md`](PREREGISTRATION-cheap-ablation.md)
(companion ablation spec), [`LOCAL_ISO.md`](LOCAL_ISO.md) (local sandbox notes),
[`CLAUDE.md`](CLAUDE.md) (agent orientation / one-command setup),
[`docs/retros/`](docs/retros/) (lessons compressed for the next run).

## The goal this run was an audition for

A single **frozen, instance-agnostic artifact** that clears SWE-bench Pro under
official third-party grading on the held-out private set, in one submission,
verifiably free of per-instance priors. The public 95.33% is the audition, not
the deliverable: the deliverable is the artifact plus its reproducible
attestation trail. A change is admissible only if it stays general
(instance-blind), leaks no held-out signal, wins only on official-test
verdicts, keeps an honest denominator, and is reproducible. Full predicate and
the public→private strategy: [`PREREGISTRATION.md`](PREREGISTRATION.md) §0–§1,
[`PRO_PORT.md`](PRO_PORT.md).

## Layout

- `skills/{recon,craft,audit}/skill.md` — the pipeline skills (live copies;
  dual-licensed, see `skills/LICENSE.md`).
- `driver/` — orchestration, sharding, provisioning, grading. Mostly
  benchmark-agnostic; the Pro-specific constants are the adapter surface
  (`PRO_PORT.md` lists the touchpoints).
- `runs/scored/` — the frozen-tag scored-run trail: `run.jsonl` (the ledger),
  `artifacts/` (per-box captured diffs + agent trajectories),
  `auth_strips.jsonl` (the `PROVIDER_CRED_REJECT` recovery audit trail).
- `tasks/`, `iso/`, `scratch/`, `hypotheses/` — task generation, isolation
  notes, ephemeral pads, dev hypotheses.
- `./score` — prints the live tally from `run.jsonl` (last-wins dedupe by
  instance id).

## Reproducibility caveat — plan for provider flakiness

A multi-hour Claude-backed fleet will typically encounter at least one
credential-rejection wave per campaign: boxes start returning verbatim `Failed
to authenticate. API Error: 401 Invalid authentication credentials` with 0-byte
patches, recurring across instances on the same box, when an OAuth token pushed
at provisioning is rotated server-side after the fact. This run hit three. They
are recoverable (halt → re-push fresh creds → restart → strip the wave → re-
dispatch) and the prereg enumerates the fault class with four invariants so a
recovery can't double as a free re-roll
([`PREREGISTRATION.md`](PREREGISTRATION.md) §14). A reproducer who doesn't plan
for it will see the score depressed by every missed wave it reads as losses.
The full incident trail and the load pattern that drives it are in
[`RUN_NOTES.md`](RUN_NOTES.md).

## License

Repo: CC BY-SA-NS ([`LICENSE.md`](LICENSE.md)). Skills (`skills/`):
dual-licensed CC BY-SA-NS **or** GPL-3.0, recipient's choice
([`skills/LICENSE.md`](skills/LICENSE.md)).
