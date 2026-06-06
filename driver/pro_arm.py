#!/usr/bin/env python3
"""pro_arm.py — parameterized framing-prose arm for the methodeutic-content ablation.

The G/T arms of docs/PREREGISTRATION-methodeutic-content-ablation.md. Same template as
pro_untyped.py: the FULL headline pipeline (same Sonnet generator, same GPT-5.5 codex
challenger, same deterministic gate, same outer loop, full-execution box) with ONE factor
varied — the diagnosis skill prose injected at the recon stage. Everything downstream
(craft, audit, setup, gate, capture, official_grade) is the FROZEN harness, imported verbatim.

  ARM_NAME=generic ARM_SKILL=skills/generic/skill.md  -> G: steelman generic rigor (codex-authored)
  ARM_NAME=minimal ARM_SKILL=skills/minimal/skill.md  -> T: task-only floor

M (methodeutic) is the frozen /recon baseline in runs/scored/run.jsonl — not re-run here.
The adapter wrapper is held NEUTRAL and identical across G and T (working-notes phrasing, same
as pro_untyped), so the only methodeutic vocabulary anywhere in G/T is whatever the skill itself
carries — which the parity check confirms is zero. See prereg §6 + §11 (wrapper disclosure).

  ARM_NAME=generic ARM_SKILL=skills/generic/skill.md driver/pro_arm.py <task.json> <iid>
  driver/pro_arm.py <task.json> <iid> --selftest   # $0 gate check (delegates to pilot)
"""
import json, os, sys, pathlib
import rung5_driver as r5
import pro_pilot as pp
from rung5_driver import ssh, log, claude, craft, audit, RECON_CAP, MAX_OUTER

HERE = pp.HERE

ARM_NAME = os.environ.get("ARM_NAME", "generic")
ARM_SKILL_PATH = pathlib.Path(__file__).resolve().parent.parent / os.environ.get(
    "ARM_SKILL", f"skills/{ARM_NAME}/skill.md")
ARM_SKILL = ARM_SKILL_PATH.read_text()


