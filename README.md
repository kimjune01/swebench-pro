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

## License

Repo: CC BY-SA-NS ([`LICENSE.md`](LICENSE.md)). Skills (`skills/`): dual-licensed CC BY-SA-NS **or**
GPL-3.0, recipient's choice ([`skills/LICENSE.md`](skills/LICENSE.md)).
