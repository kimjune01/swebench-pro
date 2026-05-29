# SWE-bench Pro runtime defects (field notes)

Audit-facing: defects observed in our runs that aren't documented in the official Pro repo or
grader, with the runner-side mitigations we built. None of these are our defects; all are
upstream-Pro behaviors we work around at the runner layer. The bench team is doing serious
benchmark research and this doc is product-feedback shaped, not critique.

If you're reproducing and seeing unexplained LOSSes, slow runs, or wedged graders, start here.

## Defect — `redis-server --daemonize yes` flake in NodeBB grader

**Observed:** 2026-05-29, 4 of 4 boxes simultaneously stuck on NodeBB instances.

**Symptom:**
- Docker container alive, CPU ~0.4%
- Inside container: bash → bash run_script.sh → sleep loop
- `/workspace/stdout.log` is being written every second — but every new line is identical:
  ```
  Waiting for Redis to start...
  Waiting for Redis to start...
  ...
  ```
- Container would run forever until the coordinator's instance-ceiling (default 36000s = 10h) fires

**Root cause:** the grader's `prepare_test_environment` script does:
```bash
redis-server --daemonize yes --protected-mode no --appendonly yes
while ! redis-cli ping; do
  echo "Waiting for Redis to start..."
  sleep 1
done
```
Sometimes the `daemonize yes` invocation silently fails to fork — the server doesn't start, exits zero, no error to stderr. The script then loops forever pinging nothing.

**Verification:** running `redis-server` manually in foreground inside the same container starts it instantly and `redis-cli ping` returns PONG. So Redis CAN run; the bench's daemonize call is flaky. (Why daemonize fails specifically is unverified — suspect AOF state, but not yet diagnosed.)

**Mitigation (we built):** `driver/grader_watchdog.sh` checks the tail of `/workspace/stdout.log` each poll; if ≥5 of the last 10 lines contain "Waiting for Redis to start", runs `docker exec -d <cid> redis-server --daemonize yes --protected-mode no --port 6379` to kick-start it. Verified live: containers immediately switch from spam to real test output once Redis comes up.

**Disclosure stance:** the kick-start is operator-layer mitigation — it helps the bench's intended setup state actually obtain. The bench grades "does the patch fix the bug under working infra"; our intervention only ensures the infra works. We do not modify pro_run, the grader, the tests, or the verdict. Score outputs carry a `*` footnote pointing here.

## Defect — grader leaks containers after exit

**Observed:** 2026-05-29.

**Symptom:** `docker ps` shows multiple grader-shaped containers after pro_run has finished its
serial-per-box loop. pro_run is serial, so anything older than the newest container is necessarily
leaked. Observed 3-4 stale containers per box after several hours of runs.

**Implications:** disk grows monotonically; more importantly, the orphans' `pro_grade_<iid>/`
directories persist on disk and can mislead any watchdog that uses "most recent grade dir" as a
proxy for current activity (we hit this — see the worklog "later" entry from 2026-05-29).

**Mitigation:** `driver/grader_watchdog.sh` reaps orphans each poll — keeps newest container per
box, `docker kill`s the rest. Logs `REAP_ORPHAN`.

## Defect — `not resolved` LOSS is indistinguishable from grader-hang artifact

**Observed:** ongoing.

**Symptom:** when our watchdog kills a wedged container (real hang or redis flake), pro_run records
the failed eval as `"not resolved"` — the same `detail` field a genuinely-failed test gets. The
ledger can't tell them apart on its own.

**Mitigation:**
- `runs/scored/grader_kills.jsonl` — structured kill log; one JSON line per watchdog kill.
- `driver/retry_grader_kills.sh` — cross-references the kill log with the ledger, strips matching
  LOSSes, lets the queue re-pick them on next coordinator startup.
- Policy: if the retry fails twice, run gold-passes-verifier (oracle mode) to decide between real
  LOSS and platform-bug KNOWN_BAD. The latter is reserved for cases where even the reference
  solution fails — not for cases where our patch happened to fail twice.

## What we initially mistook for a defect

For honesty: the first writeup of this doc included a "silent grader deadlock (futex hang)" as
Defect 1. That framing was largely wrong. Investigation later in the day found:

1. Our watchdog read `runs/dev/pro_grade_*/` mtime on the HOST as the idle signal, but that dir
   only updates when pro_run writes the verdict back. Active graders looked idle to the watchdog
   for the entire test duration.
2. Containers that we marked KILL with "0.4% CPU, idle 3h" were largely just slow-but-progressing
   NodeBB graders that the watchdog was misreading.

The corrected watchdog reads `/workspace/stdout.log` mtime inside the container, which is the real
progress signal. The narrow truth that survives: the official grader has no internal timeout, so a
*genuinely* hung process sits forever. But "silent futex deadlock pervasive across NodeBB" was our
own measurement artifact, not a real Pro defect. We've kept the morning's spurious-kill audit trail
in `grader_kills.jsonl` to retry those instances honestly.

## Integrity direction

All defects above bias the SAME direction: **inflated LOSS count, deflated WIN count.**
- A WIN is solid: the grader returned "resolved." Grader bugs in other dimensions don't forge a pass.
- A LOSS may be real OR a bench-side artifact our runner couldn't disambiguate.

Any reported number from a non-trivial Pro run is **conservative** (lower bound on true capability)
unless the reporter has receipts to identify the bench artifacts. We keep those receipts:
- Per-instance patches and trajectories: `runs/scored/artifacts/<coord>/`
- Structured grader-kill audit: `runs/scored/grader_kills.jsonl`
- Box heartbeat trace: `runs/scored/box_heartbeat.jsonl`
- This doc + the worklog for the prose

For any specific LOSS, the re-grade recipe:
```bash
# 1. Spin up a fresh box
# 2. Apply runs/scored/artifacts/<coord>/patches/pro_patch_<iid>.diff
# 3. Run swe_bench_pro_eval.py with the new watchdog mitigations available
# 4. Outcome: PASS → spurious LOSS; FAIL → real LOSS; HANG → run with gold to check for KNOWN_BAD
```

A `driver/re_grade.sh` helper is planned for the final reporting pass.

## See also

- `WORKLOG.md` — chronological narrative; "2026-05-29 (latest)" entry is the §14-style amendment for the redis-wedge mitigation
- `docs/retros/2026-05-29-operator-infra-v1.md` — the operator-infra journey that surfaced these defects
- `driver/grader_watchdog.sh` — running mitigation
- `driver/box_health.sh` — operator query for current fleet state
