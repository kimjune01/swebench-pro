# SWE-bench Pro defects observed in our runs

> **⚠ STALE — revision pending.** Defect 1 below ("silent grader deadlock") is largely a
> misdiagnosis. The "deadlock" symptom (low CPU + idle `pro_grade_*/` dir) turned out to be our
> own watchdog reading the wrong file — host-side `pro_grade_*/` mtime only updates at verdict
> time, while the actual grader runs inside the container writing `/workspace/stdout.log`.
> A working slow grader looked deadlocked to the watchdog for the whole test duration.
>
> What's almost certainly still true: the official grader has **no internal timeout**, so anything
> that genuinely hangs would sit forever. But "pervasive silent deadlock" is the wrong framing.
>
> See `WORKLOG.md` entry **"2026-05-29 (even later)"** for the corrected understanding and
> `~/Documents/sweep/repo-hypotheses/swebench-pro__grader-hang.md` for the investigation trail.
> Will revise this doc once the morning's 3 retried-after-watchdog-kill instances return — their
> outcomes tell us whether the originals were real LOSSes or our-watchdog artifacts.
>
> **Do NOT publish or share externally until revised.** The current framing would be unfair to a
> bench team whose actual rigor we respect.

Audit-facing: things the bench does that aren't documented in the SWE-bench Pro repo
or the official grader, that anyone reproducing this work will hit. None of these
are our defects; all are upstream-Pro behaviors we work around at the runner layer.

If you're reproducing and seeing unexplained LOSSes, slow runs, or hung graders,
start here.

## Defect 1 — Official grader (`swe_bench_pro_eval.py`) deadlocks silently on heavy suites

**Observed:** 2026-05-29, multiple NodeBB instances on 8 boxes.

**Symptom:**
- Docker container running the grader stays alive for hours
- CPU usage ~0.4%, RAM ~40MB (essentially idle)
- Process state `S`, `wchan=futex_` (sleeping on a futex)
- Grade output directory mtime stops being updated
- No log output, no exception, no error code
- Eventually hits the coordinator's `--instance-ceiling` (default 36000s = 10h) and box-faults

**Root cause (unverified, our guess):** The Pro grader has no internal timeout. NodeBB's
test suite involves real DB/HTTP setup that can leak hung Node processes or open DB
connections. When that happens inside the grader's docker container, the grader's main
process waits indefinitely on a futex (likely a child-process join) and never reports back.

**Implications for reproduction:**
- Without mitigation, heavy-suite instances will silently consume your 36000s ceiling
  before the worker box-faults and requeues. Multiple such hangs in parallel can wedge
  most of your fleet for hours.
- These hangs produce no useful diagnostic. Logs are clean, container is "running."

**Mitigation (we built):** `driver/grader_watchdog.sh` — SSHes to each box on a 5-min
cadence, force-kills any docker container with:
- uptime > 60min AND
- CPU% < 1 AND
- grade output dir mtime idle > 30min

