# Results — SWE-bench Pro, frozen tag `prereg-pro-v1`

**694 / 728 eligible resolved = 95.33%**, official Pro grader, single frozen
instance-blind artifact, whole eligible set in one measurement. All numbers
below are recomputed from `runs/scored/run.jsonl` (last-wins dedupe by
`instance_id`, matching the `./score` tool). A reader can re-derive every
figure here from that ledger; the per-instance captured diffs in the
committed bundle `runs/scored/artifacts.tar.zst` let a reader re-grade any
single verdict (PROCEDURE §6).

- **Eligible denominator:** 728 (731 dataset instances − 3 gold-patch defects).
  The three excluded ids and their grader output are committed in
  `runs/audit/defects.jsonl`; the kept set is `runs/audit/eligible.txt`
  ([`PREREGISTRATION.md`](PREREGISTRATION.md) §6).
- **Terminal verdicts:** 728 (694 WIN, 34 LOSS), **0 INCOMPLETE** — full coverage.
- **Resolve-rate:** W / (W + L) = 694 / 728 = 95.33%.
- **Run window:** 2026-05-27 20:02Z → 2026-05-30 17:37Z, ~72 h wall-clock —
  **not uninterrupted:** three provider-credential stalls and a mid-run switch
  from Max-subscription to paid API billing, all recovered with 0 instances
  lost. Provenance in [`RUN_NOTES.md`](RUN_NOTES.md).

This is a **system result**, not a capability claim: a Sonnet-4.5 generator
plus a GPT-5.5 craft challenger, both contaminated on these repos, in the
recon→craft→audit scaffold. See [`PREREGISTRATION.md`](PREREGISTRATION.md) §7,
§12 for what that confound costs the claim. The headline is a bench number, not
evidence that either model "reasoned" the fixes.

## Per-repo breakdown

Eleven public repos. `W`/`L` are terminal official verdicts; `%win` is
W/(W+L). Runtime columns are wall-clock seconds per terminal instance (recon +
craft + audit + capture + grade), recomputed across all 728.

| repo | W | L | %win | mean s | p50 s | p90 s | max s |
|---|---:|---:|---:|---:|---:|---:|---:|
| navidrome | 57 | 0 | 100.0 | 918 | 672 | 1231 | 5085 |
| tutao | 20 | 0 | 100.0 | 1194 | 957 | 1431 | 4070 |
| qutebrowser | 78 | 1 | 98.7 | 771 | 657 | 1100 | 3663 |
| gravitational | 75 | 1 | 98.7 | 1474 | 1005 | 2393 | 10745 |
| future | 60 | 1 | 98.4 | 937 | 784 | 1148 | 3789 |
| flipt | 83 | 2 | 97.6 | 1111 | 886 | 1442 | 6339 |
| element | 54 | 2 | 96.4 | 1200 | 767 | 2401 | 7619 |
| protonmail | 62 | 3 | 95.4 | 1362 | 849 | 2995 | 7037 |
| ansible | 89 | 6 | 93.7 | 919 | 697 | 1294 | 6391 |
| internetarchive | 84 | 7 | 92.3 | 726 | 626 | 1082 | 4347 |
| NodeBB | 32 | 11 | 74.4 | 1433 | 873 | 3178 | 6441 |
| **total** | **694** | **34** | **95.33** | **1060** | **770** | **1537** | **10745** |

Repo labels are the dataset org prefix; the canonical instance ids are
`instance_<org>__<repo>-<sha>` (e.g. `gravitational` is
`gravitational__teleport`, `flipt` is `flipt-io__flipt`, `element` is
`element-hq__element-web`, `future` is `future-architect__vuls`).

Resolve-rate, sorted, as a bar (each `#` ≈ 2 points):

```
navidrome        100.0  ##################################################
tutao            100.0  ##################################################
qutebrowser       98.7  #################################################
gravitational     98.7  #################################################
future            98.4  #################################################
flipt             97.6  #################################################
element           96.4  ################################################
protonmail        95.4  ###############################################
ansible           93.7  ###############################################
internetarchive   92.3  ##############################################
NodeBB            74.4  #####################################
```

Ten of eleven repos resolve at 92.3% or above. **NodeBB at 74.4% sits 18
points below the next-lowest repo (internetarchive, 92.3%) and contributes 11
of the 34 total losses** (see below).

## Runtime distribution

All 728 terminal instances, by wall-clock bucket (each `#` ≈ 3 instances):

```
   0–300 s      0
 300–600 s    168  ########################################################
 600–900 s    305  ######################################################################################################
 900–1200 s   137  ##############################################
1200–1800 s    58  ###################
1800–2700 s    14  #####
2700–3600 s    17  ######
3600–5400 s    15  #####
5400+   s      14  #####
```

