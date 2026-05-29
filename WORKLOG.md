# swebench-pro worklog — `prereg-pro-v1`

Newest first. This is the **scored-run trail** for the frozen artifact `prereg-pro-v1`. Pre-freeze
development history is in [`WORKLOG_PREFREEZE.md`](WORKLOG_PREFREEZE.md). Per §13, each scored tag
gets its own worklog; this one carries only `v1`'s run.

## 2026-05-29 (later) — Pro grader leaks containers; orphans poisoned watchdog perception

Added per-box heartbeat (`runs/scored/box_heartbeat.jsonl`) + `box_health.sh` operator query after
several hours of asking "is it healthy" and getting only ledger-level information. First query
revealed a class of finding the snapshot-based grader_watchdog had been missing:

**The official Pro grader leaves containers running after the grader process exits.** Observed
coord1 with 3 grader containers (uptime 6m, 72m, 73m), coord2 with 4 (uptime 22m, 71m, 72m, 72m).
`pro_run` is serial per box, so anything older than the newest container is leaked from a prior
instance run. Across 4 boxes, 5 orphan containers persisted. Each one had been idle for hours,
sitting at ~0.4% CPU.

**The orphans poisoned the grader_watchdog's own perception.** The watchdog uses
`ls -dt ~/swebench-pro/runs/dev/pro_grade_*/` to find the latest grade-output dir, then checks its
mtime to compute `idle_min`. Orphan containers left their grade dirs around (each a `pro_grade_*`
sibling), and those stale dirs were the most-recently-modified hours ago — so the watchdog saw
`idle_min=22m` for the active container too. Live graders were making progress; the watchdog just
couldn't tell. None had crossed the 30m idle threshold yet, but a stale orphan would have triggered
the kill on an *active* grader within minutes.

**Remediation (immediate):**
- Extended `grader_watchdog.sh` to reap orphan containers each poll: keep newest per box (docker ps
  is newest-first by default), `docker kill` the rest, log `REAP_ORPHAN cid=... up=Xm`.
- Manually killed the 5 existing orphans across coord1-4 before the next poll cycle.
- Verified: `idle_min` on the active containers immediately dropped from 22-23m to 0m once the
  stale grade dirs were gone (active graders had been working the whole time).

**Why this matters beyond housekeeping:** the watchdog's filter (3-threshold gate) had a latent
false-positive class we didn't know about. With orphan dirs present, any active grader that ran
>60 minutes would have crossed all three thresholds and been killed mid-grade — adding a spurious
LOSS to the ledger AND killing legitimate work. We dodged it this morning by luck (orphans hadn't
crossed the 30m idle threshold yet relative to the active dirs). Codex's #4 finding on the
unwired reconciler ("count_actual is just env files, not actual fleet state") generalizes: any
filter that depends on derived state can be silently poisoned by stale siblings. Always sanity-check
the input signal before trusting the gate.

**Audit-implication parallel:** another Pro-grader oddity to document alongside the futex-hang
finding. The bench ships containers that leak resources; that's their bug, ours to work around.

## 2026-05-29 — official Pro grader deadlocks silently; force-halve via drain script

**Surprise finding.** The Pro `swe_bench_pro_eval.py` grader (third-party, in docker) hangs on
heavy suites (NodeBB-shaped instances) in `futex_wait` with **0.4% CPU, 41MB RAM, no log activity
for 3h+**. No timeout, no error, no progress signal — same `ship-without-sanity-checks` pattern
we critiqued DeepSWE for, except here it's the upstream Pro grader. Documented as a known
craft-hang pattern (`project_swebench_craft_hang.md`), now confirmed on the grader path too.

Caught while ramping down to relieve 5-hour subscription quota pressure. SSH'd into all 8 boxes,
found 7/8 stuck inside the docker grader, agent work long-since complete. Container `xenodochial_pike`
on coord3: up 3h, 0.40% CPU, output dir mtime frozen at container start. Process state `S` with
`wchan=futex_`. Identical pattern on coord4-6, 8 (2-3h+) and coord2 (49m, earlier in the hang cycle).
Only coord1 was actually working (claude+codex spawning).

**Operator infra built (does NOT touch the inner harness):**
- **`driver/coordinator_watchdog.sh`** — polls for `coordinator.py` every 30s; on death, restarts
  with `--skip-setup --boxes ${WATCHDOG_BOXES:-8}` against existing `/tmp/coord*.env`. Belt-and-
  suspenders after a silent coordinator death earlier in the day (no traceback, EC2 boxes kept
  running; we mistook a slow heartbeat for a crash). Logs to `runs/scored/watchdog.log`.
