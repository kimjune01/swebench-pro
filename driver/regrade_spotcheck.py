#!/usr/bin/env python3
"""Tier-1 kill-check #3: independently re-grade captured WIN diffs with the
official Pro grader on fresh containers. Model-free (no tokens). Confirms no
binding leak (local-green / official-red).

Replicates driver/pro_pilot.py:official_grade() inline to avoid the
rung5_driver import-time sys.argv side effect."""
import sys, os, json, pathlib, subprocess, time
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent.parent
GEN = ROOT / "tasks" / "generated"
HERE = ROOT / "runs" / "dev"
HERE.mkdir(parents=True, exist_ok=True)
SWEAP = os.environ.get("SWEAP_OS_REPO", "/tmp/swebench-pro-os")


def official_grade(inst, src):
    iid = inst["instance_id"]; tag = iid.replace("/", "_")
    samp = HERE / f"audit_sample_{tag}.jsonl"; pred = HERE / f"audit_pred_{tag}.json"
    row = {k: inst[k] for k in inst if k not in ("run_script", "parser_script")}
    row["fail_to_pass"] = json.dumps(inst["fail_to_pass"])
    row["pass_to_pass"] = json.dumps(inst["pass_to_pass"])
    row["selected_test_files_to_run"] = json.dumps(inst["selected_test_files"])
    pd.DataFrame([row]).to_json(samp, orient="records", lines=True)
    json.dump([{"instance_id": iid, "patch": src, "prefix": ""}], open(pred, "w"))
    out = HERE / f"audit_grade_{tag}"
    subprocess.run([sys.executable, "swe_bench_pro_eval.py", "--raw_sample_path", str(samp),
                    "--patch_path", str(pred), "--output_dir", str(out), "--scripts_dir", "run_scripts",
                    "--num_workers", "1", "--use_local_docker", "--dockerhub_username",
                    os.environ.get("DOCKERHUB_USER", "jefzda"), "--redo"], cwd=SWEAP)
    res = out / "eval_results.json"
    return json.load(open(res)).get(iid) if res.exists() else None


ids = [l.strip() for l in open("/tmp/regrade_ids.txt") if l.strip()]
patchmap = json.load(open("/tmp/regrade_patchmap.json"))
results = {}
for iid in ids:
    t0 = time.time()
    tasks = json.load(open(GEN / f"{iid}.json"))
    inst = next(t for t in (tasks if isinstance(tasks, list) else [tasks])
                if t["instance_id"] == iid)
    diff = open(patchmap[iid]).read()
    print(f"GRADING {iid}  ({len(diff)}B diff)", flush=True)
    try:
        verdict = official_grade(inst, diff)
    except Exception as e:
        verdict = f"ERROR:{e}"
    dt = int(time.time() - t0)
    results[iid] = {"verdict": verdict, "secs": dt}
    print(f"RESULT {verdict}  {dt}s  {iid}", flush=True)
    json.dump(results, open("/tmp/regrade_results.json", "w"), indent=2)

green = sum(1 for r in results.values() if r["verdict"] is True)
print(f"DONE: {green}/{len(results)} official-RESOLVED (expected all — these were run WINs)", flush=True)