When killed, `pro_run` returns "not resolved" and the instance lands in the ledger as
LOSS. See [Defect 3](#defect-3) for the integrity caveat.

## Defect 2 — Grader leaks containers after exit

**Observed:** 2026-05-29, same session as Defect 1.

**Symptom:**
- `docker ps` on a box shows multiple grader-shaped containers
- Only one is the active grader; the rest are orphans from prior instance runs
- Orphans persist for hours; one observed at 73-minute uptime
- Each orphan retains its `runs/dev/pro_grade_<iid>/` output directory

**Root cause (unverified):** The Pro grader (or its docker invocation) does not
`docker rm` on exit. After each `pro_run` invocation completes, the container stops but
isn't removed from `docker ps`. Stale containers accumulate one per completed instance.

**Implications for reproduction:**
- Disk usage on each box grows monotonically.
- More serious: **the orphans' grade output dirs are still on disk, with their stale
  mtimes,** which poisons any watchdog logic that uses "most recent `pro_grade_*/` dir"
  as a proxy for "what the active grader is doing." We hit this — see Defect 3.

**Mitigation (we built):** `driver/grader_watchdog.sh` now reaps orphans each poll —
keeps the newest container per box, `docker kill`s the rest. `pro_run` is serial per
box, so anything older than the newest is necessarily leaked.

## Defect 3 — Orphan-poisoned watchdog perception (interaction of 1 and 2)

**Observed:** 2026-05-29, after Defect 2 was identified.

**Symptom:**
- `box_health.sh` showed `idle_min=22-23m` on active containers across the fleet
- Looked like all boxes were hung
- Actually: the active graders were writing fresh output the whole time; the watchdog
  was reading mtime off the *most recent* `pro_grade_*/` dir, which was a leaked one
  from a prior run, hours stale

**Implication:** Without orphan reap, an active grader that runs >60min crosses the
watchdog's age threshold; if orphan dirs are present, the watchdog sees stale mtime and
trips the idle threshold too; the live grader gets killed mid-grade. Adds a spurious
LOSS *and* destroys legitimate work. We caught it before this fired; could have happened
any time.

**Mitigation:** Defect 2's mitigation (orphan reap) eliminates the poisoned-perception
class entirely. With only one container per box, `ls -dt pro_grade_*/` reads the right
dir.

## Defect 4 — `not resolved` LOSS is indistinguishable from grader-hang artifact

**Observed:** ongoing.

**Symptom:** The ledger's `detail` field uses `"not resolved"` for both:
- A real LOSS (agent produced an incorrect patch; grader correctly reported it doesn't
  pass the hidden test).
- A watchdog-killed grader hang (agent's patch may have been correct; grader never returned
  a verdict; `docker kill` made the eval process exit non-zero).

You cannot tell them apart from the ledger alone.

**Mitigation (we built):**
- `runs/scored/grader_kills.jsonl` — structured kill log; one JSON line per watchdog kill
  with `{ts, box, cid, container, uptime_min}`.
- `driver/retry_grader_kills.sh` — cross-references the kill log with `run.jsonl`,
  strips any LOSS recorded within 60s of a kill on the same box, backs up the ledger.
  The stripped instances re-enter the queue on next coordinator startup.
- Policy: if the retry fails again, verify with gold-passes-verifier (oracle mode) before
  marking KNOWN_BAD. A LOSS that fails twice but the gold passes is a real failure; one
  where both fail is upstream defect.

## Integrity implications

The grader bugs all bias the same direction: **inflated LOSS count, deflated WIN count.**

- A WIN is solid: the grader returned "resolved." Grader bugs in other dimensions don't
  forge a pass.
- A LOSS may be real OR a bench artifact. We can disambiguate via re-grade.

So any reported number from a non-trivial Pro run is **conservative** (lower bound on true
capability) unless the reporter has receipts to identify the bench artifacts. We keep
those receipts: per-instance patches + trajectories + the grader-kills audit trail
(`runs/scored/artifacts/<coord>/patches/` + `grader_kills.jsonl`).

For audit:

```bash
# Re-grade any LOSS independently of the runtime watchdog:
#   1. Spin up a fresh box
#   2. Apply runs/scored/artifacts/<coord>/patches/pro_patch_<iid>.diff
#   3. Run swe_bench_pro_eval.py with no kill timeout
#   4. Outcome: PASS → bench artifact; FAIL → real LOSS; HANG → check with gold
```

A `driver/re_grade.sh` helper is planned for the final reporting pass but not yet built.

## See also

- [`docs/retros/2026-05-29-operator-infra-v1.md`](retros/2026-05-29-operator-infra-v1.md) —
  the operator-infra journey that surfaced these defects
- [`WORKLOG.md`](../WORKLOG.md) — entries on 2026-05-29 with the original symptoms
- [`driver/grader_watchdog.sh`](../driver/grader_watchdog.sh) — the running mitigation
- [`driver/box_health.sh`](../driver/box_health.sh) — operator query for current fleet state
