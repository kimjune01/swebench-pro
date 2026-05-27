# swebench-pro worklog — `prereg-pro-v1`

Newest first. This is the **scored-run trail** for the frozen artifact `prereg-pro-v1`. Pre-freeze
development history is in [`WORKLOG_PREFREEZE.md`](WORKLOG_PREFREEZE.md). Per §13, each scored tag
gets its own worklog; this one carries only `v1`'s run.

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
