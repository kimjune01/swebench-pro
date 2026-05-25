#!/usr/bin/env python
"""$0 environment self-test: grade a Pro instance's GOLD patch through the official evaluator.
Must print RESOLVED=True — if not, the Docker/arch/eval-repo/venv setup is wrong (see PROCEDURE
§0.5). Portable: uses this interpreter (must have swebench+datasets+pandas+docker) and runs the
grader from $SWEAP_OS_REPO. Usage: pro_smoke.py <instance_id> [--offline]"""
import os, sys, json, subprocess, pathlib
import pandas as pd
from datasets import load_dataset

iid = sys.argv[1]
offline = "--offline" in sys.argv
repo = pathlib.Path(os.environ.get("SWEAP_OS_REPO", "/tmp/swebench-pro-os"))
assert (repo / "swe_bench_pro_eval.py").exists(), f"clone scaleapi/SWE-bench_Pro-os at {repo} (set SWEAP_OS_REPO)"
work = pathlib.Path("/tmp/pro_smoke") / iid
work.mkdir(parents=True, exist_ok=True)

r = next(x for x in load_dataset("ScaleAI/SWE-bench_Pro", split="test") if x["instance_id"] == iid)

def as_str(v):  # harness eval()s these → need python-literal strings, not arrays
    return v if isinstance(v, str) else json.dumps(list(v))

row = dict(r)
row["fail_to_pass"] = as_str(r["fail_to_pass"]); row["pass_to_pass"] = as_str(r["pass_to_pass"])
row["selected_test_files_to_run"] = as_str(r["selected_test_files_to_run"])
pd.DataFrame([row]).to_json(work / "sample.jsonl", orient="records", lines=True)
json.dump([{"instance_id": iid, "patch": r["patch"], "prefix": ""}], open(work / "gold.json", "w"))

cmd = [sys.executable, "swe_bench_pro_eval.py",
       "--raw_sample_path", str(work / "sample.jsonl"), "--patch_path", str(work / "gold.json"),
       "--output_dir", str(work / "out"), "--scripts_dir", "run_scripts", "--num_workers", "1",
       "--use_local_docker", "--dockerhub_username", os.environ.get("DOCKERHUB_USER", "jefzda"), "--redo"]
if offline:
    cmd.append("--block_network")
p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(repo))
res = work / "out" / "eval_results.json"
verdict = json.load(open(res)).get(iid) if res.exists() else None
tail = "\n".join((p.stdout + p.stderr).splitlines()[-4:])
print(f"\n=== {iid}\n    offline={offline}  RESOLVED={verdict}\n{tail}")
sys.exit(0 if verdict else 1)
