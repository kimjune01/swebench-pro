#!/usr/bin/env python3
"""uptime_correlate.py — external corroboration of platform faults (prereg §4 anti-cheat).

INCOMPLETE earns a free re-roll under §3; a capability LOSS does not. So an INCOMPLETE must be backed
by a *real* provider outage, or it's a laundered loss. This tool ties each INCOMPLETE's UTC window to
the Anthropic + OpenAI Statuspage incident history.

  snapshot   : fetch each provider's status summary + incidents NOW, save timestamped under
               runs/scored/status_snapshots/ — capture-at-time so a later page edit can't move the
               goalposts. Run periodically during the scored run (the coordinator does this).
  correlate  : for every INCOMPLETE in the ledger, report whether its [started_at, ended_at] overlaps
               any documented incident. No overlap -> flagged: reclassify LOSS (prereg §4). Writes the
               table into FAILURE_ATTRIBUTION.md.

Stdlib only (urllib) — no third-party deps, so it runs anywhere the rest of the harness does.
"""
import argparse, json, pathlib, sys, time, urllib.request
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent
SNAP_DIR = REPO / "runs" / "scored" / "status_snapshots"
LEDGER = REPO / "runs" / "scored" / "run.jsonl"
ATTRIB = REPO / "FAILURE_ATTRIBUTION.md"

# Statuspage v2 JSON. Anthropic 302-redirects to its canonical host; urllib follows GET redirects.
PROVIDERS = {
    "anthropic": "https://status.anthropic.com/api/v2/incidents.json",
    "openai": "https://status.openai.com/api/v2/incidents.json",
}
SUMMARY = {k: v.replace("incidents.json", "summary.json") for k, v in PROVIDERS.items()}


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "swebench-pro-uptime/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _parse(ts):
    """ISO8601 (Statuspage uses offset-aware; our ledger uses trailing Z) -> aware UTC datetime."""
    if not ts:
        return None
    ts = ts.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(ts).astimezone(timezone.utc)
    except ValueError:
        return None


def snapshot():
    SNAP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    for name, url in SUMMARY.items():
        try:
            data = _get(url)
            (SNAP_DIR / f"{name}_{stamp}.json").write_text(json.dumps(data))
            print(f"snapshot {name} @ {stamp}: {data.get('status', {}).get('description', '?')}")
        except Exception as e:
            print(f"snapshot {name} FAILED: {e}", file=sys.stderr)


def _all_incidents():
    """Union of incident windows from live API + every saved snapshot (snapshots win if the page was
    later edited — capture-at-time). Returns list of (provider, name, start, end)."""
    out = []
    seen = set()

    def add(provider, inc):
        key = (provider, inc.get("id"))
        if key in seen:
            return
        seen.add(key)
        start = _parse(inc.get("started_at") or inc.get("created_at"))
        end = _parse(inc.get("resolved_at")) or datetime.now(timezone.utc)
        if start:
            out.append((provider, inc.get("name", "?"), start, end))

    for name, url in PROVIDERS.items():
        try:
            for inc in _get(url).get("incidents", []):
                add(name, inc)
        except Exception as e:
            print(f"live fetch {name} failed ({e}); relying on snapshots", file=sys.stderr)
    for snap in sorted(SNAP_DIR.glob("*.json")) if SNAP_DIR.exists() else []:
        prov = snap.name.split("_")[0]
        try:
            for inc in json.loads(snap.read_text()).get("incidents", []):
                add(prov, inc)
        except Exception:
            pass
    return out


def correlate(ledger):
    recs = [json.loads(l) for l in pathlib.Path(ledger).read_text().splitlines() if l.strip()]
    incs = _all_incidents()
    incomplete = [r for r in recs if r["state"] == "INCOMPLETE"]
    rows, flagged = [], 0
    for r in incomplete:
        s, e = _parse(r.get("started_at")), _parse(r.get("ended_at"))
        hits = [(p, n) for (p, n, ist, ien) in incs if s and e and ist <= e and s <= ien] if s and e else []
        ok = bool(hits)
        flagged += 0 if ok else 1
        rows.append((r["instance_id"], r.get("started_at", "?"), r.get("ended_at", "?"),
                     "; ".join(f"{p}:{n}" for p, n in hits[:2]) if ok else "— NONE —",
                     "corroborated" if ok else "**RECLASSIFY LOSS (§4)**"))

    lines = [
        "# Failure attribution — platform-fault corroboration (prereg §4)",
        "",
        f"Generated {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} from `{pathlib.Path(ledger).name}` "
        f"+ {len(incs)} provider incidents (live + snapshots).",
        "",
        f"INCOMPLETE instances: **{len(incomplete)}** · corroborated by a provider incident: "
        f"**{len(incomplete)-flagged}** · uncorroborated (→ reclassify LOSS): **{flagged}**.",
        "",
        "| instance | started_at | ended_at | overlapping incident | verdict |",
        "|---|---|---|---|---|",
    ]
    lines += [f"| `{i[:48]}` | {st} | {en} | {hit} | {v} |" for i, st, en, hit, v in rows]
    if not rows:
        lines.append("| _(no INCOMPLETE instances)_ | | | | |")
    ATTRIB.write_text("\n".join(lines) + "\n")
    print(f"wrote {ATTRIB}  ({len(incomplete)} INCOMPLETE, {flagged} uncorroborated)")
    if flagged:
        print(f"  ⚠ {flagged} INCOMPLETE with no provider-incident overlap — reclassify LOSS (prereg §4)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["snapshot", "correlate"])
    ap.add_argument("--ledger", default=str(LEDGER))
    args = ap.parse_args()
    (snapshot if args.cmd == "snapshot" else lambda: correlate(args.ledger))()


if __name__ == "__main__":
    main()
