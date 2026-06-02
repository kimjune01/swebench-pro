#!/usr/bin/env python3
"""gold_divergence.py — how close are the harness's winning patches to the gold patch?

A skeptic's check, and evidence bearing on the contamination/recall objection.
OpenAI retired SWE-bench Verified after finding frontier models could reproduce
its *gold patches* on contaminated tasks
(https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/): a score
that replays the memorized human fix measures recall, not capability. Pro is the
contamination-resistant tier; this script measures, per win, how much the model's
patch overlaps the dataset's gold patch, so the claim is graded data rather than
an assertion.

WHY OVERLAP, NOT IDENTITY. Two unified diffs of the *same change* are almost never
byte-identical: they differ in git `index <sha>..<sha>` lines, `@@` hunk line
numbers, and surrounding context. So "byte-identical to gold" is ~0 for any run,
contaminated or not, and is reported only as a floor. A model that *recalled* the
gold fix would reproduce its changed lines, formatted as its own diff. The honest
signal is therefore the **overlap** between the model's changed lines/files and
gold's, reported as a distribution with a labelled near-gold tail.

CAPTURE NOISE. Harness-captured diffs can include runtime artifacts the agent
never authored (e.g. Redis `appendonlydir/…aof.manifest`). Those are stripped
(see NOISE) before comparison, because they are present in the model patch and
absent from gold and would otherwise inflate divergence for no reason. The set of
stripped patterns is printed so the normalization is auditable.

COVERAGE. The denominator is WIN rows in the run ledger, not "patches we happened
to load." A win with no captured patch is reported as `missing_prediction`, never
silently dropped, so "checked N of M wins" is explicit.

Metrics per win (runtime noise stripped):
  byte_identical      raw model patch == raw gold patch              (floor; ~0)
  file_overlap_gold   |model_files ∩ gold_files| / |gold_files|      (same region?)
  file_jaccard        Jaccard(model_files, gold_files)
  line_jaccard        Jaccard(changed content lines)                 (same change?)
  near_gold           line_jaccard >= --near-gold (default 0.80)     (recall tail)

What it does and does not show:
  - Low overlap is positive evidence the win is an independent fix, not recalled gold.
  - High overlap (near_gold) is a *candidate* for recall OR a forced fix (one
    reasonable diff). The script flags them; it does not adjudicate. Inspect the tail.
  - Model patches are often broader than gold's curated fix, which lowers overlap
    for reasons unrelated to recall. Read file_overlap_gold (region) alongside
    line_jaccard (exact change).

Usage:
    pip install datasets
    # frontier run (raw .diff capture):
    python driver/gold_divergence.py \
        --preds-dir /tmp/scoredpatches --run runs/scored/run.jsonl \
        --gold-field patch --out runs/scored/gold_divergence.jsonl
    # open-weight run (fc_pred_*.json capture) straight from the tarball:
    python driver/gold_divergence.py \
        --tarball runs/flash-composer/artifacts.tar.zst \
        --run runs/flash-composer/run.jsonl \
        --gold-field patch --out runs/flash-composer/gold_divergence.jsonl

Each receipt row carries gold+pred sha256 and the overlap numbers so a third party
can re-fetch the dataset and recompute any single value without rerunning the bench.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pathlib
import re
import statistics
import sys
import tarfile

# Runtime artifacts that capture can sweep into a diff but the agent never authored.
# Present in model patch, absent from gold -> would inflate divergence. Stripped, and
# printed at run time so the normalization is auditable.
NOISE = ("appendonlydir/", "dump.rdb", ".aof", "__pycache__/", ".pyc")

DIFF_GIT = re.compile(r"^diff --git a/.* b/(.+)$")


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", "replace")).hexdigest()


def _noise(s: str) -> bool:
    return any(n in s for n in NOISE)


def changed_files(patch: str) -> set:
    """Set of b/-side paths touched, excluding runtime-noise files."""
    return {m.group(1) for line in patch.splitlines()
            if (m := DIFF_GIT.match(line)) and not _noise(m.group(1))}


def changed_lines(patch: str) -> set:
    """Set of added/removed content lines (stripped), excluding file markers,
    hunk headers, and runtime-noise lines."""
    out = set()
    for line in patch.replace("\r\n", "\n").split("\n"):
        if line[:3] in ("+++", "---") or line.startswith("@@"):
            continue
        if line and line[0] in "+-":
            body = line[1:].strip()
            if body and not _noise(body):
                out.add(body)
    return out


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a | b) else 1.0


def _iid_from_diff_name(name: str) -> str:
    stem = pathlib.PurePosixPath(name).name[: -len(".diff")]
    return stem[len("pro_patch_"):] if stem.startswith("pro_patch_") else stem


def load_predictions(tarball, preds_dir):
    """instance_id -> model patch. Handles fc_pred_instance_*.json ({instance_id,
    patch}) and pro_patch_instance_*.diff (raw diff). Records empties separately."""
    preds, empty = {}, set()

    def add(iid, patch):
        if not iid:
            return
        if patch and patch.strip():
            preds[iid] = patch
        else:
            empty.add(iid)

    def ingest_json(raw: bytes):
        try:
            recs = json.loads(raw)
        except Exception:
            return
        for r in (recs if isinstance(recs, list) else [recs]):
            add(r.get("instance_id"), r.get("patch") or r.get("model_patch") or "")

    if preds_dir:
        for p in pathlib.Path(preds_dir).rglob("fc_pred_instance_*.json"):
            ingest_json(p.read_bytes())
        for p in pathlib.Path(preds_dir).rglob("pro_patch_instance_*.diff"):
            add(_iid_from_diff_name(p.name), p.read_text(errors="replace"))
    elif tarball:
        with tarfile.open(tarball, mode="r:*") as tf:  # .zst needs py>=3.14; else --preds-dir
            for m in tf.getmembers():
                if "fc_pred_instance_" in m.name and m.name.endswith(".json"):
                    f = tf.extractfile(m)
                    if f:
                        ingest_json(f.read())
                elif "pro_patch_instance_" in m.name and m.name.endswith(".diff"):
                    f = tf.extractfile(m)
                    if f:
                        add(_iid_from_diff_name(m.name), f.read().decode("utf-8", "replace"))
    else:
        sys.exit("provide --tarball or --preds-dir")
    return preds, empty


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


def load_gold(dataset, split, gold_field):
    from datasets import load_dataset
    ds = load_dataset(dataset, split=split)
    if gold_field:
        if gold_field not in ds.column_names:
            sys.exit(f"--gold-field {gold_field!r} not in {ds.column_names}")
        field = gold_field
    else:
        field = next((c for c in ("patch", "gold_patch", "golden_patch", "fix_patch") if c in ds.column_names), None)
        if not field:
            sys.exit(f"no gold-patch column in {ds.column_names}")
        print(f"WARNING: --gold-field not set; auto-selected {field!r}. Pass --gold-field for evidence runs.")
    return {r["instance_id"]: (r[field] or "") for r in ds}, field


def match_gold(iid, gold, strict):
    if iid in gold:
        return gold[iid], "exact"
    if strict:
        return None, "unmatched"
    base = iid[len("instance_"):] if iid.startswith("instance_") else iid
    for c in (base, re.sub(r"-v[0-9a-f]{40}$", "", iid), re.sub(r"-v[0-9a-f]{40}$", "", base)):
        if c in gold:
            return gold[c], "normalized-id"
    return None, "unmatched"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tarball")
    ap.add_argument("--preds-dir")
    ap.add_argument("--run", required=True, help="run.jsonl ledger; WIN rows are the denominator")
    ap.add_argument("--dataset", default="ScaleAI/SWE-bench_Pro")
    ap.add_argument("--split", default="test")
    ap.add_argument("--gold-field", default=None, help="gold-patch column; required tone for evidence runs")
    ap.add_argument("--strict-id", action="store_true", help="exact instance_id match only (no normalized fallback)")
    ap.add_argument("--near-gold", type=float, default=0.80, help="line_jaccard >= this flags a near-gold (recall-candidate) win")
    ap.add_argument("--out", default="gold_divergence.jsonl")
    args = ap.parse_args()

    preds, empty = load_predictions(args.tarball, args.preds_dir)
    wins, dupes = load_wins(args.run)
    gold, field = load_gold(args.dataset, args.split, args.gold_field)
    print(f"dataset={args.dataset} split={args.split} gold_field={field} | "
          f"wins={len(wins)} preds={len(preds)} empty_preds={len(empty)} ledger_dupes={dupes}")
    print(f"runtime-noise patterns stripped: {NOISE}")

    rows, fov, fjac, ljac = [], [], [], []
    n_missing = n_unmatched = n_byte = n_neargold = n_zerofile = 0
    for iid in wins:
        patch = preds.get(iid)
        if not patch:
            n_missing += 1
            rows.append({"instance_id": iid, "status": "missing_prediction" if iid not in empty else "empty_prediction"})
            continue
        gpatch, how = match_gold(iid, gold, args.strict_id)
        if gpatch is None:
            n_unmatched += 1
            rows.append({"instance_id": iid, "status": "unmatched", "match": how})
            continue
        mf, gf = changed_files(patch), changed_files(gpatch)
        ml, gl = changed_lines(patch), changed_lines(gpatch)
        f_over = (len(mf & gf) / len(gf)) if gf else 0.0
        f_jac = jaccard(mf, gf)
        l_jac = jaccard(ml, gl)
        byte_id = patch == gpatch
        near = l_jac >= args.near_gold
        n_byte += byte_id
        n_neargold += near
        n_zerofile += (len(mf & gf) == 0)
        fov.append(f_over); fjac.append(f_jac); ljac.append(l_jac)
        rows.append({
            "instance_id": iid, "status": "matched", "match": how,
            "byte_identical": byte_id,
            "file_overlap_gold": round(f_over, 4), "file_jaccard": round(f_jac, 4),
            "line_jaccard": round(l_jac, 4), "near_gold": near,
            "model_files": len(mf), "gold_files": len(gf),
            "model_changed_lines": len(ml), "gold_changed_lines": len(gl),
            "pred_sha256": sha256(patch), "gold_sha256": sha256(gpatch),
        })

    with open(args.out, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    compared = len(ljac)
    print(f"\nWINS: {len(wins)} total | compared {compared} | "
          f"missing/empty {n_missing} | unmatched {n_unmatched}")
    if compared:
        med = statistics.median
        print(f"  byte_identical to gold (floor):  {n_byte}  ({100*n_byte/compared:.1f}%)")
        print(f"  file_overlap_gold:  median {med(fov):.2f}  mean {statistics.mean(fov):.2f}")
        print(f"  wins touching NONE of gold's files: {n_zerofile}  ({100*n_zerofile/compared:.1f}%)")
        print(f"  line_jaccard:       median {med(ljac):.2f}  mean {statistics.mean(ljac):.2f}")
        print(f"  near-gold (line_jaccard >= {args.near_gold}): {n_neargold}  ({100*n_neargold/compared:.1f}%)")
        hist = collections.Counter(min(int(x * 10), 9) for x in ljac)
        print("  line_jaccard histogram:")
        for k in range(10):
            bar = "#" * hist.get(k, 0)
            print(f"    {k/10:.1f}-{(k+1)/10:.1f}: {hist.get(k,0):4d} {bar[:60]}")
    print(f"\nreceipt: {args.out} (one row per win; status, overlaps, gold+pred sha256)")


if __name__ == "__main__":
    main()
