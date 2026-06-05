#!/usr/bin/env python3
"""pro_untyped.py — the UNTYPED arm for SWE-bench Pro: the clean single-factor ablation.

The primary ablation of docs/PREREGISTRATION-untyped-ablation.md (§4.5b, the typed-mode
on/off / blind-blind on / gate on row of the paper's §limitations per-factor plan). It is the
FULL headline pipeline — same Sonnet generator, same GPT-5.5 codex challenger, same deterministic
gate, same outer loop — with ONE factor removed: the methodeutic typing of the `inquire` stage.

  TYPED headline `recon`  : the /recon skill (skills/recon/skill.md) — Peircean abduction/
                            deduction/induction, a typed hypothesis graph (typed nodes, kill
                            predicates, credence-by-mode).
  UNTYPED `untyped_recon` : the /ask skill (skills/ask/skill.md) — SAME GOAL (find the source
                            root cause, hand a fix-plan to craft, same handoff shape), WITHOUT
                            the applied epistemology: no mode typing, no typed graph, no kill
                            predicates, no confidence-by-mode. Just find the problem.

The single varied factor is **the injected skill**: `untyped_recon` mirrors rung5.recon's adapter
verbatim and injects ASK_SKILL where recon injects RECON_SKILL. Everything else is the FROZEN
harness, imported verbatim: `craft` (codex volley) and `audit` from rung5_driver; `pro_setup` /
`install_gate` / `pro_capture` / `official_grade` from pro_pilot. craft consumes the handoff as an
opaque string, so one skill file is the whole ablation. If p_untyped < p_typed (frozen
`run.jsonl`), the gap Δ_typing = p_typed − p_untyped is the methodeutic's contribution — the
proof that the reasoning is encoded in the typing, not just the surrounding harness.

  driver/pro_untyped.py <task.json> <instance_id>            # real run (spends Sonnet + codex)
  driver/pro_untyped.py <task.json> <instance_id> --selftest # $0 gate check (delegates to pilot)
"""
import json, sys, pathlib
import rung5_driver as r5
import pro_pilot as pp
from rung5_driver import ssh, log, claude, craft, audit, RECON_CAP, MAX_OUTER

HERE = pp.HERE

# The untyped counterpart to RECON_SKILL (skills/recon/skill.md). Loaded and injected the SAME
# way the frozen harness injects the recon skill — so the entire ablation is one skill file
# swapped: recon/skill.md (typed Peircean inquiry) -> ask/skill.md (same goal, no epistemology).
ASK_SKILL = (pathlib.Path(__file__).resolve().parent.parent / "skills" / "ask" / "skill.md").read_text()


def untyped_recon(inst, box, gate, hgraph, kill_report, depth):
    """inquire's GOAL via the /ask skill, without the applied epistemology. Same signature and
    contract as rung5.recon (returns (handoff, fixed_point)); the adapter mirrors recon's
    verbatim — the ONLY change is the injected skill (ASK_SKILL vs RECON_SKILL) and its name."""
    iid = inst["instance_id"]; tag = f"untyped_recon_{iid.replace('/','_')}_d{depth}"
    added = "\n".join(l[1:] for l in inst["test_patch"].splitlines()
                      if l.startswith("+") and not l.startswith("+++"))
    testfiles = [l[6:] for l in inst["test_patch"].splitlines() if l.startswith("+++ b/")]
    kr = (f"\nPRIOR FIX FAILED (prior diagnosis failed — treat as a fresh start; do NOT "
          f"re-propose the failed root cause):\n{kill_report}\n" if kill_report else "")
    adapter = (
        f"You will follow the /ask skill below. Diagnose from the code alone and print "
        f"your handoff to stdout starting `# Diagnosis:`.\n\n"
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
        f"\n===================== THE /ask SKILL =====================\n{ASK_SKILL}\n"
    )
    out, dt, _to = claude(adapter, HERE / f"r4_cwd_{tag}", tag, timeout=RECON_CAP)
    fixed_point = "FIXED POINT" in out.upper()
    log({"instance": iid, "stage": "untyped_recon", "depth": depth, "wall_s": round(dt),
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
    log({"instance": iid, "stage": "untyped_start", "bench": "pro"})
    s = pp.pro_setup(inst)
    if not s: print("setup failed"); return
    cid, root = s
    box, gate = pp.install_gate(inst, cid, root)
    failbase = pp.run_gate(gate)
    tag = iid.replace("/", "_")
    (HERE / f"untyped_failbase_{tag}.txt").write_text(failbase)
    hgraph = str(HERE / f"untyped_notes_{tag}.md"); pathlib.Path(hgraph).write_text(f"# Untyped: {iid}\n")

    # IDENTICAL outer loop to pro_pilot.main — the only swap is recon -> untyped_recon.
    verdict, route, kill, handoff, prev = "UNKNOWN", "recon", None, None, None
    for depth in range(MAX_OUTER):
        if route == "recon" or handoff is None:
            handoff, fp = untyped_recon(inst, box, gate, hgraph, kill, depth)
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
    log({"instance": iid, "stage": "untyped_done", "agent_verdict": verdict,
         "official_resolved": resolved, "patch_bytes": len(src)})
    print(f"\n=== UNTYPED {iid} ===\n  agent_verdict: {verdict}\n  patch_bytes: {len(src)}"
          f"\n  gate(final): {'GREEN' if 'ALL F2P PASSED' in final_gate else 'RED'}"
          f"\n  OFFICIAL RESOLVED: {resolved}")


if __name__ == "__main__":
    main()
