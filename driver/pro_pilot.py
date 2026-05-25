#!/usr/bin/env python3
"""Pilot driver for SWE-bench Pro (PUBLIC set only).

Reuses rung5's recon/craft/audit/claude/capture loop verbatim (they take box+gate as
opaque helpers) and supplies the Pro-specific container setup + gate. Runs LOCALLY on
the Mac under linux/amd64 emulation (rung5.ssh already localizes `sudo docker`).

  driver/pro_pilot.py <task.json> <instance_id>            # real pilot (spends tokens)
  driver/pro_pilot.py <task.json> <instance_id> --selftest # gate check, $0 tokens:
        fail-on-base must be RED (F2P fail) and gold patch must be GREEN (F2P pass)

LEGALITY (private Pro): the F2P-reading gate below is the PUBLIC-mode stopping signal and
is legitimate only because public tests are visible. On the held-out private set the
FAIL_TO_PASS verdict must NEVER be a stopping signal — that path is a separate one-shot
blind submission gated on PASS_TO_PASS / repo suite / budget. Do not reuse this gate on
private. (See PRO_PORT.md "Blind mode".)
"""
import json, sys, pathlib, shlex
import rung5_driver as r5
from rung5_driver import ssh, log, claude, recon, craft, audit, capture_patch, _strip_test_blocks

WORKSPACE = "/workspace"
# Telemetry artifacts land in the self-descriptive runs/dev/ (gitignored, no-credit), not the
# shared driver tmp. Redirect the driver's output dir for the whole module so recon/craft/audit
# (which use rung5.HERE) and our own writes co-locate there.
r5.HERE = pathlib.Path(__file__).resolve().parent.parent / "runs" / "dev"
r5.HERE.mkdir(parents=True, exist_ok=True)
HERE = r5.HERE


def restore_cmd(inst):
    # The gold-test restoration is the LAST line of before_repo_set_cmd (the grader uses the
    # same reduction). It's `git checkout <instance_commit> -- <test_files>` — touches only
    # test files, so it never clobbers the agent's source edits. This IS the source-only gate.
    return inst["before_repo_set_cmd"].strip().splitlines()[-1].strip()


def pro_setup(inst):
    iid = inst["instance_id"]; img = inst["image_name"]; root = inst.get("repo_dir", "/app")
    ssh(f"sudo docker pull {img} 2>&1 | tail -1", timeout=2400)
    # Pro images have ENTRYPOINT=[/bin/bash], so `... sleep infinity` would run `bash sleep`
    # and exit instantly. Override the entrypoint to keep the container alive.
    cid = ssh(f"sudo docker run -d --entrypoint sleep {img} infinity").stdout.strip()
    if not cid or len(cid) < 12:
        log({"instance": iid, "stage": "setup", "msg": f"run failed: {cid[:80]}"}); return None
    # clean base + restore gold tests so the agent can READ the failing tests during recon
    base = inst["base_commit"]
    ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && git reset --hard {base} -q && "
        f"git checkout {base} -q 2>/dev/null; {restore_cmd(inst)} 2>/dev/null; echo OK'")
    # write run_script.sh + parser.py + the F2P list into /workspace in the container
    ssh(f"sudo docker exec {cid} bash -lc 'mkdir -p {WORKSPACE}'")
    for name, content in (("run_script.sh", inst["run_script"]), ("parser.py", inst["parser_script"]),
                          ("f2p.json", json.dumps(inst["fail_to_pass"]))):
        ssh(f"cat > /tmp/_pf && sudo docker cp /tmp/_pf {cid}:{WORKSPACE}/{name}", inp=content)
    return cid, root


