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
else changes. That is the whole point of the data-source-agnostic `task.json` + EC2-box packaging
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

## Frozen run config (prereg §13 item 3)

The exact knobs a scored run freezes. The artifact is **model-agnostic** by construction (model
identity is a config parameter, `RCA_MODEL`, `CRAFT_CODEX_MODEL`, no code path branches on it,
grep-verified), so this block, not the code, records what the headline number ran under.

| knob | frozen value | source |
|---|---|---|
| generator model | `claude-sonnet-4-5` | `RCA_MODEL` (rung5_driver.py) |
| craft-volley model | `gpt-5.5` | `CRAFT_CODEX_MODEL`, pinned via `codex exec -c model=` |
| agent CLI | `@anthropic-ai/claude-code@2.1.150` | `npm i -g` (invokes the generator) |
| craft CLI | `@openai/codex@0.134.0` | `npm i -g` (invokes the volley model) |
| outer loop depth | `MAX_OUTER=5` | rung5_driver.py |
| stage caps (wall-clock, s) | recon 2000 · craft 3600 · audit 1200 | `RECON_CAP`/`CRAFT_CAP`/`AUDIT_CAP` |
| retry policy | INCOMPLETE only, on a verdict-independent platform fault (`FAULT_RE`); WIN/LOSS never reran | prereg §4 |
| EC2 | `m7i.xlarge`, `us-west-2`, AMI `ami-00563078bca04e287`, **100 GB EBS**, watchdog `+720 min` | provision_box.sh, run_fleet.sh |
| auth | claude = Max OAuth (keychain → `~/.claude/.credentials.json`, bills Max/$0); codex = `~/.codex/auth.json` | run_fleet.sh `stage_creds` |
| eligible denominator | **728** (731 − 3 §6 defects) | `runs/audit/eligible.txt` |

**Regression checks (the three 2026-05-25 harness faults; a recurrence reads as INCOMPLETE, never a method LOSS):**
1. **Non-login shell** — gate + box run via `bash -c` (not `-lc`); a login shell resets PATH and hides baked toolchains (Go/Rust/Node) → false RED gate. Preflight: gate goes GREEN on a Go gold patch.
2. **Ledger dir** — `log()` mkdirs its parent; stages log before setup, so a missing dir crashes the first call on a fresh box (false loop-failure).
3. **Serial gold selftests under emulation** — parallel container contention corrupts the gold pass-check; selftests run serially.

## Token access / auth (the harness is auth-agnostic)

The harness drives the `claude` and `codex` CLIs, which resolve credentials from standard env vars,
so **whoever reproduces it plugs in their own token source with no code change.** Claude Code's
precedence: cloud-provider creds (`CLAUDE_CODE_USE_BEDROCK=1` / `CLAUDE_CODE_USE_VERTEX=1` + provider
creds) → `ANTHROPIC_AUTH_TOKEN` → `ANTHROPIC_API_KEY` → subscription OAuth.

