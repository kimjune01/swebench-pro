#!/usr/bin/env python3
"""pro_feynman.py -- the STATIC arm for SWE-bench Pro (prereg-pro-v1-feynman).

ask-feynman = /recon with scoped diagnostic perturbation removed, nothing else. The diagnosis runs
the /ask-feynman skill against a READ-ONLY box (no execution: cat/grep/git log only; interpreters,
test runners, scripts, and writes are refused and logged), and is handed the captured failure output
(the same symptom /recon observes by reproducing). Everything downstream -- craft (codex volley),
audit, capture, official_grade -- is the FROZEN harness, imported verbatim from pro_pilot/rung5.

Baseline (perturb arm) = frozen /recon in runs/scored/run.jsonl; this arm is paired against it.

  driver/pro_feynman.py <task.json> <instance_id>            # real run (spends Sonnet + codex)
  driver/pro_feynman.py <task.json> <instance_id> --selftest # $0 gate check (delegates to pilot)
"""
import json, sys, pathlib, shlex
import rung5_driver as r5
import pro_pilot as pp
from rung5_driver import ssh, log, claude, craft, audit, RECON_CAP, MAX_OUTER

HERE = pp.HERE
FEYNMAN_SKILL = (pathlib.Path(__file__).resolve().parent.parent / "skills" / "ask-feynman" / "skill.md").read_text()

# Execution / perturbation denylist for the read-only diagnosis box. The model has no incentive to
# evade (the skill forbids experiments); this is belt-and-suspenders + an audit trail of any attempt.
DENY = (r"(^|[ ;&|(`$])(python3?|node|nodejs|pytest|ruby|php|perl|npm|npx|yarn|cargo|make|gcc|g\+\+|"
        r"java|javac|dotnet|go run|go test|tox|nox|\./|eval |exec |source |bash -c|sh -c|zsh -c)"
        r"|(>>?[^|&])|(\bsed\b[^|]*-i)|(\btee\b)")


def install_readonly_box(inst, cid, root):
    """A box helper that refuses execution/writes (read-only diagnosis). Logs refusals in-container
    to /tmp/_feynman_refusals so we can audit whether feynman tried to perturb."""
    tag = inst["instance_id"].replace("/", "_")
    box_ro = f"/tmp/box-feynman-{tag}"
    guard = (f"cd {root} && C=$(cat /tmp/_bc); "
             f"if printf '%s' \"$C\" | grep -qE {shlex.quote(DENY)}; then "
             f"printf '%s\\n' \"$C\" >> /tmp/_feynman_refusals; "
             f"echo '[REFUSED: read-only diagnosis arm -- no execution or writes permitted]'; "
             f"else bash /tmp/_bc; fi")
    bx = (f"printf '%s' \"$*\" | docker exec -i {cid} bash -c 'cat >/tmp/_bc' && "
          f"docker exec {cid} bash -c {shlex.quote(guard)}")
    import subprocess
    pathlib.Path(box_ro).write_text(f"#!/bin/bash\n{bx}\n")
    subprocess.run(["chmod", "+x", box_ro])
    return box_ro


def feynman_recon(inst, box_ro, hgraph, failbase, kill_report, depth):
    """/recon's goal via /ask-feynman: static diagnosis, read-only box, the failure symptom provided,
    NO gate. Same signature/contract as rung5.recon (returns (handoff, fixed_point))."""
    iid = inst["instance_id"]; tag = f"feynman_recon_{iid.replace('/','_')}_d{depth}"
    added = "\n".join(l[1:] for l in inst["test_patch"].splitlines()
                      if l.startswith("+") and not l.startswith("+++"))
    testfiles = [l[6:] for l in inst["test_patch"].splitlines() if l.startswith("+++ b/")]
    kr = (f"\nAUDIT KILL REPORT (prior diagnosis failed -- treat as new H0; do NOT re-propose the "
          f"killed root cause):\n{kill_report}\n" if kill_report else "")
    adapter = (
        f"You will follow the /ask-feynman skill below. Diagnose STATICALLY (no execution) and print "
        f"your handoff to stdout starting `# Recon:`.\n\n"
        f"ENVIRONMENT:\n"
        f"- The code is in an offline container, reached READ-ONLY via: `{box_ro} '<cmd>'` "
        f"(it already cd's to repo root -- do NOT prepend cd). Reads/greps/`git log` only; any "
        f"execution (python/node/pytest/go/scripts) or writes are REFUSED. No internet, no gh, no codex.\n"
        f"- You may NOT run the failing tests. The captured failure output (the symptom recon observes "
        f"by reproducing) is below; reason from it.\n"
        f"- The fix must be SOURCE-ONLY: test files are gold-locked. Diagnose the source cause that "
        f"makes the GOLD tests pass.\n"
        f"- Append hypothesis nodes to: {hgraph} (never truncate).\n"
        f"- Failing tests live in: {testfiles}\n\n"
        f"FAIL_TO_PASS (must pass): {str(inst['FAIL_TO_PASS'])[:600]}\n\n"
        f"PROBLEM:\n{inst['problem_statement'][:4000]}\n\n"
        f"CAPTURED FAILURE OUTPUT (the symptom -- you may not re-run it):\n{failbase[-3000:]}\n\n"
        f"ADDED FAILING TESTS:\n{added[:2500]}\n"
        f"{kr}"
        f"\n===================== THE /ask-feynman SKILL =====================\n{FEYNMAN_SKILL}\n"
    )
    out, dt, _to = claude(adapter, HERE / f"r4_cwd_{tag}", tag, timeout=RECON_CAP)
    fixed_point = "FIXED POINT" in out.upper()
    log({"instance": iid, "stage": "feynman_recon", "depth": depth, "wall_s": round(dt),
         "fixed_point": fixed_point, "timed_out": _to})
    return out, fixed_point