def install_gate(inst, cid, root):
    """Gate (PUBLIC mode): restore gold tests, run the instance run_script, parse with the
    instance parser, print an F2P pass/fail summary the agent iterates against. Source edits
    in the live tree are preserved; only test files are reset to gold."""
    files = ",".join(inst["selected_test_files"])  # grader passes comma-joined as one token
    summary = (
        "import json;o=json.load(open('/workspace/output.json'));"
        "f2p=set(json.load(open('/workspace/f2p.json')));"
        "st={t['name']:t['status'] for t in o.get('tests',[])};"
        "pas=[t for t in f2p if st.get(t)=='PASSED'];fail=[t for t in f2p if st.get(t)!='PASSED'];"
        "print('=== GATE F2P %d/%d PASSED ==='%(len(pas),len(f2p)));"
        "print('FAILING:',fail) if fail else print('ALL F2P PASSED');"
    )
    g = (f"cd {root} && {restore_cmd(inst)} 2>/dev/null; "
         f"bash {WORKSPACE}/run_script.sh {shlex.quote(files)} > {WORKSPACE}/stdout.log 2> {WORKSPACE}/stderr.log; "
         f"python {WORKSPACE}/parser.py {WORKSPACE}/stdout.log {WORKSPACE}/stderr.log {WORKSPACE}/output.json; "
         f"python -c {shlex.quote(summary)}")
    tag = inst["instance_id"].replace("/", "_")
    gate = f"/tmp/gate-pro-{tag}"; box = f"/tmp/box-pro-{tag}"
    # bash -c, NOT -lc: a login shell sources /etc/profile which RESETS PATH to a bare default,
    # dropping the image's baked /go/bin:/usr/local/go/bin (and GOPATH etc. in Config.Env). That
    # made `go` vanish in the gate → 0 tests run → false GREEN=False on every Go instance. The
    # official grader uses the image env (non-login); we must match it. Python survived only
    # because /usr/bin is on the reset PATH too. (Pro env_activate is empty — no conda needs -l.)
    pathlib.Path(gate).write_text(f"#!/bin/bash\ndocker exec {cid} bash -c {shlex.quote(g)} 2>&1 | tail -150\n")
    bx = (f"printf '%s' \"$*\" | docker exec -i {cid} bash -c 'cat >/tmp/_bc' && "
          f"docker exec {cid} bash -c 'cd {root} && bash /tmp/_bc'")
    pathlib.Path(box).write_text(f"#!/bin/bash\n{bx}\n")
    import subprocess; subprocess.run(["chmod", "+x", gate, box])
    return box, gate


def run_gate(gate):
    return ssh(f"bash {gate}", timeout=1800).stdout


def selftest(inst):
    """$0-token gate validation: RED on base, GREEN on gold patch."""
    from datasets import load_dataset
    s = pro_setup(inst)
    if not s: print("SELFTEST: setup failed"); return
    cid, root = s
    box, gate = install_gate(inst, cid, root)
    base_out = run_gate(gate)
    red_ok = "ALL F2P PASSED" not in base_out
    print(f"\n--- fail-on-base gate (expect RED) ---\n{base_out.strip()[-400:]}\n--> RED={red_ok}")
    # apply gold patch (fetched from dataset by id — never written into the task)
    ds = load_dataset("ScaleAI/SWE-bench_Pro", split="test")
    gold = next(x for x in ds if x["instance_id"] == inst["instance_id"])["patch"]
    ssh(f"cat > /tmp/_gold.patch && sudo docker cp /tmp/_gold.patch {cid}:/tmp/_gold.patch", inp=gold)
    ap = ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && git apply -v /tmp/_gold.patch && echo APPLIED'")
    print(f"gold apply: {'APPLIED' if 'APPLIED' in ap.stdout else 'FAILED '+ap.stderr[-200:]}")
    gold_out = run_gate(gate)
    green_ok = "ALL F2P PASSED" in gold_out
    print(f"\n--- gold-patch gate (expect GREEN) ---\n{gold_out.strip()[-400:]}\n--> GREEN={green_ok}")
    ssh(f"sudo docker kill {cid} 2>/dev/null")
    print(f"\n=== SELFTEST {inst['instance_id']}: {'PASS' if (red_ok and green_ok) else 'FAIL'} "
          f"(red={red_ok} green={green_ok}) ===")


def pro_capture(inst, cid, root):
    """Capture the agent's SOURCE-only diff: stage everything, diff vs base (HEAD), drop
    test-file blocks (selected_test_files are gold-locked). Saved as the prediction."""
    ssh(f"sudo docker exec {cid} bash -lc 'cd {root} && git add -A -- . 2>/dev/null; "
        f"git diff --cached HEAD > /tmp/_pred.diff 2>/dev/null; echo OK'")
    diff = ssh(f"sudo docker exec {cid} bash -lc 'cat /tmp/_pred.diff'").stdout
    # Use the GOLD test PATHS from the test_patch headers (real paths), not selected_test_files
    # (which are test FUNCTION names for Go/Ginkgo and never match). Convention catches the rest.
    gold_testpaths = {l[6:] for l in inst.get("test_patch", "").splitlines() if l.startswith("+++ b/")}
    src = _strip_test_blocks(diff, gold_testpaths)
    tag = inst["instance_id"].replace("/", "_")
    (HERE / f"pro_patch_{tag}.diff").write_text(src)
    return src


