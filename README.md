# swebench-pro

The recon→craft→audit agent pipeline, pointed at **SWE-bench Pro**. Sibling to
[`swebench-verified`](https://github.com/kimjune01/swebench-verified) — one repo per benchmark so
each run's artifacts and number stand on their own, no branch-spelunking to tell them apart.

**Status: rig + plan, adapter not yet built.** This repo starts as a copy of the Verified rig (which
resolved 422/438 eligible there) plus [`PRO_PORT.md`](PRO_PORT.md) — the port plan. Pro is harder and
partly held out; whether this is a clean adapter swap or a new harness depends on a handful of unknowns
(dataset shape, prebuilt images, grader, env convention) that `PRO_PORT.md` enumerates. Nothing here
claims a Pro number yet.

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