- **`driver/drain_boxes.sh`** — let a named subset of boxes finish their current run, then
  permanently retire them. Watches the ledger; on each box's next completion, terminates its EC2
  instance + deletes `/tmp/<name>.env`. Whacks any reprovisioned env from `setup_box`'s retry path
  until the worker's restart_max exhausts and it retires gracefully. Bash 3.2-compatible (sentinel
  files instead of associative arrays).

**Halving 8 → 4.** Watchdog restarted with `WATCHDOG_BOXES=4` (so any future restart only brings
back coord1-4). Drain armed on coord5-8. Drain initially waited for a normal completion that
never came (graders hung). After SSHing in and confirming the deadlock pattern, force-terminated
coord5-8 EC2 boxes directly + touched sentinel files so the drain script's Phase 2 whacked the
inevitable `setup_box` reprovision attempts. Drain reached "all targets retired" within seconds.

**Note on what we lost:** ~4 in-flight NodeBB instances that had completed the agent phase hours
ago but were stuck in the grader. Patches and trajectories were already synced to local by the
artifact puller (last cycle 09:08, captured all coord5-8 work). The verdicts are what's missing;
those instances stay in the queue and will be re-attempted later (possibly on the same grader bug,
which would suggest excluding NodeBB from the eligible set as a §6.1-style platform-bug exclusion).

**Audit implication (separate from §14).** The post-shipping critique of DeepSWE leaned on
"publish runs so others can check." This run just produced a parallel finding the bench itself
hasn't disclosed: their official grader deadlocks silently. That's an upstream-Pro defect, not
ours, but our published artifacts will surface it for anyone who looks. Worth a follow-up
audit-style post once we have more reproductions.

## 2026-05-27 (later still) — publish full run data: artifact puller + prereg §14 amendment

Sharpened by auditing a contemporaneous benchmark (DeepSWE/Datacurve) that ships tasks + harness but
**no run data** across its whole GitHub org (verified: 6 repos, the only "trajectory" hits are viewer
UI + Storybook fixtures) — its leaderboard and harness-neutrality pilot have no published numbers
behind them. Engineer's report wearing science's clothes. The line is the **burden-of-proof direction**:
publish the runs and invite refutation, or publish the result and ask for trust.

We were doing a milder version of the same sin: the coordinator checkpointed **verdicts only**;
trajectories + captured diffs died on box teardown (lost 3× this session). Closed it:
- **`driver/pull_artifacts.sh`** — read-only rsync daemon, pulls per-instance artifacts off the live
  boxes on a 600s cadence (captured diffs `runs/dev/pro_patch_*.diff`, Claude recon/craft/audit
  trajectories `~/.claude/projects/`, codex challenger sessions `~/.codex/sessions/`, per-box ledger)
  into `runs/scored/artifacts/<box>/`. Re-reads `/tmp/coord*.env` each cycle, so it follows
  reprovisioned boxes. First clean cycle pulled **33 diffs + 111 claude + 113 codex trajectories
  (36M)**. Running as bg task; zero disruption to the live run (read-only on the box side).
