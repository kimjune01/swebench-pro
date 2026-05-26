# Procedure — reproduce a SWE-bench Pro result from scratch

This is the **load-bearing reproducibility contract** (predicate clause 5): a third party with
this repo, Docker, and model access reproduces a result and *derives* the number rather than
trusting it. Counting rules live in `PREREGISTRATION.md`; this file is *how you run it*.

**Status:** validated end-to-end. Per-instance loop (`pro_pilot.py`) officially resolves across
Python/Go/JS; the whole-set driver (`pro_run.py --mode audit|run`, frozen-order + shard + resume)
and the multi-box fleet (`audit_fleet.sh`) are built. EC2-native path validated (§4a).

## 0. Track — the only fork (public → private is this `if`)

```python
if TRACK == "public":     # scored public Pro run — this repo's current target
    source = "ScaleAI/SWE-bench_Pro"   # 731, in hand
    gate   = "F2P"         # reads FAIL_TO_PASS as the stopping signal — legal ONLY because
                           # public tests are visible (pro_pilot default)
    audit  = "§6"          # gold-patch defect audit applies (gold patches in hand)
elif TRACK == "private":  # Scale-run held-out — the small-scope flip
    source = "scale-held-out"          # Scale hands our driver a task.json (data-source-agnostic)
    gate   = "BLIND"       # P2P / repo-suite / budget. F2P is NEVER a stopping signal (leakage).
    audit  = None          # gold not in hand; Scale runs it
```

**Everything below is shared.** Going public→private is exactly: swap `source`, swap `gate`. Nothing
else changes — that is the whole point of the data-source-agnostic `task.json` + EC2-box packaging
(for skeptics *and* for Scale, who run the same self-contained driver rather than us conforming to
their harness). Residual knots on the private flip: model credentials + sandbox-trust on secret data.

## Pinned versions (a reproduction must match these)

| component | pin |
|---|---|
| dataset | `ScaleAI/SWE-bench_Pro` split `test` (731), revision `7ab5114912baf22bb098818e604c02fe7ad2c11f` |
| eval repo | `github.com/scaleapi/SWE-bench_Pro-os` commit `ca10a60a5fcae51e6948ffe1485d4153d421e6c5` |
| python | `swebench==4.1.0`, `datasets==4.8.5`, `pandas==3.0.3`, `docker==7.1.0` (docker-py) |
| images | `jefzda/sweap-images:<tag>` (DockerHub, amd64, immutable per-instance tags) |
| baseline scaffold (for the differential) | **SWE-Agent**, 200-turn limit (Scale's reported baseline) |

## 0. Prerequisites

You bring two things; **`bootstrap.sh` does the rest and proves it worked**:
- model CLIs `claude` (generator) + `codex` (craft filter), authenticated;
- an amd64 Docker host — Mac/OrbStack (emulated, dev only) or EC2 `m7i.xlarge` (native, scored — §4).

```bash
bash driver/bootstrap.sh      # idempotent: pins+clones eval repo, builds venv, checks docker,
                              # writes driver/.proenv, then VALIDATES with the $0 gold smoke.
. driver/.proenv              # exports SWEAP_OS_REPO + PY for every other command below
```

`bootstrap.sh` ends by grading a gold patch (must print `READY — env validated`). If it fails, the
environment is wrong and it tells you the exact command to debug — **don't proceed until it's
green.** That single command replaces the old clone/checkout/venv/validate dance. Re-run anytime.

## Layout (the dirs are the instructions)

```
driver/            pipeline code + bootstrap.sh + .proenv
skills/            recon · craft · audit
tasks/strata.json  curated difficulty strata (committed)
tasks/generated/   per-instance task JSONs from make_task — regenerable, gitignored
runs/dev/          telemetry runs (pilots, dev batches) — NO-CREDIT, gitignored  (prereg §2)
runs/scored/       frozen-tag scored-run artifacts — the committed trail          (prereg §10)
scratch/           ephemeral pad — gitignored; durable record goes in WORKLOG.md
```

Scripts default into these (no paths to pass): `make_task` → `tasks/generated/`, pilots/batches →
`runs/dev/`, `pro_smoke` → `scratch/`. dev vs scored, regenerable vs committed — read off the tree.

## 1. Build the task

```bash
BENCH=pro $PY driver/make_task.py <instance_id>   # writes tasks/generated/<instance_id>.json
```

Emits the self-contained Pro shape: `jefzda` image (via `image_uri.py`), `repo_dir=/app`, empty
`env_activate` (no conda), `before_repo_set_cmd`, `selected_test_files`, lowercase
`fail_to_pass`/`pass_to_pass`, `test_patch`, and `run_script`/`parser_script` baked in. **No gold
patch** (agent-safe).

## 2. Run a pilot

```bash
T=tasks/generated/<instance_id>.json
# gate self-test first ($0 tokens): must print RED on base, GREEN on gold
$PY driver/pro_pilot.py $T <instance_id> --selftest

# the real loop (spends model tokens): recon -> craft -> audit -> source-only capture -> grade
$PY driver/pro_pilot.py $T <instance_id>          # artifacts land in runs/dev/
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
- **Scored:** EC2 `m7i.xlarge` (amd64 native, no emulation). Native matches Scale's environment. The
  batch/sharding driver for Pro is 🔧 (port from the Verified `rung5_driver`/`shard_batch`); the
  **single-instance EC2-native path is built and validated** (recipe below).

### 4a. EC2-native single-instance recipe (validated 2026-05-25)

```bash
EBS_GB=100 bash driver/provision_box.sh heavy        # 100 GB (heavy images unpack large); writes /tmp/heavy.env
. /tmp/heavy.env; PEM=/tmp/${KEY}.pem
rsync -az -e "ssh -i $PEM" --exclude .venv --exclude .git --exclude runs --exclude scratch \
  ./ ec2-user@$PUBIP:~/swebench-pro/                 # ship the tree (no .git)
ssh -i $PEM ec2-user@$PUBIP '
  sudo dnf install -y git python3.11 python3.11-pip
  curl -LsSf https://astral.sh/uv/install.sh | sh
  cd ~/swebench-pro && git init -q && git add -A && git commit -qm init  # codex refuses untrusted (non-git) dirs
  UV_PYTHON=3.11 bash driver/bootstrap.sh'           # py3.11: pinned pandas 3.0/swebench need >=3.10
```
Model auth = **your Max OAuth, not the API key** (keeps it $0 on the Max plan; the key bills PAYG):
```bash
security find-generic-password -s "Claude Code-credentials" -w | ssh -i $PEM ec2-user@$PUBIP 'mkdir -p ~/.claude; cat > ~/.claude/.credentials.json; chmod 600 ~/.claude/.credentials.json'
cat ~/.codex/auth.json | ssh -i $PEM ec2-user@$PUBIP 'mkdir -p ~/.codex; cat > ~/.codex/auth.json; chmod 600 ~/.codex/auth.json'
# on the box, run loops with: unset ANTHROPIC_API_KEY; export PATH=$HOME/.local/bin:$PATH
```

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
