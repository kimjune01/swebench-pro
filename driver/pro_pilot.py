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
from rung5_driver import ssh, log, claude, recon, craft, audit, capture_patch, _strip_test_blocks, HERE

WORKSPACE = "/workspace"


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
    pathlib.Path(gate).write_text(f"#!/bin/bash\ndocker exec {cid} bash -lc {shlex.quote(g)} 2>&1 | tail -150\n")
    bx = (f"printf '%s' \"$*\" | docker exec -i {cid} bash -c 'cat >/tmp/_bc' && "
          f"docker exec {cid} bash -lc 'cd {root} && bash /tmp/_bc'")
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


def main():
    task_path, iid = sys.argv[1], sys.argv[2]
    inst = next(t for t in json.load(open(task_path)) if t["instance_id"] == iid)
    assert inst.get("bench") == "pro", "not a Pro task (BENCH=pro make_task)"
    # recon/craft/audit read uppercase keys + test_patch; alias from the Pro task
    inst.setdefault("FAIL_TO_PASS", inst["fail_to_pass"]); inst.setdefault("PASS_TO_PASS", inst["pass_to_pass"])
    if "--selftest" in sys.argv:
        selftest(inst); return
    print("real pilot loop not wired in this commit — run --selftest first")


if __name__ == "__main__":
    main()
