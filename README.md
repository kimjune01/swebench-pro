# swebench-pro

The recon→craft→audit agent pipeline, pointed at **SWE-bench Pro**. Sibling to
[`swebench-verified`](https://github.com/kimjune01/swebench-verified) — one repo per benchmark so
each run's artifacts and number stand on their own, no branch-spelunking to tell them apart.

**Status: adapter built and validated; pre-scored-run.** The Pro adapter works end-to-end — grader
across Python/Go/JS, gate, source-only capture — with **two pilots officially RESOLVED** (ansible,
NodeBB) and a 6/6 hardest-reasoning telemetry batch (dev-mode, no-credit). No scored run has been
started or frozen. **Agents start at [`CLAUDE.md`](CLAUDE.md)**; setup is one command
(`bash driver/bootstrap.sh`). See [`PROCEDURE.md`](PROCEDURE.md) (how to run),
[`PREREGISTRATION.md`](PREREGISTRATION.md) (the rules + the audition posture), and
[`WORKLOG.md`](WORKLOG.md) (current state). `PRO_PORT.md` is the original port plan/background.

## Goal (the predicate)

A single **frozen, instance-agnostic artifact** that clears SWE-bench Pro under **official third-party
grading on the held-out private set, in one submission**, verifiably free of per-instance priors. The
deliverable is that artifact + its reproducible attestation trail — not a percentage. A change is
admissible only if it stays **general** (instance-blind), leaks **no** held-out signal back into the
artifact, wins **only** on official-test verdicts, keeps an **honest denominator**, and is
**reproducible**. See `PRO_PORT.md` for the full predicate and the public-then-private strategy.

## Layout

- `skills/{recon,craft,audit}/skill.md` — the pipeline skills (the live, evolving copies; dual-licensed,
  see `skills/LICENSE.md`). Verified's are frozen; these move as the Pro adapter is built.
- `driver/` — orchestration, sharding, provisioning, grading. Mostly benchmark-agnostic; the
  Verified-specific constants are the adapter surface (`PRO_PORT.md` lists the touchpoints).
- `PRO_PORT.md` — the port plan: goal predicate, strategy, verification contracts, efficiency levers,
  Verified-session failure taxonomy, and the open questions to resolve first.

## Docs

Three kinds: **specs** (what we will do — rules and contracts), **journals** (what actually happened
— newest first), and **retros** (what we learned). Read specs to start, journals to catch up,
retros to avoid re-deriving lessons.

### Specs — read in this order

| doc | what it answers | read when |
|---|---|---|
| [`CLAUDE.md`](CLAUDE.md) | agent orientation: one-command setup, where things live, current state | **first, always** |
| [`PROCEDURE.md`](PROCEDURE.md) | how to run: bootstrap → make_task → pilot → official grade; pinned versions; reproduction contract | running or reproducing a result |
| [`PREREGISTRATION.md`](PREREGISTRATION.md) | the rules: predicate, two modes, restart scope, failure-mode state machine, freeze gate (§13) | before claiming a number / cutting a tag |
| [`PREREGISTRATION-cheap-ablation.md`](PREREGISTRATION-cheap-ablation.md) | cheap-ablation companion spec | before launching the ablation arm |
| [`PRO_PORT.md`](PRO_PORT.md) | original port plan + background; adapter touchpoints | understanding *why* the adapter is shaped this way |
| [`LOCAL_ISO.md`](LOCAL_ISO.md) | local isolation / sandbox notes | debugging the local dev path |

### Journals

| doc | covers |
|---|---|
| [`WORKLOG.md`](WORKLOG.md) | scored-run trail for the frozen artifact (current). **Source of truth for current state.** |
| [`WORKLOG_PREFREEZE.md`](WORKLOG_PREFREEZE.md) | pre-freeze development history |

### Retros — lessons compressed for future me

Filed under [`docs/retros/`](docs/retros/), one per ISO date + topic. Read before the next bench run
or operator-infra rebuild so we don't repeat the path.

- [`2026-05-29-operator-infra-v1.md`](docs/retros/2026-05-29-operator-infra-v1.md) — what we built reactively
  (5 operator-infra layers), what hurt (silent failures, two controllers fighting, watchmen unwatched,
  lossy ramps), the k8s-reinvention realization, and the Pulumi+Go v2 direction with substrate division

### Bench defects (read before reproducing)

[`docs/bench-defects.md`](docs/bench-defects.md) — upstream Pro behaviors we discovered the hard way:
silent grader deadlocks, container leaks, perception poisoning, indistinguishable LOSS detail. If
you're reproducing and seeing unexplained hangs or surprise LOSSes, start there. Includes the
mitigations we built and the integrity-direction note (all defects bias toward inflated LOSS,
so headline numbers are conservative).

State at a glance: **adapter built + validated; freeze-gate items 1–3 done; pre-scored-run.** Only the
§13 freeze decision (cut `prereg-pro-vN` + launch) remains. `WORKLOG.md` is the source of truth.

## Reproducibility caveat — plan for provider flakiness

The Claude Code service operates at ~99% uptime over 90d (the whole Anthropic
stack averages similarly — claude.ai 98.83%, Console 99.23%, API 99.09%, Code
99.08%, snapshot 2026-05-29). The stripe pattern in the statuspage history is
consistent with frequent degraded-but-not-incident-class events: partial
errors, regional slowness, **server-side credential rotations**.

![Anthropic stack uptime — 90d snapshot 2026-05-29](docs/images/anthropic-stack-uptime-2026-05-29.png)

A multi-hour Claude-backed fleet (this run is 10+ hours per shard) will
typically encounter at least one `PROVIDER_CRED_REJECT` wave per campaign:
boxes start returning verbatim `Failed to authenticate. API Error: 401 Invalid
authentication credentials` in subprocess capture, with 0-byte patch
artifacts, recurring across instances on the same box. The operator did not
log out — the credential pushed at provisioning was rejected by upstream
after the fact (OAuth token rotation).

**Recovery loop** (codified in `docs/auth_storm_2026-05-29.md`): halt
dispatch → re-extract creds from the operator's authoritative store →
scp to all boxes → restart coordinator → strip the wave to
`runs/scored/auth_strips.jsonl` and re-dispatch.

**Prereg accounting**: `PREREGISTRATION.md` §14 amendment 2026-05-29 adds
`PROVIDER_CRED_REJECT` as an enumerated fault class with four invariants
(canonical 401 string + 0-byte patch + ≥3-instance wave + resolution by fresh
cred push). The class slots between provider-incident (statuspage-required)
and infra-class (on-box-log-required); on-box subprocess capture is the
corroboration, same shape as dmesg-for-OOM.

A reproducer who doesn't plan for this will see their score artificially
depressed by 5+ percentage points per missed wave (today's was 28
instances → −6.3% noise). Plan for it.

## License

Repo: CC BY-SA-NS ([`LICENSE.md`](LICENSE.md)). Skills (`skills/`): dual-licensed CC BY-SA-NS **or**
GPL-3.0, recipient's choice ([`skills/LICENSE.md`](skills/LICENSE.md)).
