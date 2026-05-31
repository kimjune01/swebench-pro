# Sweep pipeline meta hypothesis graphs (imported artifact)

These two files are **verbatim copies** from the `sweep` PR-contribution
pipeline — the original harness that runs on live open-source repos. The
SWE-bench methodeutic harness in this repo is an **adaptation of it**, not a
separate project: same typed-inquiry machinery, retargeted from "open a
mergeable PR against a real maintainer" to "resolve a benchmark instance under a
preregistered grader." These graphs are therefore the direct ancestor's record,
reproduced here as evidence that the harness's hypothesis-graph substrate is
**reflexive**: the same machinery that diagnoses a bug in a target repo also
runs with the harness *itself* as the system-under-test. They are what that
looks like when it is maintained as a standing artifact rather than spun up per
incident.

## Source

Imported from `kimjune01/sweep` at commit `ef13a31` (2026-05-18), the last
commit to touch either file.

- `HYPOTHESIS_GRAPH.md` — https://github.com/kimjune01/sweep/blob/ef13a31/HYPOTHESIS_GRAPH.md
- `OPS_HYGRAPH.md` — https://github.com/kimjune01/sweep/blob/ef13a31/OPS_HYGRAPH.md

The copies are byte-identical to the originals; no edits were made. The
originals remain the canonical, live versions and continue to evolve in the
sweep repo.

## What the two graphs are

They split along the same world-model / self-model line the harness draws
between a bug-in-the-repo and a bug-in-its-own-pipeline:

- **`HYPOTHESIS_GRAPH.md` — the PR-science graph.** Hypotheses about the
  *world*: merge rates, issue-first vs repo-first candidate quality, whether
  prior standing gates large repos, whether drip pacing prevents ban cascades,
  whether AI-friendly repos merge more or just attract more competing PRs. Unit
  of inquiry is a PR outcome; a hypothesis is falsified when the merge rate
  diverges from prediction.

- **`OPS_HYGRAPH.md` — the ops/substrate graph.** Hypotheses about *running
  the pipeline ourselves*: activity-owned observability beating skill-emitted
  events, watchdog auto-recovery needing to run independent of the workflow it
  governs, interface accounting, routing actors. Unit of inquiry is a pipeline
  health signal; a hypothesis is falsified when the substrate fails or silently
  drops work. `O`-prefixed identifiers keep cross-file references unambiguous.

`HYPOTHESIS_GRAPH.retros.md` (the dated append-only trail in the sweep repo) is
not copied here; it is the narrative log behind the live PR-science graph and
is not load-bearing for the reflexivity point.

## Why it lives in this repo

The SWE-bench adaptation does not maintain its own standing meta-graph, and the
absence is a signal rather than a gap. A meta-graph accumulates wherever the
*tuning loop* runs — where hypotheses about the harness's own behavior get
posed, tested against outcomes, and folded back into the pipeline. That loop ran
on **real-world open-source issues and PRs**, against live maintainers and merge
decisions, which is exactly what `HYPOTHESIS_GRAPH.md` and `OPS_HYGRAPH.md`
record. It never ran on the benchmark. The harness was tuned on OSS and then
*applied* to SWE-bench Pro under a frozen preregistration — so the bench side
shows only per-incident, self-directed inquiry (e.g. the
`swebench-pro-flash-composer__no-patch-produced` and
`deepswe-run__phase-a-unresolved` graphs in `repo-hypotheses/`), never a
standing meta-graph, because there was no tuning loop on the bench to grow one.

This is the no-overfit story stated structurally: had the harness been iterated
against SWE-bench, a bench-side hygraph would exist as the residue of that
iteration. There isn't one. The development pressure lived entirely on OSS,
which is why these two files are cited from the parent harness rather than
reconstructed here.
