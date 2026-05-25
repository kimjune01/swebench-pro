# Procedure

The exact steps to reproduce a run, adapted from the Verified procedure for **SWE-bench Pro**.
See `PRO_PORT.md` for the goal predicate and `README.md` for status.

**Status: in progress.** The provisioning layer transfers as-is; the task/gate/grade **adapter
is not built yet**. Steps are marked:
- ✅ **works now** — transfers unchanged from the Verified rig.
- 🔧 **adapter TODO** — described as intended; the code does not exist yet (the Pro grading
  model diverges enough from Verified that this is a new adapter, not a constant swap — see
  "What changes" below).

Nothing here claims a Pro number. This file is the plan we execute against.

## What changes from Verified (the adapter surface)

Resolved by inspecting `ScaleAI/SWE-bench_Pro` and `scaleapi/SWE-bench_Pro-os`:

| Aspect | Verified | **Pro** |
|---|---|---|
| Dataset | `princeton-nlp/SWE-bench_Verified` | `ScaleAI/SWE-bench_Pro` (731 public; held-out private split) |
| Field case | `FAIL_TO_PASS` / `PASS_TO_PASS` (JSON) | `fail_to_pass` / `pass_to_pass` (lowercase) |
| Image | `swebench/sweb.eval.x86_64.<key>` (conda) | `jefzda/sweap-images:<dockerhub_tag>` (language-native) |
| Image arch | amd64 | **amd64** (confirmed via `docker manifest inspect`) — native on EC2, no emulation |
| Repo dir | `/testbed` | **`/app`** |
| Env | conda `activate testbed` | **none** — `node:18` etc.; setup via `before_repo_set_cmd` + the run script |
| Test command | `install_config.test_cmd` (regex from eval spec) | **no `test_cmd`** — per-instance `run_scripts/<id>/run_script.sh` |
| Result parsing | swebench `get_logs_eval` / `get_eval_tests_report` | per-instance `run_scripts/<id>/parser.py` |
| Grader | `swebench.harness.run_evaluation --dataset_name` | `swe_bench_pro_eval.py --scripts_dir run_scripts --dockerhub_username jefzda` |
| Languages | all Python | Python, JavaScript, Go, + more (NodeBB, qutebrowser, ansible, openlibrary, teleport, navidrome) |

**Note on the source-only contract:** Pro's `run_script.sh` re-applies the gold tests itself
(`git checkout <instance_commit> -- <test_files>`, `cp -r test/.`), so the false-green class
the Verified gate fix closes is **structurally handled by Pro's own grader**. The local gate
should still replicate it, but it is not new risk on Pro.

## 0. Prerequisites

- An **amd64** Linux Docker host. Pro images are linux/amd64; `driver/provision.sh` provisions
  an AWS EC2 `m7i.xlarge` (amd64) — they pull and run **natively, no Rosetta/`--platform`
  emulation** (unlike the local Mac/OrbStack path in `LOCAL_ISO.md`). ✅
  - **Bump the disk** in the provisioner from 40–50 GB to **80–100 GB**: Pro repos are
    enterprise-scale and images are larger (~0.9 GB compressed → a few GB unpacked, plus deps
    like `node_modules`/redis). 🔧 (one-line edit to `provision.sh`)
- On the plan host (your laptop): `claude` CLI (generator), `codex` CLI (filter), Python with
  `pip install -r requirements.txt`. ✅
- For grading, clone `scaleapi/SWE-bench_Pro-os` (provides `run_scripts/`, `parser.py`, and
  `swe_bench_pro_eval.py`); `pip install -r` its requirements. 🔧
- Models run on the plan host; only the system-under-test container goes offline. Auth notes
  (subscription vs API key, `CLAUDE_SUBSCRIPTION=1`, `RCA_MODEL`, `SSH_USER`) are identical to
  Verified — see that repo's `PROCEDURE.md` §0. ✅

## 1. Build the task JSON 🔧

```bash
python driver/make_task.py <instance_id> tasks/<instance_id>.json   # BENCH=pro
```

Intended behavior (adapter TODO): pull the instance from `ScaleAI/SWE-bench_Pro`, derive the
image (`jefzda/sweap-images:<tag>` via the `helper_code/image_uri.py` tag logic), set
`repo_dir=/app`, leave `env_activate` empty, and carry `before_repo_set_cmd`,
`selected_test_files_to_run`, lowercase `fail_to_pass`/`pass_to_pass`, `test_patch`, and
`base_commit` into the shape the driver expects. The "test command" is not a string — it is the
instance's `run_scripts/<id>/run_script.sh`, so the task records the run-script path, not a
`test_cmd`.