The mass sits at 300–1200 s (610 / 728 = 84%); median 770 s. The right tail is
heavy repos (webclients, teleport) and craft-hangs on big test suites — the
`craft 3600` stage cap is per-stage, so a multi-cycle outer loop on a slow
suite can stack well past it. The single longest run is a 10,745 s
`gravitational__teleport` WIN.

## Loss analysis — all 34 have non-empty patches

Every loss is a real graded `not resolved` verdict on a non-empty captured
patch. **None is an empty-capture or no-patch loss.** Patch sizes across the 34
loss diffs:

| stat | bytes |
|---|---:|
| min | 765 |
| median | 3,607 |
| max | 194,336 |
| empty (0 B) | **0** |

This matters for the integrity direction: a loss here is the loop *producing a
fix the official tests rejected*, not the loop failing to produce anything. The
prereg counts both as LOSS (§4), but the distinction is what the patches show.

Losses by repo, with the loss-instance runtimes:

| repo | losses | loss runtimes (s) |
|---|---:|---|
| NodeBB | 11 | 508, 540, 552, 678, 679, 749, 812, 856, 962, 1355, 6441 |
| internetarchive | 7 | 407, 558, 655, 774, 782, 1082, 1599 |
| ansible | 6 | 766, 1125, 1266, 3065, 5417, 6391 |
| protonmail | 3 | 1446, 5562, 7037 |
| future | 1 | 2839 |
| element | 2 | 6321, 7619 |
| flipt | 2 | 512, 1725 |
| qutebrowser | 1 | 762 |
| gravitational | 1 | 8202 |

### Reading any loss yourself

Every loss is committed as an inspectable artifact, not a summary. All 6,553
artifact files (860 captured diffs, the Claude and GPT-5.5 trajectories, and the
per-box ledgers) are committed as a single compressed bundle,
`runs/scored/artifacts.tar.zst` (87 MB, sha256 + full file listing in
`runs/scored/artifacts.MANIFEST.txt` — browsable without unpacking). Unpack:

```
cd runs/scored && zstd -dc artifacts.tar.zst | tar -xf -
# yields artifacts/coord<N>/{patches,claude,codex}/...
#   patches/pro_patch_<instance_id>.diff   captured source-only diff (the graded patch)
#   claude/...craft-<instance_id>...        Claude recon/craft/audit session JSONLs
#   codex/...                               GPT-5.5 craft-challenger sessions
```

To audit a loss: take its `pro_patch_*.diff`, build `pred.json`, and re-grade
on a clean container per PROCEDURE §3 / §6. Re-grading the captured diff under
the pinned procedure reproduces the `not resolved` verdict without re-running
the agent — the grade reads only the diff, modulo the grader pathologies
documented in [`docs/bench-defects.md`](docs/bench-defects.md). The trajectory
JSONLs show *why* the loop emitted that diff.

## Open question — ansible runtime shape (flagged, not a finding)

Early in the run, ansible losses looked **bimodal by verdict**: crisp WINs
(~780 s mean) versus catastrophic LOSSes (early sample ~3200 s), suggesting
ansible's module-coupled test collection punishes a craft attempt that misses
the call graph — each extra adversary cycle re-pays a large pytest-collection
cost (worklog 2026-05-30 15:35Z; same shape as the documented sympy/matplotlib
craft-hang).

**The full six-loss sample does not support the clean split.** Ansible WIN mean
is 778 s; the six losses are 766, 1125, 1266, 3065, 5417, 6391 — three of them
sit inside the WIN range. The "fast WIN vs slow wall" story holds for the tail
(3065–6391 s craft-hangs) but breaks for the three sub-1300 s losses, which are
ordinary graded fails, not collection blowups. So this is **an open question
for the next campaign, not a result**: whether stricter test-scoping in the
craft prompt ("test only files the diff touches, not the package") removes the
tail without changing the fast losses. It is a hypothesis to test on practice
rungs, deliberately not acted on mid-run (the artifact was frozen).

## Verifying the tally

```bash
./score                       # prints WIN/LOSS, resolve-rate, coverage from run.jsonl
./score runs/scored/run.jsonl # same, explicit ledger path
```

`./score` applies last-wins dedupe by `instance_id` over all ledger events
(the run.jsonl carries the full event trail including requeues, so the raw line
count exceeds 728). The deduped terminal set is 728: 694 WIN, 34 LOSS, 0
INCOMPLETE. The per-repo and runtime figures above come from the same dedupe;
the recompute script is reproduced inline in this repo's history if you want to
diff it against your own.
