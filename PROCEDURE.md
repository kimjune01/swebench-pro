# Procedure — reproduce a SWE-bench Pro result from scratch

This is the **load-bearing reproducibility contract** (predicate clause 5): a third party with
this repo, Docker, and model access reproduces a result and *derives* the number rather than
trusting it. Counting rules live in `PREREGISTRATION.md`; this file is *how you run it*.

**Status:** the per-instance pilot path below is **real and validated** — two pilots officially
resolved across two languages: `ansible-5e369604` (Python) and `NodeBB-51d8f3b1` (JS, 40 s grade
after the capture fix). The multi-box batch driver for Pro is **not built yet** — single-instance
`pro_pilot.py` is the current unit. Steps marked 🔧 are not yet wired.

**Packaging = the EC2 box, not a harness.** The reproduction artifact is "provision an amd64 box,
clone, run the driver" (§4) — for skeptics *and* for Scale (who would run the same self-contained
driver pointed at held-out instances, rather than us conforming to their 200-turn agent harness).
Residual knots: model credentials, and sandbox-trust for running our code on secret held-out data.

## Pinned versions (a reproduction must match these)

| component | pin |
|---|---|
| dataset | `ScaleAI/SWE-bench_Pro` split `test` (731), revision `7ab5114912baf22bb098818e604c02fe7ad2c11f` |
| eval repo | `github.com/scaleapi/SWE-bench_Pro-os` commit `ca10a60a5fcae51e6948ffe1485d4153d421e6c5` |
| python | `swebench==4.1.0`, `datasets==4.8.5`, `pandas==3.0.3`, `docker==7.1.0` (docker-py) |
| images | `jefzda/sweap-images:<tag>` (DockerHub, amd64, immutable per-instance tags) |
| baseline scaffold (for the differential) | **SWE-Agent**, 200-turn limit (Scale's reported baseline) |

## 0. Prerequisites

```bash
# (a) this repo
export REPO=/path/to/swebench-pro

# (b) the eval repo (run_scripts + parser.py + dockerfiles + the official grader) — a HARD dependency
git clone https://github.com/scaleapi/SWE-bench_Pro-os.git /tmp/swebench-pro-os
( cd /tmp/swebench-pro-os && git checkout ca10a60a5fcae51e6948ffe1485d4153d421e6c5 )
export SWEAP_OS_REPO=/tmp/swebench-pro-os

# (c) a venv with the pins (uv or pip)
python -m venv .venv && . .venv/bin/activate
pip install "swebench==4.1.0" "datasets==4.8.5" "pandas==3.0.3" "docker==7.1.0"
export PY=$(command -v python)

# (d) model CLIs for the agent loop: `claude` (generator) + `codex` (craft filter), authed.
# (e) an amd64 Docker host. Mac/OrbStack runs the amd64 images under emulation (dev only);
#     EC2 m7i.xlarge runs them native (scored runs — §4).
```

## 0.5 Validate your environment ($0, no tokens) — DO THIS FIRST

Confirm the grader + images + scripts work on your box *before* spending anything, by grading a
**gold patch** (must resolve). This is the self-test that proves setup with zero tacit knowledge:

```bash
cd $SWEAP_OS_REPO
$PY $REPO/driver/pro_smoke.py <instance_id>     # builds 1-row sample + gold pred, grades it
# expect: eval_results.json -> {"<id>": true}, "Overall accuracy: 1.0"
```

If this is not `true`, stop — your Docker/arch/eval-repo/venv is wrong; fix it before §1.
(Known-good instance: `instance_ansible__ansible-5e369604e1930b1a2e071fecd7ec5276ebd12cb1-v0f01c69f1e2528b935359cfe578530722bca2c59`.)

## 1. Build the task

```bash
BENCH=pro $PY $REPO/driver/make_task.py <instance_id> $REPO/tasks/pro/<name>.json
```

Emits the self-contained Pro shape: `jefzda` image (via `image_uri.py`), `repo_dir=/app`, empty
`env_activate` (no conda), `before_repo_set_cmd`, `selected_test_files`, lowercase
`fail_to_pass`/`pass_to_pass`, `test_patch`, and `run_script`/`parser_script` baked in. **No gold
patch** (agent-safe). Requires `$SWEAP_OS_REPO` for the image-uri logic and run_scripts.

## 2. Run a pilot

```bash
# gate self-test first ($0 tokens): must print RED on base, GREEN on gold
$PY $REPO/driver/pro_pilot.py $REPO/tasks/pro/<name>.json <instance_id> --selftest

# the real loop (spends model tokens): recon -> craft -> audit -> source-only capture -> grade
SWEAP_OS_REPO=$SWEAP_OS_REPO $PY $REPO/driver/pro_pilot.py $REPO/tasks/pro/<name>.json <instance_id>
```

The PUBLIC-mode gate restores gold tests (`before_repo_set_cmd` last line) then runs
`run_script.sh` + `parser.py`, reporting F2P pass/fail. Capture is source-only: `git diff` minus
test files, build/runtime blobs, and any single-file diff >256 KB. The run ends by **re-grading
the captured diff on a fresh container** (gate == official grader) and prints `OFFICIAL RESOLVED`.

## 3. The authoritative grade

The agent's gate is the stopping signal, not the verdict. The number is the official grader on the
captured source-only diff:

```bash
cd $SWEAP_OS_REPO
$PY swe_bench_pro_eval.py --raw_sample_path <sample.jsonl> --patch_path <pred.json> \
  --output_dir <out> --scripts_dir run_scripts --num_workers 1 \
  --use_local_docker --dockerhub_username jefzda --redo
# verdict: <out>/eval_results.json -> {"<id>": true|false}
```

`pred.json` = `[{"instance_id","patch","prefix":""}]`. `sample.jsonl` needs lowercase
`fail_to_pass`/`pass_to_pass`/`selected_test_files_to_run` as **string** reprs (the grader `eval()`s
them) — `pro_pilot.py:official_grade` builds both correctly.

## 4. Dev (local, emulated) vs scored (EC2, native)

- **Dev:** Mac/OrbStack, amd64 under Rosetta. Fine for small Python/Go/JS instances; **impractical
  for heavy repos** (webclients 4.7 GB, teleport 2.4 GB) and slow on big suites under emulation.
- **Scored:** EC2 `m7i.xlarge` (amd64 native, no emulation) via `driver/provision.sh` — **bump the
  EBS volume to 100 GB** (Pro images unpack large). Native matches Scale's environment. The
  batch/sharding driver for Pro is 🔧 (port from the Verified `rung5_driver`/`shard_batch`).

## 5. Gotchas (each cost a pilot to find)

- Pro images are `ENTRYPOINT=[/bin/bash]` → start with `--entrypoint sleep` or the container exits.
- Fields are **lowercase** and the grader `eval()`s them → pass **string** reprs, not JSON arrays.
- Image URI: use `helper_code/image_uri.py:get_dockerhub_image_uri`; only `-vnan` is stripped, other
  `-v<sha>` suffixes are **kept**. The task must carry `repo` (image_uri does `repo.split("/")`).
- Capture must drop runtime blobs (redis `appendonly.aof`, `node_modules`, build dirs) — handled by
  the denylist + 256 KB per-file cap in `_strip_test_blocks`.
- The eval repo clone is a hard dependency (dockerfiles + run_scripts read from disk by id).

## 6. Verify someone else's number (derive, don't trust)

Every committed result carries its captured source-only diff. To verify: take `patch.diff`, build
`pred.json`, run §3 on a clean container, confirm the verdict matches. No need to re-run the agent —
the grade is deterministic from the diff.

## Not yet load-bearing (honest gaps)

- Pro batch/sharding driver (multi-box) — single-instance only today.
- Packaging for Scale to run our pipeline on the held-out (containerized, model-creds, 200-turn
  budget). The held-out is Scale-run and relationship-gated, not a self-serve submission — see
  `PREREGISTRATION.md` §9.
