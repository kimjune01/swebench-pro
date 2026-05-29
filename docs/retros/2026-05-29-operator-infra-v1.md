# Retro: operator infra v1 — what we built, what hurt, what's next

**Date:** 2026-05-29
**Subject:** the bash + AWS-CLI orchestration layer above `coordinator.py` (the inner harness)
**Audience:** future me + anyone trying to reproduce the run

## The path we walked, in one session

Started the day with a coordinator dispatching 4 boxes. Ended at 4 boxes again. In between, we:

- Provisioned an additional 4 (8 total)
- Drained 4 (back to 4)
- Force-terminated 6 (down to 2) under quota emergency
- Re-provisioned 2 (back to 4)

Plus killed and restarted the coordinator at least four times, terminated and re-provisioned at least 10 EC2 instances, and added three watchdog-class processes that didn't exist at session start. Every shape change taught us something the previous shape couldn't.

## What we built (newest last)

1. **`coordinator_watchdog.sh`** — restart-on-death for the Python coordinator. Built after a silent coordinator-death incident (no traceback, no exit log, EC2 boxes kept running while local orchestration vanished). Polls `pgrep` every 30s.

2. **`drain_boxes.sh`** — let named boxes finish their current run, terminate, whack any `setup_box` reprovision retries, exit clean. Built when we wanted to halve 8→4 without losing in-flight work.

3. **`grader_watchdog.sh`** — SSH into each box, find docker containers running >60min with <1% CPU and grade-output mtime stale >30min, force-kill them. Built after discovering the official Pro grader (third-party, in docker) deadlocks silently in `futex_wait` on heavy NodeBB suites. Was the single highest-leverage piece this session: rescued 3 hung boxes within 30 seconds of going live.

4. **`grader_kills.jsonl` + `retry_grader_kills.sh`** — structured audit trail for watchdog kills + a script to strip the resulting spurious LOSSes from the ledger so the queue re-picks them on next coordinator startup. Policy: if the retry fails too, it's a real LOSS (or KNOWN_BAD if repeating). Built after realizing watchdog kills produce LOSS entries indistinguishable from real failures.

5. **`scale_fleet.sh` + `fleet_reconciler.sh` (drafted, not deployed)** — declarative single-knob scaling via a desired-state file. Codex review found 12 issues (5 High); deferred to v2.

Each was built reactively — under pressure, when the previous shape was actively burning tokens or wall-clock. None was prebuilt to spec.

## What hurt

- **Silent failures.** The coordinator died once without a traceback. The grader deadlocked without an error. Both were detected by absence (no log activity, no ledger entries) rather than presence (no exception). Defensive infra needs to make absence loud.

- **Two controllers fighting over the same resource.** Dual coordinators with the same `eligible.txt` independently built identical heavy-first queues and dispatched the same instances in parallel. The bug was subtle (no error, just doubled token burn). Generalized rule: never run two control loops against the same state without a claim mechanism.

- **State spread across `/tmp` files, in-memory queues, AWS, and one local `run.jsonl`.** Each layer disagreed about what was true. `count_actual` was just "how many env files are in `/tmp`" — not actual fleet truth.

- **Ramping is lossy by construction.** Killing the coordinator kills SSH sessions which kill remote `pro_run` processes. Every ramp-up costs one round of in-flight runs (~10–30 min × N boxes). We did this enough times today that the loss showed up in throughput.

- **Watchmen with no judges.** Each watchdog we built was itself unwatched. If the grader watchdog had silently died, we wouldn't have known. The user asked "who watches the watchmen" and the honest answer was "nobody, ultimately."

## What worked

- **Audit trails as receipts.** The grader watchdog's structured kill log let us identify spurious LOSSes after the fact and stage a retry. Without it, those LOSSes would have permanently corrupted the score.

- **Drain semantics via existing primitives.** `drain_boxes.sh` whacks `setup_box` reprovision retries until the worker exits gracefully — uses only the inner harness's existing fault-handling path. No inner-harness modification needed.

- **Quota relief by killing the coordinator first.** Within seconds of `pkill -f coordinator.py`, 8 concurrent Claude streams stopped. EC2 cleanup is bookkeeping; quota relief is the SSH session death.