**Gotchas confirmed by the gold-patch smoke (see WORKLOG):**
- The Pro evaluator `eval()`s `fail_to_pass`, `pass_to_pass`, and `selected_test_files_to_run`,
  so they must be **Python-literal strings** (`'["a","b"]'`), not JSON arrays. The HF dataset's
  casing is already lowercase; the repo's `sweap_eval_full_v2.jsonl` ships **uppercase**
  `FAIL_TO_PASS`/`PASS_TO_PASS` (internally inconsistent with its own harness — alias to lowercase).
- The grader reads per-instance Dockerfiles from disk (`dockerfiles/{base,instance}_dockerfile/
  <id>/`) and scripts from `run_scripts/<id>/`, so a clone of `scaleapi/SWE-bench_Pro-os` is a
  hard dependency. Use `get_dockerhub_image_uri` for the image URI — only `-vnan` is stripped;
  any other `-v<sha>` suffix is **kept**.

## 2. Get an offline-capable Docker box ✅ (disk tweak 🔧)

```bash
bash driver/provision.sh        # after bumping VolumeSize to 80–100 GB
```

Unchanged from Verified: writes `/tmp/v4smoke.env` (`KEY`, `PUBIP`, `IID`, `SG`, `REGION`),
installs Docker, arms the self-terminate watchdog. `provision_box.sh <name>` for batch boxes.
Pro images being amd64, the EC2 host runs them natively.

## 3. Run the pipeline 🔧

```bash
python driver/rung5_driver.py /tmp/v4smoke.env tasks/<instance_id>.json <instance_id>
```

Same recon → craft → audit loop and source-only gate, with the adapter changes:
1. Pull `jefzda/sweap-images:<tag>`, start the container, `git apply` the test patch and commit
   it at `/app` (so the captured patch excludes test changes).
2. Run `before_repo_set_cmd` + the instance `run_script.sh` once online to install deps and
   capture the fail-on-base baseline. No conda activation.
3. Disconnect the container from the network (offline SUT).
4. **recon / craft / audit** as on Verified. The **gate runs the instance's `run_script.sh`**
   (which restores gold tests itself) and classifies via the instance's **`parser.py`**, not the
   swebench marker regex. The andon + source-only prompts carry over unchanged.
5. Outer loop (max 3), capture `git diff` as the model patch, tear down.

Outputs land in the same per-instance artifact shape (`r4_*`, ledger, hypothesis graph).

## 4. Grade with the official Pro harness (the real verdict) 🔧

The driver's gate is the stopping signal, not the grader. For the authoritative verdict, run the
Pro evaluator from `scaleapi/SWE-bench_Pro-os`:

```bash
python swe_bench_pro_eval.py \
  --raw_sample_path=swe_bench_pro_full.csv \
  --patch_path=<predictions>.json \
  --output_dir=<out> \
  --scripts_dir=run_scripts \
  --num_workers=1 \
  --dockerhub_username=jefzda
```

`<predictions>.json` maps `instance_id` → model patch (gather via `helper_code/gather_patches.py`
shape). Sanity-check the harness first with the gold `patch` column (must grade RESOLVED).
Treat that report, not this repo's `RESOLVED`, as the verdict.

## Batch runs 🔧

Mirror Verified: `provision_box.sh` per box, `shard_batch.py` to spread instances (give the
heaviest repos — teleport/ansible/NodeBB — solo boxes), `launch_generic.sh` with
`CLAUDE_SUBSCRIPTION=1`, then grade each box's shard and `archive_batch.py`. Stream-monitor every
run (`driver/MONITORING.md`). All `*_batch` scripts need the same Pro-field/image adapter as §1.

## 5. Archive into the repo ✅

Copy run outputs into `results/<instance_id>/` (separate tree from Verified) and append a
`WORKLOG.md` entry. Pro gets its own documented-defects list — never "instances we failed" (the
no-priors / honest-denominator rule from `PRO_PORT.md` still binds).

## Teardown ✅

Identical to Verified:
```bash
. /tmp/v4smoke.env
aws ec2 terminate-instances --instance-ids "$IID" --region "$REGION"
aws ec2 delete-security-group --group-id "$SG" --region "$REGION"
aws ec2 delete-key-pair --key-name "$KEY" --region "$REGION"
```

## Sequence to build the adapter (the actual next work)

1. **One-instance smoke, by hand:** pick a small public instance (a Python repo like qutebrowser
   or ansible), `docker pull` its `jefzda/sweap-images` tag on an EC2 box, run its
   `run_script.sh` against the gold `patch`, confirm `parser.py` reports the F2P resolved. This
   validates image + grader before any driver code.
2. **`make_task.py` Pro mode** (§1) → **`rung5_driver` gate swap** (run_script.sh + parser.py,
   `/app`, no conda) (§3) → **grade wiring** (§4).
3. Small sharded batch, then the methodeutics loop on the public set toward a frozen artifact.
4. Private split last: one blind submission (see `PRO_PORT.md` "Blind mode").
