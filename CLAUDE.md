# swebench-pro — agent orientation

Read this first. The recon→craft→audit pipeline pointed at **SWE-bench Pro** (public set = the
731 `ScaleAI/SWE-bench_Pro` instances).

## Start here (one command, idempotent, self-validating)

```bash
bash driver/bootstrap.sh      # clones+pins the eval repo, builds .venv, checks docker,
                              # writes driver/.proenv, validates with the $0 gold smoke
. driver/.proenv              # exports SWEAP_OS_REPO + PY for every command
```
Prints `READY` or tells you the exact debug command. Don't proceed until green.

## Where things are (the dirs are the instructions)

```
driver/            pipeline code + bootstrap.sh
skills/            recon · craft · audit
tasks/strata.json  difficulty strata (committed) · tasks/generated/ (regenerable, ignored)
runs/dev/          telemetry runs — NO-CREDIT, ignored   · runs/scored/  committed trail
scratch/           ephemeral — ignored; durable record → WORKLOG.md
```

## The docs, in reading order

- **PROCEDURE.md** — how to run (bootstrap → make_task → pro_pilot → official grade). Reproducible
  from scratch; pinned versions.
- **PREREGISTRATION.md** — the rules. **We are pre-scored-run; the doc is unfrozen.** Key posture:
  the public number is an **audition** to earn a Scale-run held-out eval; **public iteration is
  free** (held-out is a physical firewall), but fixes must stay **general/instance-blind**; a
  restart is always the **whole set**; failure-mode counting is a fixed state machine.
- **WORKLOG.md** — what happened, newest first. Start here for current state.
- **PRO_PORT.md** — original port plan / background. **LIMITATIONS / contamination** posture lives
  in the prereg (§12: contamination is symmetric → isolates the scaffold claim, not a confound).

## Current state (2026-05-27)

Adapter **built and validated**: grader works across Python/Go/JS; gate red-on-base/green-on-gold;
source-only capture (size-capped, language-aware test stripping). **Two pilots officially RESOLVED**
(ansible/Py, NodeBB/JS) + a **6/6 hardest-reasoning telemetry batch** (dev-mode, no-credit). We run
**Sonnet 4.5** (`RCA_MODEL`); the reference baseline is Sonnet 4 + gpt4o in **SWE-Agent** — so our
differential is *largely scaffold* (same model family).

**Built since:** whole-set driver (`pro_run.py`) + multi-box fleet (`audit_fleet.sh`, `coordinator.py`),
validated on real boxes (2026-05-27); freeze-gate items 1–3 done. **Not doing:** the same-model
`mini-swe-agent` control arm — removing codex shifts all load onto the scarce Claude budget, so it's
not budget-viable; scaffold-only attribution stays permanently OPEN (prereg §12, not a TODO). **Not yet
done:** the §13 freeze decision itself (cut `prereg-pro-vN` tag + launch). No
scored run has been started or frozen — keep it that way until deliberately committing.

## Conventions

- Dev-mode subset runs are **telemetry, not a score** (labeled-set, no-credit). A scored run is the
  whole eligible set under a frozen tag (prereg §2).
- Commit the honest trail; losing runs stay. Generated/ephemeral files are gitignored.
- The user runs on a Max subscription — token volume is the scarce resource; everything verifiable
  at $0 (gold-patch grading, gate selftests) should be done before spending tokens.
