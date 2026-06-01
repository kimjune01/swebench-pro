# Verifying the OSS receipts

[`pr-receipts.jsonl`](pr-receipts.jsonl) is a frozen ledger of every decided pull request
(merged or closed-unmerged) authored by `kimjune01` during the ~10-day OSS run that began
at the pipeline epoch `2026-05-09T00:34:00Z`. [`pr-receipts.summary.json`](pr-receipts.summary.json)
is its rollup. This file lets a third party reconfirm both the frozen artifact and the
live GitHub state, with no dependency on any other repository.

## Frozen counts (as committed here)

| | |
|---|--:|
| merged | 81 |
| closed-unmerged | 79 |
| decided (merged + closed) | 160 |
| merge rate = merged ÷ decided | 50.6% |
| distinct repos with a merge | 73 |
| self-owned repos among them | 0 |
| median merged diff (added + deleted lines) | 49 |

"Decided" excludes still-open PRs and the pre-PR triage funnel. Merge rate is
`merged / (merged + closed-unmerged)`.

## Reproduce the frozen counts from the ledger

Recompute every cell above straight from the committed `pr-receipts.jsonl`:

```bash
python3 - <<'PY'
import json
rows = [json.loads(l) for l in open('pr-receipts.jsonl')]
merged = [r for r in rows if r['category'] == 'merged']
closed = [r for r in rows if r['category'] == 'closed_unmerged']
decided = len(merged) + len(closed)
diffs = sorted(r['additions'] + r['deletions'] for r in merged)
print('merged           :', len(merged))
print('closed-unmerged  :', len(closed))
print('decided          :', decided)
print('merge rate %%     :', round(100 * len(merged) / decided, 1))
print('distinct repos   :', len({r['repo'] for r in merged}))
print('self-owned merged:', sum(r['repo'].lower().startswith('kimjune01/') for r in merged))
print('median merged diff:', diffs[len(diffs) // 2])
PY
```

## Reproduce the live counts from GitHub

The ledger is a snapshot; GitHub keeps moving (open PRs resolve over time). Query the
current state with the GitHub GraphQL API — counts use the same epoch cutoff, so the
`merged` total is monotonic and should match or exceed the frozen 81:

```bash
gh api graphql -f query='
{ merged: search(query: "is:pr is:merged author:kimjune01 created:>2026-05-09T00:34:00Z", type: ISSUE) { issueCount }
  closed: search(query: "is:pr is:closed is:unmerged author:kimjune01 created:>2026-05-09T00:34:00Z", type: ISSUE) { issueCount }
  open:   search(query: "is:pr is:open author:kimjune01 created:>2026-05-09T00:34:00Z", type: ISSUE) { issueCount } }'
```

Or paste the inner query into the GitHub GraphQL Explorer (https://docs.github.com/en/graphql/overview/explorer).

**Keep the full `T00:34:00Z` timestamp — do not shorten it.** The pipeline epoch is
`2026-05-09T00:34:00Z`, and GitHub's `created:>` qualifier honors the time component (and
the `Z`). Two ways to get it wrong: a bare date `created:>2026-05-09` means *after the
entire day* (starts May 10, dropping the epoch day, undercount to 66 merged); midnight
`T00:00:00Z` pulls in two closed-unmerged PRs from the `00:00–00:34` pre-epoch window
(closed reads 82 instead of 80, deflating the merge rate). The query must start at the
epoch instant, not the calendar day and not midnight.

Observed live on 2026-05-31: `merged 81`, `closed 80`, `open 117` — one PR closed since the
freeze (79 → 80), merged unchanged. Live merge rate among decided: 81 / 161 ≈ 50.3%.

## Why this is the contamination-free check

These are post-cutoff issues on 73 repositories the model held no training priors for
("cold" repos), where a real maintainer either merges the fix or closes it. Public-split
benchmark contamination cannot inflate a maintainer's merge decision, so the ~50% merge
rate is a harness-attribution signal independent of any training-data overlap. The PRs
came from the sibling [`sweep`](https://github.com/kimjune01/sweep) pipeline — the same
methodeutics lineage as this repo's recon → craft → audit harness, not a byte-for-byte
copy of it — so read the receipts as evidence for the *method*; the open-weight ablation
in [`README.md`](../README.md) is the evidence for this specific scaffold.