- **Codex review caught the design before it shipped.** The first cut of `fleet_reconciler.sh` had a torn-read race, a silent-AWS-failure bug, a `pkill -f` that would shoot any coordinator process, and 9 others. Sending it for review before deploying was much cheaper than deploying and debugging.

## Realization: we reinvented kubernetes (in miniature)

Each layer we added moved one rung up the intelligence ladder:

| Layer | Role added (Natural Framework) |
|---|---|
| Coordinator | Perceive (ledger) + Transmit (dispatch) |
| Coordinator watchdog | Filter (is coord alive?) + Transmit (restart) |
| Grader watchdog | Perceive (docker state) + Filter (3-threshold) + Transmit (docker kill) |
| Drain | Attend (which to retire) + Transmit (terminate) |
| Reconciler (drafted) | All four, with desired state as externalized Cache |

The lesson isn't "k8s was right all along." The lesson is **mechanism alone doesn't compose; you need judgment in every control loop**. K8s is the industrial solution to this problem. Our bash-and-SSH stack is the artisanal one. Both are answers to the same forcing function.

## Where Pulumi fits (v2 direction)

The bash + AWS-CLI surface is right at the seam where IaC pays off. Specifically:

**Pulumi (Go) owns EC2 + credentials:**
- Atomic state transitions — replaces "delete env file unconditionally after best-effort terminate"
- Authoritative state — `pulumi stack output --json` replaces `ls /tmp/coord*.env`
- Sequenced changes — `pulumi up` serializes scale-up vs drain
- Provider-level retry + drift detection — replaces the AUTH_ASSERT-escape-bug class of failure

**Bash + Python keep owning processes + judgment:**
- The coordinator process (Python on Mac, opaque to Pulumi)
- Grader-hang detection (must SSH in, can't be declared)
- The Claude subscription quota dance (state lives in Anthropic, not in our stack)

**Sketch:**

```
pulumi/
  Pulumi.yaml
  Pulumi.production.yaml      # config: fleet_size, region, instance_type
  main.go
  fleet.go                    # ComponentResource: N×EC2 + SG + key + provisioner
  outputs.go                  # exports: ips, iids per coord
scripts/
  scale_fleet.sh              # → pulumi config set fleet:size <N> && pulumi up
  coord_health.sh             # consumes pulumi outputs, no more /tmp/coord*.env
```

Scaling becomes `pulumi config set fleet:size 4 && pulumi up`. Drain stays as a separate process (it's judgment, not provisioning). Most of codex's 12 findings against the bash reconciler disappear because Pulumi solves them at the infra layer.

## Lessons compressed (for memory)

1. **Watchmen are intelligence-shaped, not mechanism-shaped.** Every layer you add for resilience must Perceive, Filter, Attend, and Transmit. Pure mechanism doesn't compose.

2. **Audit trails are cheap when added before they're needed.** The grader kill log was added at watchdog construction; without it, we couldn't have distinguished spurious LOSSes from real ones.

3. **Never run two control loops over the same state without a claim mechanism.** Lesson from the dual-coordinator duplicate-dispatch incident.

4. **Make silence loud.** Silent coordinator death and silent grader deadlock both burned hours before detection. Heartbeat logs at every layer; alert on absence, not just on exceptions.

5. **Codex review before deploy is cheaper than deploy then debug.** The reconciler had 12 real issues before its first run.

6. **Quota is a sliding window, not a wall.** Operating against a hard reset is the wrong mental model; operate against the curve. Throttle to 4 instead of emergency-to-2 when you can.

7. **The right division of substrate matters.** IaC for AWS resources, code for judgment, scripts for glue. Don't force one substrate to do all three jobs.

8. **Audit posture is audience-calibrated.** Same evidence, different framing depending on who the
   reader is. For benches whose published rigor warrants pushback (DeepSWE — gold-passes-verifier
   was never run), punchy audit posture is earned. For benches built by people doing serious
   benchmark research (Pro), the same findings should land as **field notes** — closer to product
   feedback than critique: "we hit these edge cases at scale, here's the trace, here's our
   workaround." The `docs/bench-defects.md` doc is already field-notes-shaped on purpose; any
   public Pro writeup should match.