def official_grade(inst, src):
    """Authoritative verdict: re-grade the captured source-only diff with the Pro evaluator
    on a FRESH container (gate == grader by construction). PUBLIC set only."""
    import subprocess, os
    repo = os.environ.get("SWEAP_OS_REPO", "/tmp/swebench-pro-os")
    iid = inst["instance_id"]; tag = iid.replace("/", "_")
    samp = HERE / f"pro_sample_{tag}.jsonl"; pred = HERE / f"pro_pred_{tag}.json"
    row = {k: inst[k] for k in inst if k not in ("run_script", "parser_script")}
    row["fail_to_pass"] = json.dumps(inst["fail_to_pass"]); row["pass_to_pass"] = json.dumps(inst["pass_to_pass"])
    row["selected_test_files_to_run"] = json.dumps(inst["selected_test_files"])
    import pandas as pd; pd.DataFrame([row]).to_json(samp, orient="records", lines=True)
    json.dump([{"instance_id": iid, "patch": src, "prefix": ""}], open(pred, "w"))
    out = HERE / f"pro_grade_{tag}"
    subprocess.run([sys.executable, "swe_bench_pro_eval.py", "--raw_sample_path", str(samp),
                    "--patch_path", str(pred), "--output_dir", str(out), "--scripts_dir", "run_scripts",
                    "--num_workers", "1", "--use_local_docker", "--dockerhub_username",
                    os.environ.get("DOCKERHUB_USER", "jefzda"), "--redo"], cwd=repo)
    res = out / "eval_results.json"
    return json.load(open(res)).get(iid) if res.exists() else None


def main():
    task_path, iid = sys.argv[1], sys.argv[2]
    inst = next(t for t in json.load(open(task_path)) if t["instance_id"] == iid)
    assert inst.get("bench") == "pro", "not a Pro task (BENCH=pro make_task)"
    # recon/craft/audit read uppercase keys + test_patch; alias from the Pro task
    inst.setdefault("FAIL_TO_PASS", inst["fail_to_pass"]); inst.setdefault("PASS_TO_PASS", inst["pass_to_pass"])
    if "--selftest" in sys.argv:
        selftest(inst); return

    HERE.mkdir(parents=True, exist_ok=True)
    log({"instance": iid, "stage": "pilot_start", "bench": "pro"})
    s = pro_setup(inst)
    if not s: print("setup failed"); return
    cid, root = s
    box, gate = install_gate(inst, cid, root)
    failbase = run_gate(gate)                       # baseline (all F2P fail on base)
    tag = iid.replace("/", "_")
    (HERE / f"pro_failbase_{tag}.txt").write_text(failbase)
    # NOTE: network left ON for the pilot (some repos need deps at test time; offline-per-repo
    # is still being mapped). The bench is contamination-acknowledged (LIMITATIONS).
    hgraph = str(HERE / f"pro_hgraph_{tag}.md"); pathlib.Path(hgraph).write_text(f"# Pilot: {iid}\n")

    verdict, route, kill, handoff, prev = "UNKNOWN", "recon", None, None, None
    for depth in range(r5.MAX_OUTER):
        if route == "recon" or handoff is None:
            handoff, fp = recon(inst, box, gate, hgraph, kill, depth)
            if fp and depth > 0: break
        craft_out, redo, timed_out = craft(inst, box, gate, hgraph, handoff, kill, depth)
        if timed_out: verdict = "CRAFT_TIMEOUT"; break
        if redo and depth < r5.MAX_OUTER - 1:
            kill = f"craft could not implement the diagnosis:\n{craft_out[-2000:]}"; route = "recon"; prev = None; continue
        audit_out, verdict, route = audit(inst, box, gate, hgraph, failbase, depth)
        if verdict == "RESOLVED" or route == "none": break
        if route == "craft" and prev == "craft":
            route = "recon"; kill = "NARROW MODE STALLED — re-diagnose differently.\n" + audit_out[-1800:]
        elif depth < r5.MAX_OUTER - 1: kill = audit_out[-2500:]
        prev = route

    src = pro_capture(inst, cid, root)
    final_gate = run_gate(gate)
    ssh(f"sudo docker kill {cid} 2>/dev/null")
    resolved = official_grade(inst, src) if src.strip() else None
    log({"instance": iid, "stage": "pilot_done", "agent_verdict": verdict,
         "official_resolved": resolved, "patch_bytes": len(src)})
    print(f"\n=== PILOT {iid} ===\n  agent_verdict: {verdict}\n  patch_bytes: {len(src)}"
          f"\n  gate(final): {'GREEN' if 'ALL F2P PASSED' in final_gate else 'RED'}"
          f"\n  OFFICIAL RESOLVED: {resolved}")


if __name__ == "__main__":
    main()
