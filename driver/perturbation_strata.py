#!/usr/bin/env python3
"""perturbation_strata.py -- pre-registered stratifier for the ask-feynman vs ask-static ablation.

Scores each Pro instance for DECISION-RELEVANT perturbation, read off the FROZEN typed /recon
trajectories (the diagnosis stage's actual execution record). Emits an ORDERED instance list
(underdetermined-first, determined-control last) so the Bayesian run front-loads the discriminating
cases. Frozen + reproducible: same trajectories -> same strata.

Signals (per instance, from runs/scored/artifacts/*/claude/*recon*/*.jsonl):
  - manufactured-diff perturbation: box commands that RUN code with logic / inject a print / run a
    narrowed test -- the abductive experiment (manufacture a diff), NOT pure navigation.
  - re-entry: a depth>=1 recon trajectory exists -> the first diagnosis was killed and re-diagnosed
    -> perturbation was DECISION-RELEVANT (it broke a tie). Weighted heavily.

Strata (pre-committed):
  UNDERDETERMINED : re-entry OR manufactured-diff >= 2   (primary endpoint: feynman > static here)
  DETERMINED      : manufactured-diff == 0 AND no re-entry (control: feynman ~ static here)
  MID             : everything else (run after primary, before control)

  driver/perturbation_strata.py            # write tasks/perturbation_strata.tsv + ordered .txt
"""
import json, glob, re, pathlib, sys
from collections import defaultdict

REPO = pathlib.Path(__file__).resolve().parent.parent
ART = REPO / "runs" / "scored" / "artifacts"
OUT_TSV = REPO / "tasks" / "perturbation_strata.tsv"
OUT_TXT = REPO / "tasks" / "perturbation_sample.txt"

# A box command counts as a MANUFACTURED-DIFF experiment if it runs code carrying logic (not just
# locating a file) or injects/narrows a test. Pure navigation (import X; print(X.__file__)) excluded.
EXPERIMENT = re.compile(
    r"(print\([^)]*[.\[(+\- ][^)]*\)"          # print of a computed expression, not print('x')
    r"|console\.log\([^)]*[.\[(+\-][^)]*\)"
    r"|\bpytest\b[^|]*\b-k\b"                    # narrowed test target
    r"|python3?\s+-c\s+['\"][^'\"]*(;|\bfor\b|\bif\b|\bdef\b|=)"  # inline script with statements
    r"|node\s+-e\s+['\"][^'\"]*(;|=>|=)"
    r"|>>?\s*\S+\.(py|js|go|rb|php)\b"          # writing into a source file (inject) then (re)run
    r")", re.I)
NAV = re.compile(r"__file__|which |type -|\bls\b|\bfind\b|\bcat\b|\bgrep\b|\bhead\b|\btail\b|\bsed -n\b|\bgit (log|blame|show)\b")


def bash_cmds(path):
    out = []
    for line in open(path, errors="ignore"):
        try:
            o = json.loads(line)
        except Exception:
            continue
        def walk(x):
            if isinstance(x, dict):
                if x.get("type") == "tool_use" and str(x.get("name", "")).lower() == "bash":
                    c = x.get("input", {}).get("command", "")
                    if c:
                        out.append(c)
                for v in x.values():
                    walk(v)
            elif isinstance(x, list):
                for v in x:
                    walk(v)
        walk(o)
    return out


def main():
    files = glob.glob(str(ART / "*" / "claude" / "*recon*" / "*.jsonl"))
    exp = defaultdict(int); depth = defaultdict(int); seen = set()
    for f in files:
        m = re.search(r"recon-instance-(.+?)-d(\d)", f)
        if not m:
            continue
        iid, d = m.group(1), int(m.group(2))
        seen.add(iid); depth[iid] = max(depth[iid], d)
        for c in bash_cmds(f):
            if c.lstrip().startswith("/tmp/gate-pro"):
                continue  # reproduction = universal, not scoped perturbation
            inner = c.split("'", 1)[1] if ("'" in c and "box-pro" in c) else c
            if EXPERIMENT.search(inner) and not (NAV.search(inner) and not EXPERIMENT.search(inner)):
                exp[iid] += 1

    rows = []
    for i in sorted(seen):
        reentry = 1 if depth[i] >= 1 else 0
        e = exp[i]
        if reentry or e >= 2:
            stratum = "UNDER"
        elif e == 0 and not reentry:
            stratum = "DET"
        else:
            stratum = "MID"
        score = reentry * 100 + e
        rows.append((score, stratum, i, e, reentry))

    order = {"UNDER": 0, "MID": 1, "DET": 2}
    rows.sort(key=lambda r: (order[r[1]], -r[0]))   # strata-ordered, high-perturbation first within
    OUT_TSV.write_text("instance_id\tstratum\texperiments\treentry\tscore\n" +
                       "".join(f"{i}\t{s}\t{e}\t{re_}\t{sc}\n" for sc, s, i, e, re_ in rows))
    OUT_TXT.write_text("".join(f"{i}\n" for _, _, i, _, _ in rows))
    from collections import Counter
    c = Counter(s for _, s, _, _, _ in rows)
    print(f"scored {len(rows)} instances from {len(files)} recon trajectories")
    print(f"  strata: {dict(c)}")
    print(f"  ordered sample -> {OUT_TXT}   (UNDER first, DET last)")
    print(f"  top UNDER: " + ", ".join(f"{i[:28]}(e={e},r={re_})" for sc, s, i, e, re_ in rows[:4]))


if __name__ == "__main__":
    main()
