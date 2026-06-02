# Cost basis — how the per-instance dollar figures are derived

This document shows the arithmetic behind the cost figures for both SWE-bench Pro
model-pair runs. Every number traces to committed token data times a published API
rate. It is an accounting record, not an argument; interpretation lives in
[`DISCUSSION.md`](DISCUSSION.md).

**Two bases, kept separate.** *Economic* is what the work costs anyone at metered
public API rates (the portable, reproducible number, quoted in the scoreboard).
*Cash* is what the operator actually paid, most of it absorbed by flat
subscriptions (Claude Max, codex, Cursor) at ~$0 marginal. The economic basis is
the one a third party can reproduce; the cash basis is recorded at the end for
context. See [the cash-vs-economic reconciliation](#cash-vs-economic).

## Published API rates (May 2026)

Per million tokens. Cache columns are provider-specific; "—" means not applicable
to that leg's logged usage.

| Model | role | input | cache write | cache read | output | source |
|---|---|--:|--:|--:|--:|---|
| Claude Sonnet 4.5 | frontier generator | $3.00 | $3.75 (5m) | $0.30 | $15.00 | [platform.claude.com](https://platform.claude.com/docs/en/about-claude/pricing) |
| OpenAI GPT-5.5 | frontier challenger | $5.00 | — | $0.50 | $30.00 | [openai.com](https://openai.com/api/pricing/) |
| Kimi K2.5 (Composer 2.5) | open-weight generator | $0.60 | — | $0.10 | $3.00 | [Moonshot via costgoat](https://costgoat.com/pricing/kimi-api) |
| Gemini Flash 3.5 | proprietary challenger | $0.30 | — | — | $2.50 | [ai.google.dev](https://ai.google.dev/gemini-api/docs/pricing) |

GPT-5.5 cache read uses the standard 10%-of-input OpenAI cache discount ($0.50).
Sonnet cache writes are priced at the 5-minute rate ($3.75); any 1-hour writes
(billed $6.00) would raise the Sonnet leg slightly, so this is a lower bound on
that line.

## Frontier pair — Sonnet 4.5 + GPT-5.5

### Sonnet 4.5 generator leg

Source: 3,103 Claude Code session logs (`*.jsonl`, UUID-named) in
`runs/scored/artifacts.tar.zst`, summed over per-message `usage` records, model
`claude-sonnet-4-5-20250929`.

| token type | volume | rate | cost |
|---|--:|--:|--:|
| input (uncached) | 0.9 M | $3.00 | $2.70 |
| output | 67.4 M | $15.00 | $1,011.00 |
| cache creation | 225.2 M | $3.75 | $844.50 |
| cache read | 5,277.5 M | $0.30 | $1,583.25 |
| **Sonnet leg** | | | **$3,442.33** |

Cross-check: the output (67.4 M) and cache-read (5,277.5 M ≈ 5.3 B) totals match
the independently published figures in [`SCOREBOARD.md`](SCOREBOARD.md) ("67M output
tokens, 5.3B cache-read"), derived from a different pass over the same artifacts.

### GPT-5.5 challenger leg

Source: 2,285 codex rollout logs (`rollout-*.jsonl`) in `runs/scored/artifacts.tar.zst`.
1,244 carry a `token_count` event (the session's `total_token_usage`); these are
summed directly. The remaining 1,041 are short single-turn challenge sessions (3–4
`response_item`s each, none empty) that emitted no counter; their text is
char-counted (÷4) as a tail estimate.

| source | input (uncached) | cached input | output | cost |
|---|--:|--:|--:|--:|
| 1,244 logged sessions | 31.65 M | 93.73 M | 2.74 M | $287.41 |
| 1,041 short sessions (char-est.) | ~3.08 M | — | ~0 | $15.42 |
| **GPT-5.5 leg** | | | | **$302.83** |

The tail is char-estimated (the one approximation in the chain) but bounded under
$16 (well under 1% of the frontier total), so its imprecision does not move the
headline.

### Frontier total

| leg | total | per instance (÷728) |
|---|--:|--:|
| Sonnet 4.5 | $3,442.33 | $4.728 |
| GPT-5.5 | $302.83 | $0.416 |
| **Frontier** | **$3,745.16** | **$5.14** |

## Open-weight pair — Composer 2.5 + Gemini Flash

### Composer 2.5 generator leg

Source: Cursor usage export `runs/flash-composer/composer-usage-cursor-2026-05-31.csv`
(2,094 events, model `composer-2.5`), summed by token type and priced at Kimi K2.5
rates (Composer 2.5 is a K2.5 fine-tune).

| token type | volume | rate | cost |
|---|--:|--:|--:|
| input (uncached) | 92.1 M | $0.60 | $55.27 |
| cache read | 1,462.9 M | $0.10 | $146.29 |
| output | 17.1 M | $3.00 | $51.18 |
| **Composer leg** | | | **$252.73** |

Total logged volume is 1.57 B tokens, cache-write column zero.

### Gemini Flash challenger leg

`$44.00`, operator-attested. Gemini ran on the metered Gemini API, so the attested
cash equals the economic cost for this leg (no subscription subsidy to back out).

### Open-weight total

| leg | total | per instance (÷728) |
|---|--:|--:|
| Composer 2.5 | $252.73 | $0.347 |
| Gemini Flash | $44.00 | $0.060 |
| **Open-weight** | **$296.73** | **$0.41** |

## Summary

| pair | resolve | economic $/instance | median time |
|---|--:|--:|--:|
| Sonnet 4.5 + GPT-5.5 | 95.3% (694/728) | **$5.14** | 12.8 min |
| Composer 2.5 + Gemini Flash | 93.1% (678/728) | **$0.41** | 8.4 min |

Same frozen harness. The open-weight-generator pair runs **~12.6×** cheaper at **2.2 points**
lower resolve rate.

Denominator is 728 eligible instances for both runs (731 dataset − 3 gold-patch
defects). Median time is per-instance wall-clock, last-wins dedup over the run
ledger (frontier n=728; open-weight n=597 instances that logged timing).

## Cash vs economic

The economic figures above price every leg at public API rates, as a third-party
reproducer would pay. The operator's actual cash was far lower because most legs
ran on flat subscriptions at ~$0 marginal:

| leg | economic | how it was actually run | marginal cash |
|---|--:|---|--:|
| Sonnet 4.5 | $3,442 | Max plan (418 inst) + paid API (310 inst) | $813.52 |
| GPT-5.5 | $303 | codex subscription | ~$0 |
| Composer 2.5 | $253 | Cursor subscription | ~$0 |
| Gemini Flash | $44 | metered Gemini API | $44.00 |

So against ~$4,042 of economic (all-API) cost, the run's marginal cash was
≈ **$858** plus the fixed monthly subscriptions and ~$58 EC2. The gap is the
subscription subsidy; it is real but **not reproducible** by someone paying API
rates, which is why the scoreboard quotes the economic basis and treats the cash
basis as context. (Whether bulk automation on a consumer subscription falls under
those plans' terms is unspecified; the economic basis sidesteps that question.)

## Reproduce these numbers

Token totals (each re-derivable from the committed artifacts):

```bash
# Sonnet leg — sum usage across Claude Code session logs
tar --use-compress-program=unzstd -xf runs/scored/artifacts.tar.zst -C /tmp/x \
  $(tar --use-compress-program=unzstd -tf runs/scored/artifacts.tar.zst | grep -E '/[0-9a-f-]{36}\.jsonl$')
#   then sum message.usage.{input,output,cache_creation_input,cache_read_input}_tokens
#   for model claude-sonnet-4-5-*  ->  67.4M out, 5277.5M cache-read (matches SCOREBOARD)

# GPT-5.5 leg — sum total_token_usage from codex rollouts
#   grep payload.type == 'token_count', take last total_token_usage per file

# Composer leg — sum the Cursor CSV columns
python3 -c "import csv;r=list(csv.DictReader(open('runs/flash-composer/composer-usage-cursor-2026-05-31.csv')));\
print(sum(float(x['Cache Read'] or 0) for x in r), sum(float(x['Output Tokens'] or 0) for x in r))"
```

Then apply the rate table above. The Gemini Flash leg ($44) is operator-attested
and not reconstructable from the committed artifacts.