- **Prereg §14 (post-freeze amendment)** — transparency-only (can't bend a verdict or the denominator),
  so no §3 restart. Operationalizes §10: a run isn't a headline until its per-instance trajectories +
  diffs are published, not merely its ledger. Binds v1 and all future versions.
- **Structural TODO:** fold the pull into the coordinator's checkpoint so future runs capture full
  provenance by default instead of via a side daemon.

## 2026-05-27 (later still) — switch to paid API for a time-boxed window (Sonnet on key, codex on sub)

**Decision:** rather than wait out the Max quota grind, the operator dropped a **short-lived
`ANTHROPIC_API_KEY`** (expires ~2026-05-29 03:00, then revert to subscription, same 4-box pace). Plan:
run the scored set on **paid Sonnet + codex-on-sub** until the window closes. Key stored 600 at
`~/.swebench-pro/anthropic.key` (outside repo); validated live (`claude-sonnet-4-5-20250929`). Operator
confirmed the key is short-lived so transcript exposure is acceptable; rotate-after not required.

**Auth-source change is NOT an artifact change → stays v1**, byte-identical (PROCEDURE "Token access"):
auth source isn't part of the frozen artifact, the headline already discloses model+scaffold.

**Plumbing built (operator, not artifact):** `coordinator.py` + `run_fleet.sh` gained `AUTH_MODE=api`
alongside subscription — pushes a 600 key file (not OAuth), `run_instance` exports `ANTHROPIC_API_KEY`
and leaves `CLAUDE_SUBSCRIPTION` unset so `plan_env()` honors the key; codex sub auth untouched.
Subscription path byte-identical (assert refactored into an injected snippet; both modes
simulation-verified to render valid remote bash). The dynamic coordinator's fault-tolerance is retained
(vs the fragile static-shard path) for the unattended window. Committed.

**Canary (DONE — PASS):** 1 box, `AUTH_MODE=api`, 3 quota-paused **flipt** instances → dev ledger
(`runs/dev/canary_api.jsonl`). Plumbing works end-to-end (api provision, key billing, codex-on-sub, full
pipeline, clean teardown). **Confirms the quota-casualty diagnosis:** under healthy tokens these ran
**full-length 885–1378s** (vs 196–374s fast-deaths at the wall) → **2 WIN / 1 LOSS**. flipt-0b119520
flipped LOSS@268s → **WIN@885s**; flipt-05d7234f ran 1378s and genuinely lost. So re-running cleanly
separates quota-casualties from real losses — the reclassification was correct.
**Measured cost: USD 6.21 / 3 = ~$2.07/instance (flipt = light end; ~900–1400s).** Heavy repos cost
more, so blended is higher. Cost read from the Console (regular key can't query the cost API — needs
admin key). Box self-terminated on drain → session logs lost again (3rd teardown artifact-loss; retro:
pull logs before teardown). Canary verdicts stay on the dev ledger; the scored run re-runs those 3.

**Bulk run launched:** 4 boxes, `AUTH_MODE=api`, full eligible → scored ledger, resuming the 680 (354
quota-paused + 326 never-attempted; 48 terminal skipped). Runs until the key window (~2026-05-29 03:00),
then revert to subscription at 4-box pace. Projection: ~250–300 instances in-window ≈ **~$1k–2.4k**.

## 2026-05-27 (later) — PAUSE: Max quota exhausted mid-run → 341 un-run, resume when budget refreshes

**Not a fault — the pre-registered `QUOTA_EXHAUSTED` PAUSE (§4).** After the auth-fix resume (~22:49Z),
the fleet ran ~5.5h and exhausted the Max token budget. The `claude` CLI hit the quota wall and died
empty (48–311s, no output across all stages) — the **same harness mis-recording** as the auth outage:
~341 quota-deaths written as `LOSS ("no verdict endogenous")` instead of PAUSE. This briefly showed an
11.2% resolve rate, which was **garbage** (mostly quota-deaths, not capability).

**Reclassified** (mechanical, output-substance criterion — `state==LOSS AND detail startswith "no
verdict (endogenous)"`): 341 rows `LOSS`→`INCOMPLETE`, `fault=QUOTA_EXHAUSTED`. Backed up →
`run.jsonl.prequota.bak`. Real-output verdicts stand.

**Follow-up investigation (the "13 same-repo fast losses" the operator flagged).** The 16 standing
real-diff LOSSes split on duration: 3 genuine full-length (teleport 2622s@00:58, protonmail
5489s@06:36 + 1015s@07:51, all *healthy regime*) vs **13 flipt at 196–374s, all 08:18–09:41Z**.
Smoking gun = a **fleet-wide temporal regime change**, not instance difficulty: flipt WINs (9) all ran
05:51–07:52 at **764–3025s**; flipt LOSSes (13) all ran 08:18–09:41 at **<400s** — 3× faster than any
flipt win, and **interspersed with the empty-deaths** inside the quota wall [08:01–11:28Z], where
**WIN=0 fleet-wide**. Mechanism: under quota throttling a *light* Go repo (flipt) can limp to a thin
shallow patch (~250s, real diff → graded LOSS) while heavy repos die fully empty. **Same
`QUOTA_EXHAUSTED` fault, thin-output variant.** Reclassified the 13 → INCOMPLETE/QUOTA by the same
verdict-independent window rule (zero in-window wins, so no cherry-picking). The 3 healthy-regime
losses **stand**.

**True state on genuine (quota-healthy) completions: 45 WIN / 3 LOSS = 93.8%** (N=48, skewed to
early-order teleport/protonmail/flipt — NOT a headline). Remaining: **354 quota-paused + 326
never-attempted = 680 to run**.

**Process gap (retro action):** `coordinator.py` checkpoints only verdicts, not captured diffs / agent
logs — so post-teardown the flipt losses were diagnosable *only* from ledger timing/metadata, not the
actual patches. The coordinator must pull per-instance diff + logs to the laptop (echoes the 2026-05-26
heavy-patch teardown loss). Until then, diagnosis leans on the timing trail.

**Resume discipline (§4 QUOTA_EXHAUSTED):** byte-identical artifact, no peek-to-decide, same tag v1,
same order. Diagnosing the fault is not peeking-to-decide (no artifact/order change). **Cannot resume
until Max quota refreshes.** Structural note: 667 heavy instances on one Max sub = a multi-quota-window
grind; cadence needs a decision (see next steps).

## 2026-05-27 — FAULT logged: auth outage (operator re-login) → 32 INCOMPLETE, re-run (§4a)

**Fault class: `AUTH_OUTAGE`** (operator-induced platform fault; verdict-independent). Corroboration:
- **Trigger:** operator got logged out of Claude and re-authenticated (`/login`) mid-run. Max OAuth
  re-login rotates the refresh token, invalidating the tokens pushed to the boxes at setup.
- **Signature:** a cliff at **04:42:39Z**. From then, 32 instances failed with `detail="no verdict
  (endogenous): … craft:[empty] audit:[empty] pilot_done:[empty]"` — **empty output across all three
  stages**, 156–297s each. Before the cliff: full-length loops (WINs 1000–2900s, one genuine 2622s
  LOSS). The agent produced *nothing*, which is the auth-failure signature, not capability.
- **Not difficulty-correlated:** WINs continued as late as 05:11 (boxes on still-valid cached tokens
  completed; only token-*refresh* attempts failed) → the failures track auth, not instance hardness.

**Classification (pre-registered, mechanical, verdict-INDEPENDENT — NOT discretion):** the trigger is
**outage-window membership** — `started_at ∈ [04:42:39Z, 05:29:14Z]` (first..last empty-output start)
→ INCOMPLETE, **regardless of verdict**. This supersedes a first-pass empty-output-only criterion: that
version would have kept in-window WINs while re-running in-window losses — an asymmetry that is exactly
the loss-laundering the §4 anti-cheat forbids. Treating the *whole* window as contaminated and
re-running **wins too** is the verdict-independent version. Re-running the 2 in-window WINs may not
reproduce them; accepting that risk is the cost that keeps the rule honest. Grounded in §13
regression-check #1 (environment-induced results are platform faults, INCOMPLETE not method LOSS).

**Out-of-window terminal verdicts STAND** (clean auth): 23 WIN + 1 LOSS (the genuine 2622s teleport
@ 00:58). Only the documented fault window is re-run.

**Action (§4a recovery, byte-identical artifact, same tag — NOT a v2 restart):**
1. Ledger backed up → `runs/scored/run.jsonl.preauthoutage.bak` (every original verdict preserved).
2. **37 in-window rows reclassified → `INCOMPLETE`** (`fault=AUTH_OUTAGE`, `orig_state`, reclass_note):
   35 LOSS (32 empty + 3 flipt `not resolved`) + **2 WIN**. `load_done()` treats INCOMPLETE as
   runnable → all 37 re-dispatch on resume.
3. Coordinator stopped; creds re-pushed to all 4 boxes from the now-valid keychain; **auth verified
   (`AUTHOK` on coord1)** before resume.

**State at fault:** 61 graded rows → **23 WIN + 1 LOSS terminal (out-of-window), 37 INCOMPLETE
(in-window, to re-run)**. Note for final tally: re-run appends fresh terminal rows; dedupe by
`instance_id` last-wins (as `load_done` does) so the INCOMPLETE rows don't double-count.

## 2026-05-26 — FROZEN: `prereg-pro-v1` cut, scored run begins

**Freeze SHA:** `99536f01fc0f3ac61e7c92a959ef5780ebe05587` (annotated tag `prereg-pro-v1` points
here). Every scored-run artifact cites this SHA.

The §13 pre-freeze gate is cleared (all four items committed): §6 defect list (eligible = 728/731),
batch/sharding driver + fleet, frozen config block, and this §13 self-update + worklog rotation. The
prereg is frozen and `WORKLOG.md` rotated — pre-freeze churn lives in `WORKLOG_PREFREEZE.md`.

**Restart motivation:** none — this is `v1`, the first scored tag. (A future `v2` would open its own
worklog with the failure class that justified the restart, per §3.)

Scored run proceeds on the 728 eligible instances under the frozen config (Sonnet 4.5 generator +
GPT-5.5 craft challenger), whole-set, fixed `tasks/run_order.txt` order, no early stop (§5).
Run/resume events, fault classifications, and the headline land below as they happen.

## 2026-05-28 14:39 PDT — AUTH_MODE switched: api → subscription

**API window closed.** Max-OAuth subscription quota replenished; switched the headline run back to
subscription billing (marginal $0).

- **API window:** 2026-05-27 (opened when subscription quota exhausted) → 2026-05-28 14:39 PDT (closed)
- **Total Sonnet-API spend:** **$654.73**
- **N at switch:** 386 terminal grades (375 WIN / 11 LOSS); 16 INCOMPLETE pending re-attempt under
  subscription
- **Per-instance API rate (observed):** ~$3 ($654.73 / 246 instances over the window, blended across
  light and heavy repos)

**Switch sequence:**
1. `SIGTERM` old coordinator (PID 46886, launched with `AUTH_MODE=api`) at 14:08 PDT
2. Drained 3 of 4 in-flight SSH orphans naturally over 30 min (PIDs 14757, 15438, 15921)
3. `SIGTERM` 1 remaining orphan (PID 16557) at 30-min ceiling; its instance routes to INCOMPLETE per §4
4. Launched new coordinator (PID 39666) with `AUTH_MODE=subscription`, same `--boxes 4 --eligible
   runs/audit/eligible.txt`
5. Startup banner verified: `AUTH_MODE=subscription -> billing: Max/$0 (per-box AUTH_ASSERT at setup)`

**Result-integrity assertion (per §4):** the switch does not change model behavior. Same Sonnet 4.5,
same prompts, same harness logic; `AUTH_MODE` only swaps the SSH-payload auth line
(`ANTHROPIC_API_KEY` export vs `CLAUDE_SUBSCRIPTION=1`). The captured diff and grader verdict are
deterministic from model output, not from billing path. Each instance is atomically one mode (auth set
per-SSH-call in `run_instance`). The 16 INCOMPLETE at switch get re-attempted under subscription and
their verdicts are equally valid per the §4 state machine.

**Subscription window active from 14:39 PDT.** Sonnet-side marginal cost zero from this point.

---

## 2026-05-28 18:50 PDT — OAuth token rotation event; 5-instance requeue

**Trigger.** During fleet expansion (coord5-8 + coord9-12 = 8 subscription boxes), the OAuth token
staged from the macOS keychain to coord6-coord12 went stale. coord5 stayed fresh by continuous use
(claude-code rotates the token in-session); coord6-12 were idle long enough for their copy to
expire. Boxes returned `API Error: 401 Invalid authentication credentials` on subsequent dispatch.

**Detection.** coord9 burned 5 instances at 74-82s each (auth-fail signature: bails within seconds
on every claude call vs. the 500-4000s legitimate runtime). All other boxes were mid-flight on
long-running instances during the window, so only coord9 victims surfaced. Fleet-wide auth probe
confirmed 7/8 boxes 401ing.

**Affected instances (all coord9, 18:41-18:46 PDT, requeued per discipline):**
- `instance_element-hq__element-web-6205c70462e0ce2e1e77afb3a70b55d0fdfe1b31-vnan` (LOSS 77s)
- `instance_element-hq__element-web-880428ab94c6ea98d3d18dcaeb17e8767adcb461-vnan` (LOSS 75s)
- `instance_element-hq__element-web-a692fe21811f88d92e8f7047fc615e4f1f986b0f-vnan` (LOSS 82s)
- `instance_element-hq__element-web-ce554276db97b9969073369fefa4950ca8e54f84-vnan` (LOSS 74s)
- `instance_navidrome__navidrome-69e0a266f48bae24a11312e9efbe495a337e4c84` (LOSS 77s)

**Remediation.**
1. Pulled fresh OAuth token from local keychain (`security find-generic-password -s
   "Claude Code-credentials"`); scp'd to all 7 stale boxes; re-tested — all 8 boxes green.
2. Backed up ledger to `runs/scored/run.jsonl.bak-20260528-184949` (792 lines).
3. Stripped the 5 LOSS entries from `runs/scored/run.jsonl` (787 lines remain). Strip predicate
   gated on `state==LOSS AND secs<100 AND iid IN <5-set>` for safety.
4. Killed coord3 (PID 56713, the coord9-12 driver). coord1 (PID 30017, coord5-8) untouched.
5. Restarted coord3 (new PID 11090) with `--skip-setup --box-offset 8 --boxes 4`. New `todo=332`
   confirmed the 5 requeues landed (was 327 implied).

**Classification.** This is an operational fault per §4 (provider-class incident — OAuth token
rotation), not a model verdict. Per discipline, the 5 LOSSes are scrubbed and the instances
re-attempted. Single ledger-strip with explicit predicate + backup is the minimal intervention;
no harness change.

**Open hygiene gap (deferred to next-run §13 amendment, not hot-patched).** Token-refresh staging
runs once at provision-time. A long-lived run needs periodic re-staging (e.g., every 30 min, or on
detection of 401 in claude output). Today's mitigation is manual: re-stage on demand when a 401
storm is observed.

