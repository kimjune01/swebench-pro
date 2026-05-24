#!/usr/bin/env python3
"""testify.py — bench-scoped re-grade of a captured prediction (the attestation
hash-as-precondition contract from PRO_PORT.md, lever #3). Named `testify` to avoid colliding
with the global `/attest` skill; this is the SWE-bench tool, deterministic code, not an LLM
skill.

Applies a SERIALIZED source-only prediction to a CLEAN base container, runs the pinned
tests, and derives the verdict from swebench's OWN log parser — so the local verdict agrees
with the official grader by construction. Emits a structured verdict + a sha256 of the
prediction (the precondition: no hash, no submission). One-shot; tears the container down.

This is NOT a fresh solve. It re-grades an existing committed artifact. Conversions on the
16 not-won are telemetry, not Verified wins (no-credit rule). Do not route output into any
results/ tree.

Usage:
  driver/testify.py <instance_id> <prediction.diff> [--keep]

  e.g. driver/testify.py pytest-dev__pytest-5787 \
         ../swebench-verified/results/pytest-dev__pytest-5787/20260523T213600Z/patch.diff

Mac/OrbStack: x86_64 images run under --platform linux/amd64.
Requires the Verified venv (swebench + datasets): ../swebench-verified/.venv.
"""
import json, sys, re, hashlib, subprocess, pathlib, argparse
from datasets import load_dataset
from swebench.harness.test_spec.test_spec import make_test_spec
from swebench.harness.grading import (
    get_logs_eval, get_eval_tests_report, get_resolution_status,
)
from swebench.harness.constants import (
    START_TEST_OUTPUT, END_TEST_OUTPUT, ResolvedStatus,
)

REPO = pathlib.Path(__file__).resolve().parent.parent
PLATFORM = "linux/amd64"
ROOT = "/testbed"
ENV_ACT = "source /opt/miniconda3/bin/activate testbed"
DATASET = "princeton-nlp/SWE-bench_Verified"


def sh(*args, **kw):
    return subprocess.run(args, capture_output=True, text=True, **kw)


def dexec(cid, cmd, timeout=1800):
    return sh("docker", "exec", cid, "bash", "-lc", cmd, timeout=timeout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instance_id")
    ap.add_argument("prediction")
    ap.add_argument("--keep", action="store_true", help="don't tear the container down")
    a = ap.parse_args()

    pred_path = pathlib.Path(a.prediction)
    pred_bytes = pred_path.read_bytes()
    pred_sha = hashlib.sha256(pred_bytes).hexdigest()

    ds = load_dataset(DATASET, split="test")
    inst = next(r for r in ds if r["instance_id"] == a.instance_id)
    spec = make_test_spec(inst, namespace="swebench")
    img = spec.instance_image_key
    m = re.search(r">>>>> Start Test Output'\n(.*?)\n: '>>>>> End Test Output",
                  spec.eval_script, re.S)
    test_cmd = m.group(1).strip() if m else "python -m pytest -rA"
    f2p = json.loads(inst["FAIL_TO_PASS"]); p2p = json.loads(inst["PASS_TO_PASS"])

    out = REPO / "iso" / a.instance_id; out.mkdir(parents=True, exist_ok=True)
    log_fp = str(out / "testify_eval.log")

    print(f">> testify {a.instance_id}  pred sha256={pred_sha[:16]}…")
    print(f">> pull {img} (--platform {PLATFORM})")
    sh("docker", "pull", "--platform", PLATFORM, img, timeout=2400)
    cid = sh("docker", "run", "-d", "--platform", PLATFORM, img, "sleep", "infinity").stdout.strip()
    if len(cid) < 12:
        print("ERRORED: container did not start"); sys.exit(2)

    try:
        # gold test patch, staged off-tree and committed (no tp.patch hunk leaks into state)
        p = sh("docker", "exec", "-i", cid, "bash", "-c", "cat > /tmp/tp.patch",
               input=inst["test_patch"])
        ap_tp = dexec(cid, f"cd {ROOT} && git apply /tmp/tp.patch && "
                           f"git -c user.email=a@x -c user.name=a add -A && "
                           f"git -c user.email=a@x -c user.name=a commit -q -m testpatch && echo OK")
        if "OK" not in ap_tp.stdout:
            print("ERRORED: test patch apply failed\n" + ap_tp.stdout + ap_tp.stderr); sys.exit(2)

        # the captured source-only prediction, applied to the clean base
        sh("docker", "exec", "-i", cid, "bash", "-c", "cat > /tmp/pred.patch",
           input=pred_bytes.decode("utf-8", "replace"))
        ap_pred = dexec(cid, f"cd {ROOT} && git apply /tmp/pred.patch && echo OK")
        pred_applied = "OK" in ap_pred.stdout
        if not pred_applied:
            # REJECTED on apply — the official harness would also fail to apply. Honest red.
            verdict = {"instance_id": a.instance_id, "prediction_sha256": pred_sha,
                       "decision": "rejected", "reason": "prediction did not apply on clean base",
                       "resolved": False, "apply_stderr": ap_pred.stderr[-500:]}
            (out / "testify.json").write_text(json.dumps(verdict, indent=2))
            print(json.dumps(verdict, indent=2)); return

        # run pinned tests, wrap output in the official markers, parse with swebench's parser
        r = dexec(cid, f"{ENV_ACT} 2>/dev/null; cd {ROOT}; "
                       f"echo '{START_TEST_OUTPUT}'; {test_cmd}; echo '{END_TEST_OUTPUT}'")
        pathlib.Path(log_fp).write_text(r.stdout + r.stderr)

        status_map, found = get_logs_eval(spec, log_fp)
        report = get_eval_tests_report(status_map, {"FAIL_TO_PASS": f2p, "PASS_TO_PASS": p2p})
        resolution = get_resolution_status(report)
        resolved = resolution == ResolvedStatus.FULL.value

        verdict = {
            "instance_id": a.instance_id,
            "prediction_sha256": pred_sha,
            "decision": "decided",
            "markers_found": found,
            "resolution": resolution,
            "resolved": resolved,
            "f2p_failures": report["FAIL_TO_PASS"]["failure"],
            "p2p_failures": report["PASS_TO_PASS"]["failure"],
            "f2p_pass": len(report["FAIL_TO_PASS"]["success"]),
            "p2p_pass": len(report["PASS_TO_PASS"]["success"]),
        }
        (out / "testify.json").write_text(json.dumps(verdict, indent=2))
        print(json.dumps({k: verdict[k] for k in
              ("resolved", "resolution", "f2p_failures", "p2p_failures",
               "f2p_pass", "p2p_pass", "prediction_sha256")}, indent=2))
    finally:
        if not a.keep:
            sh("docker", "kill", cid)
            print(f">> torn down {cid[:12]}")
        else:
            print(f">> container kept: {cid}")


if __name__ == "__main__":
    main()
