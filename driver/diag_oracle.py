#!/usr/bin/env python3
"""diag_oracle.py — score a recon DIAGNOSIS against the gold patch (the oracle).

The craft stage is shared across arms and noisy (it dominates win/loss), so end-to-end verdict
is the wrong instrument for diagnosis quality. This scores the `recon` handoff DIRECTLY against
the gold patch: did the diagnosis point at the file+line regions the gold patch actually changed?

Unit = line-region overlap on the ORIGINAL (base_commit) side. All arms read the same base file,
and gold hunk headers (`@@ -START,COUNT @@`) are base-side, so cited lines are comparable.

  recall    = gold regions hit by the diagnosis / total gold regions   (did it find the causes?)
  precision = diagnosis sites that hit a gold region / total sites      (did it stay on-target?)

A gold region is "hit" if any edit-site line the diagnosis cites falls within (region ± SLOP).

  driver/diag_oracle.py <instance_id> <recon_handoff.txt> [--label M]
  driver/diag_oracle.py <instance_id> --gold-only        # just print the gold regions

Requires the datasets lib (Pro venv). Caches gold per id in /tmp/diag_oracle_gold/.
"""
import json, os, re, sys, pathlib

SLOP = 8  # a cited line within +/-8 of a gold hunk counts as hitting it (function-local)
CACHE = pathlib.Path("/tmp/diag_oracle_gold"); CACHE.mkdir(exist_ok=True)


def gold_regions(iid):
    """Return {file: [(start,end), ...]} of base-side line regions the gold patch changes."""
    cf = CACHE / (iid.replace("/", "_") + ".json")
    if cf.exists():
        return {k: [tuple(r) for r in v] for k, v in json.loads(cf.read_text()).items()}
    from datasets import load_dataset
    ds = load_dataset("ScaleAI/SWE-bench_Pro", split="test")
    row = next((r for r in ds if r["instance_id"] == iid), None)
    if row is None:
        sys.exit(f"instance not in dataset: {iid}")
    gold = row.get("patch") or ""
    regions, cur = {}, None
    for l in gold.splitlines():
        if l.startswith("+++ b/"):
            cur = l[6:]
            regions.setdefault(cur, [])
        elif l.startswith("@@") and cur is not None:
            m = re.search(r"@@ -(\d+)(?:,(\d+))?", l)
            if m:
                s = int(m.group(1)); c = int(m.group(2) or 1)
                regions[cur].append((s, s + max(c, 1) - 1))
    regions = {k: v for k, v in regions.items() if v}
    cf.write_text(json.dumps(regions))
    return regions


def diag_sites(text):
    """Parse {file: set(lines)} from a recon handoff. Pull file + every line number cited near
    it. Focus on Edit sites / Suspect set lines that name a file then line(s)."""
    sites = {}
    # match: `path/to/file.py` ... line(s) N[-M]  (file and numbers on the same line)
    for ln in text.splitlines():
        fm = re.search(r"`([\w./\-]+\.\w+)`", ln)
        if not fm:
            continue
        f = fm.group(1)
        nums = re.findall(r"lines?\s+(\d+)(?:\s*[-–]\s*(\d+))?", ln)
        if not nums:
            nums = [(n, None) for n in re.findall(r":(\d+)", ln)]  # file:line form
        for a, b in nums:
            a = int(a); b = int(b) if b else a
            sites.setdefault(f, set()).update(range(a, b + 1))
    return sites


def score(iid, text, label):
    gold = gold_regions(iid)
    sites = diag_sites(text)
    gold_n = sum(len(v) for v in gold.values())
    hit_regions, site_total, site_hit = 0, 0, 0
    detail = []
    for f, regs in gold.items():
        cited = sites.get(f, set())
        for (s, e) in regs:
            hit = any(s - SLOP <= ln <= e + SLOP for ln in cited)
            hit_regions += hit
            detail.append((f, s, e, hit))
    for f, lines in sites.items():
        for ln in lines:
            site_total += 1
            site_hit += any(f in gold and any(s - SLOP <= ln <= e + SLOP for (s, e) in gold[f])
                            for _ in [0])
    recall = hit_regions / gold_n if gold_n else 0
    prec = site_hit / site_total if site_total else 0
    return {"label": label, "iid": iid, "gold_regions": gold_n,
            "regions_hit": hit_regions, "recall": round(recall, 3),
            "precision": round(prec, 3), "detail": detail}


def main():
    iid = sys.argv[1]
    if "--gold-only" in sys.argv:
        g = gold_regions(iid)
        for f, regs in g.items():
            print(f, regs)
        return
    handoff = pathlib.Path(sys.argv[2]).read_text()
    label = sys.argv[sys.argv.index("--label") + 1] if "--label" in sys.argv else "?"
    r = score(iid, handoff, label)
    print(f"[{r['label']}] recall={r['recall']} ({r['regions_hit']}/{r['gold_regions']} gold regions)  precision={r['precision']}")
    for f, s, e, hit in r["detail"]:
        print(f"   {'HIT ' if hit else 'MISS'} {f}:{s}-{e}")


if __name__ == "__main__":
    main()
