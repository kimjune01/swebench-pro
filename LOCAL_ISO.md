# Local isolation — iterating on failing instances on the Mac

The EC2 driver (`rung4_driver.py`) is built for a remote box: every container call goes
through `ssh(...) sudo docker ...`. For *iteration* on a handful of known-failing
instances, that round-trip (provision → ssh → sudo) is overhead. This is the local
translation: run the same eval containers directly on the Mac under OrbStack, so the
edit→gate cycle is a local `docker exec`.

**Scope.** This is a dev-loop convenience, not a grading path. Wins are still official-test
verdicts (the predicate in `PRO_PORT.md` is unchanged). Conversions on the 16 not-won are
**telemetry, not Verified wins** — they're a labeled set; see the no-credit rule in
`PRO_PORT.md`. Keep these runs out of any `results/` tree.

## The environment

- **OrbStack** provides the Docker engine on macOS. Native arch is `aarch64`; the official
  SWE-bench eval images are `x86_64`, so every pull/run needs `--platform linux/amd64`
  (Rosetta emulation). Verified working: `docker run --platform linux/amd64 alpine uname -m`
  → `x86_64`.
- If the engine wedges in "Starting" with `docker info` hanging and `vmgr.log` showing
  `vmgr is already running (socket)`, it's a stale handoff lock. Fix: quit OrbStack, kill
  leftover `OrbStack`/`vmgr` procs, relaunch. (Hit once during setup, 2026-05-24.)
- Task JSONs are generated with the **Verified** venv: `../swebench-verified/.venv`
  (swebench 4.1.0 + datasets). No separate Pro venv needed yet — Pro's dataset adapter is
  still unbuilt (see `PRO_PORT.md`).

## The translation (EC2 driver → local)

The single seam is `rung4_driver.py:ssh()` — everything funnels through it. Local mode is
three substitutions:

| EC2 driver | Local |
|---|---|
| `ssh(remote)` → run on box | run `remote` in a local shell |
| `sudo docker pull/run <img>` | `docker pull/run --platform linux/amd64 <img>` (no sudo) |
| `box`/`gate` helpers wrap `ssh … sudo docker exec` | wrap `docker exec` directly |

`driver/local_iso.sh` implements this for the **manual** loop (setup→warm→helpers, no
recon/craft/audit). It does not run the autonomous pipeline — for that, the same three
substitutions would be applied behind a `LOCAL=1` flag in `ssh()`, but manual iteration on
known failures doesn't need the agent loop.

## Usage

```bash
# one instance (defaults to tasks/not_won/<iid>.json)
driver/local_iso.sh django__django-15987
```

Produces `iso/<iid>/`:
- `cid` — running container (the SUT)
- `failbase.txt` — fail-on-base capture (audit's pre-existing-failure baseline)
- `gate` — runs the official `test_cmd` (FAIL_TO_PASS + PASS_TO_PASS) in the container
- `box` — runs an arbitrary command at repo root in the container

Iterate:
```bash
iso/django__django-15987/box 'sed -i ... django/db/...'   # edit
iso/django__django-15987/gate                              # verify
docker kill $(cat iso/django__django-15987/cid)            # tear down
```

The test patch is staged in `/tmp` and committed (not left in the tree), so a captured
`git diff HEAD` prediction never leaks a `delete tp.patch` hunk — the django-15987
`-R`-serialization false-positive the EC2 driver also guards against.

## The 16 not-won (the iteration corpus)

Generated into `tasks/not_won/`. Classification and which lever each validates is in
`PRO_PORT.md` ("The failed set"). Quick map:

- **heavy-suite hangs** (small to gate, slow to run): sympy-13878, sympy-19040,
  matplotlib-25311, django-15957 — suite-selection / stage-cap lever.
- **gate-divergence**: pytest-5787, django-14170 — attestation hash-as-precondition.
- **recon-ceiling**: django-11734, django-14351 — tri-abduction step.
- **genuinely-hard**: astropy-13398, django-16263.
- **craft-overfit**: sympy-13091. **other sympy**: sympy-20438, sympy-17139.
- **rerun-eligible (count)**: django-15563, django-14404 (box-death), django-15987
  (contamination, fixed).