- **Canonical reproduction (e.g. Scale):** set `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` (PAYG, matches
  SWE-bench's own reference inference scripts), **or** `CLAUDE_CODE_USE_BEDROCK=1` + AWS creds for the
  Claude leg if billing through Bedrock. No harness change; the CLIs pick it up. This is the most
  likely evaluator path; the benchmark's native inference is direct-API and restartable.
- **Operator (our run):** Max-OAuth pushed to each box + `CLAUDE_SUBSCRIPTION=1` in the dispatch env,
  which makes `plan_env()` drop any stray `ANTHROPIC_API_KEY` so the run bills **Max/$0**, never PAYG.
  ⚠ Because an API key *overrides* the subscription in the precedence order, a leaked `ANTHROPIC_API_KEY`
  would silently bill PAYG. `CLAUDE_SUBSCRIPTION=1` is the guard.

## Reproduction contract (read before reproducing)

What "reproducible" means here, stated precisely so a third party hits no surprises:

- **Aggregate, not bit-identical.** The agent is stochastic (sampling), so reproduction reproduces the
  **aggregate resolve-rate within sampling variance** over the 728 eligible set, **not** a deterministic
  per-instance replay. A given instance flipping WIN/LOSS between runs is expected, not a defect.
- **Pinned surface.** Match every row in *Pinned versions* + *Frozen run config*, including the **agent
  CLI versions** (`claude-code@2.1.150`, `codex@0.134.0`). Install them with `npm i -g
  @anthropic-ai/claude-code@2.1.150 @openai/codex@0.134.0`. CLI releases can change flags/auth/model
  resolution, so they are frozen deps like any other.
- **Tokens are yours.** Set `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` (or Bedrock); see *Token access*. The
  `gpt-5.5` craft model is pinned via `codex exec -c model=gpt-5.5`. If your org exposes it under a
  different alias/snapshot, set `CRAFT_CODEX_MODEL` to that ID.
- **DockerHub.** 728 multi-GB images pull from `jefzda/sweap-images`; **`docker login` first**:
  anonymous pulls throttle (~100–200/6h) and would inject spurious mid-run failures.

## Execution paths (canonical vs operator)

The verdict is **dispatch-independent**: the official grader runs per-instance with no cross-instance
state, so any dispatch that drains the full eligible set yields the identical 728-verdict set.

- **Canonical / reproducible (what a third party runs):** `pro_run.py --mode run --shard i/N
  --eligible runs/audit/eligible.txt` — deterministic stripe of the frozen order, EC2 + pinned deps
  only, **zero custom infra** (no SQS/IAM/S3). This is the path to reproduce the number.
- **Operator convenience (our week-long run):** `coordinator.py --boxes N` — laptop-side dynamic
  dispatcher. Hands each box the next eligible instance over SSH as it finishes (near-100% box
  utilization vs idle static stripes), with fault tolerance (box-death requeue + reprovision,
  bounded poison-instance retries, crash-resume from the authoritative `runs/scored/run.jsonl`).
  Same per-instance unit as canonical, so verdicts match. Needs the laptop online as coordinator.

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
environment is wrong and it tells you the exact command to debug. **Don't proceed until it's
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
`runs/dev/`, `pro_smoke` → `scratch/`. dev vs scored, regenerable vs committed: read off the tree.

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
them). `pro_pilot.py:official_grade` builds both correctly.

## 4. Dev (local, emulated) vs scored (EC2, native)

- **Dev:** Mac/OrbStack, amd64 under Rosetta. Fine for small Python/Go/JS instances; **impractical
  for heavy repos** (webclients 4.7 GB, teleport 2.4 GB) and slow on big suites under emulation.
- **Scored:** EC2 `m7i.xlarge` (amd64 native, no emulation). Native matches Scale's environment. The
  whole-set driver (`pro_run.py --shard i/N`) and multi-box fleet (`audit_fleet.sh`, `coordinator.py`)
  are **built and validated on real boxes** (2026-05-27); the single-instance EC2-native recipe below
  still applies for a one-off.

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
- Capture must drop runtime blobs (redis `appendonly.aof`, `node_modules`, build dirs), handled by
  the denylist + 256 KB per-file cap in `_strip_test_blocks`.
- The eval repo clone is a hard dependency (dockerfiles + run_scripts read from disk by id).

## 6. Verify someone else's number (derive, don't trust)

Every committed result carries its captured source-only diff. To verify: take `patch.diff`, build
`pred.json`, run §3 on a clean container, confirm the verdict matches. No need to re-run the agent;
the grade is deterministic from the diff.

## Not yet load-bearing (honest gaps)

- Same-model `mini-swe-agent` control arm (would isolate scaffold from model in the differential).
  **Decided: not running it.** Removing codex shifts all load onto the scarce Claude budget, not
  budget-viable. Scaffold-only attribution stays permanently OPEN, not pending (prereg §12, C1).
- Packaging for Scale to run our pipeline on the held-out (containerized, model-creds, 200-turn
  budget). The held-out is Scale-run and relationship-gated, not a self-serve submission. See
  `PREREGISTRATION.md` §9.
