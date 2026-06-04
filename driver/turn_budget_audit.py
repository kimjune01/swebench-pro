#!/usr/bin/env python3
"""turn_budget_audit.py — does the harness win by spending more turns, or fewer?

A skeptic's check, and evidence bearing on the budget confound. The bare baseline
on the public Scale board runs SWE-Agent with a 250-turn cap and resolves ~43.6%
(Sonnet 4.5); this harness resolves 95.3% on the same model. The standing objection
is that the 31-to-37-point lift could be turn budget alone: the harness simply gets
more steps. This script grades that objection against the committed generator
trajectories rather than asserting it away — it counts how many actions the harness
actually spent per winning instance and compares the distribution to the baseline's
cap.

ACTION UNIT. The baseline's "turn" is one ReAct step: one model call that emits one
action. The closest committed analogue is a `tool_use` block in the generator's
trajectory (one tool call = one action). So the primary metric is **tool-calls per
instance**, summed across the three stages (recon/craft/audit) and every re-entry
pass. Assistant-message count is reported alongside as a looser bound: one Claude
Code assistant message can carry several tool_use blocks, so message-count
understates actions while tool-call-count tracks them. Neither mapping is exact
across scaffolds; both are reported so a reader can pick the comparison they trust.

WHAT IT SHOWS, AND WHAT IT DOES NOT.
  - If wins land well under the baseline's cap, "the lift is just more budget" is
    refuted from receipts: the harness was granted no more headroom than the bare
    baseline already had, and won anyway. That is positive evidence the lever is how
    the actions are organized, not how many are spent.
  - It does NOT isolate the typed-mode structure from the other bundled factors
    (thinking-on, cross-family critique). It closes one confound (budget), not all.
  - The harness spreads its actions across three FRESH stage-contexts (recon, craft,
    audit), while the baseline gets one context of 250 turns. That split IS the
    structure under test, not a confound to subtract; the per-stage breakdown is
    reported so the reader sees where the budget goes.
  - Only the GENERATOR (claude: inquire/implement/attest) is counted. The cross-
    family challenger (codex) runs a separate, small budget (~8% of per-instance
    cost, §cost-profile) and is out of scope here: the "budget alone" objection is
    about the generator that does the solving.

COVERAGE. The denominator is WIN rows in the run ledger, not "trajectories we
happened to find." A win whose per-pass trajectory predates capture is reported as
`missing_trajectory`, never silently dropped, so "counted N of M wins" is explicit
(this is the same ~46-win capture gap noted in the paper's results section).

TRAJECTORY PROVENANCE. Generator trajectories live under artifacts/<box>/claude/,
one directory per stage-pass, named ...cwd-<stage>-instance-<id>-v<sha>-d<depth>/.
The directory name carries stage and re-entry depth; that is the whole parse. Each
row records the per-stage, per-depth counts so a third party can re-extract one
instance's trajectories and recount any single number without rerunning the bench.

Usage:
    # straight from the frozen tarball (py>=3.14 reads .zst):
    python driver/turn_budget_audit.py \
        --tarball runs/scored/artifacts.tar.zst \
        --run runs/scored/run.jsonl \
        --out runs/scored/turn_budget.jsonl

    # or from an already-extracted tree:
    python driver/turn_budget_audit.py \
        --artifacts-dir /tmp/artifacts \
        --run runs/scored/run.jsonl --out runs/scored/turn_budget.jsonl
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import statistics
import sys
import tarfile

# Stage-pass directory: ...cwd-<stage>-instance-<id...>-d<depth>. The id segment
# still carries the -v<sha> version suffix; canon_id() normalizes that away.
STAGE_DIR = re.compile(r"cwd-(recon|craft|audit)-instance-(.+)-d(\d+)$")
STAGES = ("recon", "craft", "audit")


def canon_id(s: str) -> str:
    """Canonical instance key shared by ledger ids and trajectory paths.

    Ledger:  instance_ansible__ansible-9759e0ca...                 (__ separator)
    Path:    instance-ansible--ansible-9759e0ca...-v<40hex>-d0     (-- separator, version, depth)
    Both collapse to ansible-ansible-9759e0ca... so the two surfaces join without
    reconstructing org/repo structure.
    """
    s = re.sub(r"^instance[-_]", "", s)
    s = re.sub(r"-d\d+$", "", s)                 # strip re-entry depth (paths only)
    s = re.sub(r"-v(?:[0-9a-f]{40}|nan)$", "", s)  # strip version suffix (paths only)
    return s.replace("__", "-").replace("--", "-")


def count_trajectory(raw: bytes) -> tuple[int, int]:
    """(tool_calls, assistant_turns) in one generator trajectory jsonl."""
    tool_calls = turns = 0
    for line in raw.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("type") != "assistant":
            continue
        turns += 1
        content = d.get("message", {}).get("content", [])
        if isinstance(content, list):
            tool_calls += sum(
                1 for b in content if isinstance(b, dict) and b.get("type") == "tool_use"
            )
    return tool_calls, turns


def iter_generator_files(tarball, artifacts_dir):
    """Yield (stage, canon_instance, depth, raw_bytes) for each claude trajectory."""
    if artifacts_dir:
        for p in pathlib.Path(artifacts_dir).rglob("*.jsonl"):
            if "/claude/" not in p.as_posix():
                continue
            m = STAGE_DIR.search(p.parent.name)
            if not m:
                continue
            yield m.group(1), canon_id(m.group(2)), int(m.group(3)), p.read_bytes()
    elif tarball:
        with tarfile.open(tarball, mode="r:*") as tf:
            for member in tf:
                if not (member.isfile() and member.name.endswith(".jsonl")
                        and "/claude/" in member.name):
                    continue
                parent = member.name.rsplit("/", 2)[-2] if "/" in member.name else ""
                m = STAGE_DIR.search(parent)
                if not m:
                    continue
                f = tf.extractfile(member)
                if f:
                    yield m.group(1), canon_id(m.group(2)), int(m.group(3)), f.read()
    else:
        sys.exit("provide --tarball or --artifacts-dir")


def load_wins(run_jsonl):
    """Ordered unique WIN instance_ids (last-write-wins on state) + duplicate count."""
    state, dupes = {}, 0
    for line in open(run_jsonl):
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        iid = d["instance_id"]
        if iid in state:
            dupes += 1
        state[iid] = d.get("state", "")
    return [i for i, s in state.items() if s == "WIN"], dupes


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tarball")
    ap.add_argument("--artifacts-dir")
    ap.add_argument("--run", required=True, help="run.jsonl ledger; WIN rows are the denominator")
    ap.add_argument("--cap", type=int, default=250,
                    help="baseline turn cap to compare against (Scale board SWE-Agent: 250)")
    ap.add_argument("--out", default="turn_budget.jsonl")
    args = ap.parse_args()

    # Accumulate per canonical instance: stage -> depth -> (tool_calls, turns).
    acc = collections.defaultdict(lambda: collections.defaultdict(dict))
    for stage, inst, depth, raw in iter_generator_files(args.tarball, args.artifacts_dir):
        tc, tu = count_trajectory(raw)
        prev = acc[inst][stage].get(depth, (0, 0))
        acc[inst][stage][depth] = (prev[0] + tc, prev[1] + tu)

    wins, dupes = load_wins(args.run)
    print(f"ledger wins={len(wins)} dupes={dupes} | instances with trajectories={len(acc)} | cap={args.cap}")

    rows = []
    calls_list, turns_list = [], []
    stage_calls = collections.defaultdict(list)
    n_missing = n_reentered = n_under = 0
    for iid in wins:
        key = canon_id(iid)
        stages = acc.get(key)
        if not stages:
            n_missing += 1
            rows.append({"instance_id": iid, "status": "missing_trajectory"})
            continue
        per_stage = {}
        total_calls = total_turns = max_depth = 0
        for s in STAGES:
            depths = stages.get(s, {})
            sc = sum(c for c, _ in depths.values())
            st = sum(t for _, t in depths.values())
            per_stage[s] = {"tool_calls": sc, "turns": st, "passes": len(depths)}
            total_calls += sc
            total_turns += st
            if depths:
                max_depth = max(max_depth, max(depths))
            if s == "craft":
                stage_calls[s].append(sc)
        reentered = max_depth >= 1
        under = total_calls <= args.cap
        n_reentered += reentered
        n_under += under
        calls_list.append(total_calls)
        turns_list.append(total_turns)
        for s in STAGES:
            stage_calls[s].append(per_stage[s]["tool_calls"])
        rows.append({
            "instance_id": iid, "status": "counted",
            "tool_calls": total_calls, "assistant_turns": total_turns,
            "max_depth": max_depth, "reentered": reentered,
            "under_cap": under, "stages": per_stage,
        })

    with open(args.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    n = len(calls_list)
    print(f"\nWINS: {len(wins)} total | counted {n} | missing_trajectory {n_missing}")
    if n:
        sv = sorted(calls_list)
        pct = lambda p: sv[min(n - 1, int(p * n))]
        med = statistics.median
        print(f"\nGENERATOR TOOL-CALLS per winning instance (action units vs {args.cap}-turn cap):")
        print(f"  p10 {pct(.10)}  p25 {pct(.25)}  median {med(calls_list):.0f}  "
              f"p75 {pct(.75)}  p90 {pct(.90)}  max {sv[-1]}  mean {statistics.mean(calls_list):.0f}")
        print(f"  <= cap ({args.cap}): {n_under}/{n} = {100*n_under/n:.1f}%   "
              f"(baseline is GRANTED {args.cap} and resolves ~43.6%)")
        print(f"  assistant turns per instance: median {med(turns_list):.0f} "
              f"(looser bound; one message can carry several tool calls)")
        print(f"  re-entered (depth>=1): {n_reentered}/{n} = {100*n_reentered/n:.1f}%")
        print(f"\n  per-stage median tool-calls/instance: " +
              "  ".join(f"{s} {med(stage_calls[s]):.0f}" for s in STAGES))
        hist = collections.Counter(min(c // 50, 9) for c in calls_list)
        print(f"\n  tool-call histogram (bucket = 50 calls; cap {args.cap} = bucket {args.cap//50}):")
        for k in range(10):
            label = f"{k*50}-{k*50+49}" if k < 9 else "450+"
            bar = "#" * hist.get(k, 0)
            print(f"    {label:>8}: {hist.get(k,0):4d} {bar[:60]}")
    print(f"\nreceipt: {args.out} (one row per win; per-stage/per-depth counts, under_cap flag)")


if __name__ == "__main__":
    main()