def arm_recon(inst, box, gate, hgraph, kill_report, depth):
    """recon's GOAL via the ARM skill. Same signature/contract as rung5.recon (returns
    (handoff, fixed_point)); the adapter mirrors recon's verbatim except (a) the injected skill
    is ARM_SKILL and (b) the wrapper vocabulary is neutral (working notes, not hypothesis nodes),
    so no methodeutic framing leaks into the non-methodeutic arms via the wrapper."""
    iid = inst["instance_id"]; tag = f"{ARM_NAME}_recon_{iid.replace('/','_')}_d{depth}"
    added = "\n".join(l[1:] for l in inst["test_patch"].splitlines()
                      if l.startswith("+") and not l.startswith("+++"))
    testfiles = [l[6:] for l in inst["test_patch"].splitlines() if l.startswith("+++ b/")]
    kr = (f"\nPRIOR FIX FAILED (prior diagnosis failed — treat as a fresh start; do NOT "
          f"re-propose the failed root cause):\n{kill_report}\n" if kill_report else "")
    adapter = (
        f"You will follow the /{ARM_NAME} skill below. Diagnose from the code alone and print "
        f"your handoff to stdout starting `# Recon:`.\n\n"
        f"ENVIRONMENT:\n"
        f"- Code is in an offline container. Run ALL reads via: `{box} '<cmd>'` "
        f"(it already cd's to repo root — do NOT prepend cd). No internet, no gh, no codex.\n"
        f"- Run the failing tests: `{gate}`\n"
        f"- The fix must be SOURCE-ONLY: test files are gold-locked (the gate restores them "
        f"before every run). Never hand off 'edit/weaken the test' as a fix — diagnose the "
        f"source cause that makes the GOLD tests pass.\n"
        f"- Jot working notes to: {hgraph} (never truncate).\n"
        f"- Failing tests live in: {testfiles}\n\n"
        f"FAIL_TO_PASS (must pass): {str(inst['FAIL_TO_PASS'])[:600]}\n\n"
        f"PROBLEM:\n{inst['problem_statement'][:4000]}\n\n"
        f"ADDED FAILING TESTS:\n{added[:2500]}\n"
        f"{kr}"
        f"\n===================== THE /{ARM_NAME} SKILL =====================\n{ARM_SKILL}\n"
    )
    out, dt, _to = claude(adapter, HERE / f"r4_cwd_{tag}", tag, timeout=RECON_CAP)
    fixed_point = "FIXED POINT" in out.upper()
    log({"instance": iid, "stage": f"{ARM_NAME}_recon", "depth": depth, "wall_s": round(dt),
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
    log({"instance": iid, "stage": f"{ARM_NAME}_start", "bench": "pro", "skill": str(ARM_SKILL_PATH)})
    s = pp.pro_setup(inst)
    if not s: print("setup failed"); return
    cid, root = s
    box, gate = pp.install_gate(inst, cid, root)
    failbase = pp.run_gate(gate)
    tag = iid.replace("/", "_")
    (HERE / f"{ARM_NAME}_failbase_{tag}.txt").write_text(failbase)
    hgraph = str(HERE / f"{ARM_NAME}_notes_{tag}.md"); pathlib.Path(hgraph).write_text(f"# {ARM_NAME}: {iid}\n")

    # RECON_ONLY: diagnosis-quality sweep (diag_oracle scores the handoff vs gold). Skip the
    # craft/audit outer loop entirely — we want the recon handoff, not a verdict. Big speedup.
    if os.environ.get("RECON_ONLY"):
        handoff, _ = arm_recon(inst, box, gate, hgraph, None, 0)
        out = HERE / f"{ARM_NAME}_handoff_{tag}.txt"; out.write_text(handoff)
        ssh(f"sudo docker kill {cid} 2>/dev/null")
        log({"instance": iid, "stage": f"{ARM_NAME}_recononly_done", "handoff": str(out),
             "handoff_bytes": len(handoff)})
        print(f"\n=== {ARM_NAME.upper()} RECON-ONLY {iid} ===\n  handoff: {out} ({len(handoff)} bytes)")
        return

    # IDENTICAL outer loop to pro_pilot.main — the only swap is recon -> arm_recon.
    verdict, route, kill, handoff, prev = "UNKNOWN", "recon", None, None, None
    for depth in range(MAX_OUTER):
        if route == "recon" or handoff is None:
            handoff, fp = arm_recon(inst, box, gate, hgraph, kill, depth)
            if fp and depth > 0: break
        craft_out, redo, timed_out = craft(inst, box, gate, hgraph, handoff, kill, depth)
        if timed_out: verdict = "CRAFT_TIMEOUT"; break
        if redo and depth < MAX_OUTER - 1:
            kill = f"craft could not implement the diagnosis:\n{craft_out[-2000:]}"; route = "recon"; prev = None; continue
        audit_out, verdict, route = audit(inst, box, gate, hgraph, failbase, depth)
        if verdict == "RESOLVED" or route == "none": break
        if route == "craft" and prev == "craft":
            route = "recon"; kill = "NARROW MODE STALLED — re-diagnose differently.\n" + audit_out[-1800:]
        elif depth < MAX_OUTER - 1: kill = audit_out[-2500:]
        prev = route

    src = pp.pro_capture(inst, cid, root)
    final_gate = pp.run_gate(gate)
    ssh(f"sudo docker kill {cid} 2>/dev/null")
    resolved = pp.official_grade(inst, src) if src.strip() else None
    log({"instance": iid, "stage": f"{ARM_NAME}_done", "agent_verdict": verdict,
         "official_resolved": resolved, "patch_bytes": len(src)})
    print(f"\n=== {ARM_NAME.upper()} {iid} ===\n  agent_verdict: {verdict}\n  patch_bytes: {len(src)}"
          f"\n  gate(final): {'GREEN' if 'ALL F2P PASSED' in final_gate else 'RED'}"
          f"\n  OFFICIAL RESOLVED: {resolved}")


if __name__ == "__main__":
    main()
