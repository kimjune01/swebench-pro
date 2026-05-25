#!/usr/bin/env python3
"""Build a driver task JSON from a SWE-bench instance id. BENCH=verified|pro.

Usage: [BENCH=pro] python make_task.py <instance_id> [out.json]
  verified: python make_task.py pallets__flask-5014 tasks/pallets__flask-5014.json
  pro:      BENCH=pro python make_task.py instance_ansible__ansible-... tasks/....json

Verified shape (rung4/5_driver):
  instance_id, image_name, repo_dir=/testbed, env_activate (conda), test_patch,
  install_config.test_cmd, problem_statement, FAIL_TO_PASS, PASS_TO_PASS
Pro shape (self-contained — no conda, no test_cmd; the "test command" is the
  instance run_script + parser, baked in from the eval-repo clone):
  instance_id, bench=pro, image_name (jefzda/sweap-images:<tag>), repo_dir=/app,
  env_activate="", base_commit, before_repo_set_cmd, selected_test_files (list),
  test_patch, problem_statement, fail_to_pass, pass_to_pass, run_script, parser_script

Pro requires a clone of scaleapi/SWE-bench_Pro-os (for image_uri + run_scripts/<id>/);
point at it with SWEAP_OS_REPO (default /tmp/swebench-pro-os). No gold patch is written
(tasks stay agent-safe; the oracle dry-run fetches gold from the dataset by id).

Requires: pip install swebench datasets
"""
import json, os, sys, re, ast, pathlib

BENCH = os.environ.get("BENCH", "verified")
iid = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else f"{iid}.json"


def _as_list(v):
    if isinstance(v, (list, tuple)): return list(v)
    return ast.literal_eval(v) if isinstance(v, str) and v.strip().startswith("[") else json.loads(v)


def build_verified(iid):
    from datasets import load_dataset
    from swebench.harness.test_spec.test_spec import make_test_spec
    ds = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")
    inst = next(r for r in ds if r["instance_id"] == iid)
    spec = make_test_spec(inst, namespace="swebench")
    m = re.search(r">>>>> Start Test Output'\n(.*?)\n: '>>>>> End Test Output", spec.eval_script, re.S)
    test_cmd = m.group(1).strip() if m else "python -m pytest -rA"
    task = {
        "instance_id": iid,
        "image_name": f"docker.io/{spec.instance_image_key}",
        "repo_dir": "/testbed",
        "env_activate": "source /opt/miniconda3/bin/activate testbed",
        "test_patch": inst["test_patch"],
        "install_config": {"test_cmd": test_cmd},
        "problem_statement": inst["problem_statement"],
        "FAIL_TO_PASS": json.loads(inst["FAIL_TO_PASS"]),
        "PASS_TO_PASS": json.loads(inst["PASS_TO_PASS"]),
    }
    note = f"  image: {task['image_name']}\n  test_cmd: {test_cmd}"
    return task, note


def build_pro(iid):
    from datasets import load_dataset
    repo = pathlib.Path(os.environ.get("SWEAP_OS_REPO", "/tmp/swebench-pro-os"))
    assert (repo / "helper_code" / "image_uri.py").exists(), f"clone scaleapi/SWE-bench_Pro-os at {repo} (set SWEAP_OS_REPO)"
    sys.path.insert(0, str(repo))
    from helper_code.image_uri import get_dockerhub_image_uri
    ds = load_dataset("ScaleAI/SWE-bench_Pro", split="test")
    inst = next(r for r in ds if r["instance_id"] == iid)
    sdir = repo / "run_scripts" / iid
    run_script = (sdir / "run_script.sh").read_text()
    parser_script = (sdir / "parser.py").read_text()
    image = get_dockerhub_image_uri(iid, os.environ.get("DOCKERHUB_USER", "jefzda"), inst["repo"])
    task = {
        "instance_id": iid,
        "bench": "pro",
        "image_name": image,
        "repo": inst["repo"],            # needed by the grader's image_uri (repo.split("/"))
        "repo_dir": "/app",
        "env_activate": "",
        "repo_language": inst["repo_language"],
        "base_commit": inst["base_commit"],
        "before_repo_set_cmd": inst["before_repo_set_cmd"],
        "selected_test_files": _as_list(inst["selected_test_files_to_run"]),
        "test_patch": inst["test_patch"],
        "problem_statement": inst["problem_statement"],
        "fail_to_pass": _as_list(inst["fail_to_pass"]),
        "pass_to_pass": _as_list(inst["pass_to_pass"]),
        "run_script": run_script,
        "parser_script": parser_script,
    }
    note = (f"  image: {image}\n  lang: {inst['repo_language']}  repo_dir: /app (no conda)\n"
            f"  tests: {task['selected_test_files']}")
    return task, note


task, note = (build_pro if BENCH == "pro" else build_verified)(iid)
json.dump([task], open(out, "w"), indent=1)
f2p = task.get("fail_to_pass", task.get("FAIL_TO_PASS")); p2p = task.get("pass_to_pass", task.get("PASS_TO_PASS"))
print(f"wrote {out}  [BENCH={BENCH}]")
print(note)
print(f"  F2P: {len(f2p)}  P2P: {len(p2p)}")