def main():
    task_path, iid = sys.argv[1], sys.argv[2]
    inst = next(t for t in json.load(open(task_path)) if t["instance_id"] == iid)
    assert inst.get("bench") == "pro", "not a Pro task (BENCH=pro make_task)"
    inst.setdefault("FAIL_TO_PASS", inst["fail_to_pass"]); inst.setdefault("PASS_TO_PASS", inst["pass_to_pass"])
    if "--selftest" in sys.argv:
        pp.selftest(inst); return

    HERE.mkdir(parents=True, exist_ok=True)
    log({"instance": iid, "stage": "feynman_start", "bench": "pro"})
    s = pp.pro_setup(inst)
    if not s: print("setup failed"); return
    cid, root = s
    box_full, gate = pp.install_gate(inst, cid, root)     # craft/audit get the FULL box + gate
    box_ro = install_readonly_box(inst, cid, root)        # diagnosis gets the READ-ONLY box
    failbase = pp.run_gate(gate)                          # the symptom (provided to feynman; not re-runnable by it)
    tag = iid.replace("/", "_")
    (HERE / f"feynman_failbase_{tag}.txt").write_text(failbase)
    hgraph = str(HERE / f"feynman_hgraph_{tag}.md"); pathlib.Path(hgraph).write_text(f"# Feynman (static): {iid}\n")

    # IDENTICAL outer loop to pro_pilot.main -- only recon -> feynman_recon (read-only box, no gate).
    verdict, route, kill, handoff, prev = "UNKNOWN", "recon", None, None, None
    for depth in range(MAX_OUTER):
        if route == "recon" or handoff is None:
            handoff, fp = feynman_recon(inst, box_ro, hgraph, failbase, kill, depth)
            if fp and depth > 0: break
        craft_out, redo, timed_out = craft(inst, box_full, gate, hgraph, handoff, kill, depth)
        if timed_out: verdict = "CRAFT_TIMEOUT"; break
        if redo and depth < MAX_OUTER - 1:
            kill = f"craft could not implement the diagnosis:\n{craft_out[-2000:]}"; route = "recon"; prev = None; continue
        audit_out, verdict, route = audit(inst, box_full, gate, hgraph, failbase, depth)
        if verdict == "RESOLVED" or route == "none": break
        if route == "craft" and prev == "craft":
            route = "recon"; kill = "NARROW MODE STALLED -- re-diagnose differently.\n" + audit_out[-1800:]
        elif depth < MAX_OUTER - 1: kill = audit_out[-2500:]
        prev = route

    src = pp.pro_capture(inst, cid, root)
    final_gate = pp.run_gate(gate)
    refusals = ssh(f"sudo docker exec {cid} bash -lc 'wc -l < /tmp/_feynman_refusals 2>/dev/null || echo 0'").stdout.strip()
    ssh(f"sudo docker kill {cid} 2>/dev/null")
    resolved = pp.official_grade(inst, src) if src.strip() else None
    log({"instance": iid, "stage": "feynman_done", "agent_verdict": verdict,
         "official_resolved": resolved, "patch_bytes": len(src), "perturbation_refusals": refusals})
    print(f"\n=== FEYNMAN {iid} ===\n  agent_verdict: {verdict}\n  patch_bytes: {len(src)}"
          f"\n  perturbation_refusals(diagnosis): {refusals}"
          f"\n  gate(final): {'GREEN' if 'ALL F2P PASSED' in final_gate else 'RED'}"
          f"\n  OFFICIAL RESOLVED: {resolved}")


if __name__ == "__main__":
    main()
