# swebench-pro worklog — `prereg-pro-v1-methcontent` (methodeutic-content ablation)

Newest first. Trail for the methodeutic-content arm: does the *content* of the framing prose (M =
`/recon`, methodeutic) carry the lift over generic rigor (G) and a task-only floor (T)? Pre-registration:
`docs/PREREGISTRATION-methodeutic-content-ablation.md`. Arms + parity: `docs/ARM-PROMPTS-GT.md`.
Frozen M verdicts/diagnoses live in `runs/scored/run.jsonl` + committed recon artifacts.

## 2026-06-05 — Diagnosis-accuracy instrument + the active-search/compression reframe (n small; one null, several relocations)

Built the G/T arms and ran the first three-way. The headline: **win-rate is the wrong instrument, the
clean instrument is diagnosis-vs-gold, and on it the methodeutic content shows no advantage over generic
rigor — for reasons that turn out to be the actual contribution.**

### What was built
- **G (generic-rigor steelman)** + **T (minimal)** diagnosis skills, **authored by codex** (third party,
  anti-sandbag, prereg §6). Parity: methodeutic vocabulary (`rival`/`discriminate`/`falsify`/`abduction`/
  `hypothesis graph`) = **0 in G and T, all in M**. G 1005 words vs M 1097 (gap = the methodeutic content).
  `skills/generic/`, `skills/minimal/`, hashes in `docs/ARM-PROMPTS-GT.md`.
- **`driver/pro_arm.py`** — parameterized clone of `pro_untyped.py`; swaps only the injected diagnosis
  skill (`ARM_NAME`/`ARM_SKILL`), full pipeline otherwise. `RECON_ONLY=1` short-circuits after recon
  (diagnosis-only, no craft/audit). Runs locally on OrbStack (amd64 emulation), **no fleet**.
- **`driver/diag_oracle.py`** — scores a recon handoff against the **gold patch** by base-side line-region
  overlap: recall (gold regions the diagnosis hit) + precision. Craft-free, continuous, oracle-grounded.

### The qutebrowser e34dfc68 three-way (one existence case)
| arm | diagnosis (gold recall) | end verdict |
|---|---|---|
| M methodeutic | 6 root causes, recall **0.75** | WIN (frozen) |
| G generic | **same 6 RCs**, recall **0.875** | RED — *craft flake*: impl 3/6, falsely claimed "all pass"; 0 src bytes |
| T minimal | 2 RCs, recall **0.50** | **WIN** — outer loop iterated 5→10→11 on a partial diagnosis |

- **Win-rate is craft-noise-dominated.** Diagnosis quality did NOT predict the verdict: equal-best
  diagnoses (M=G) split WIN/RED on a *shared* craft-stage flake; the *worst* diagnosis (T) won via the
  outer loop. `craft` is identical across arms → end-to-end verdict measures craft variance, not
  methodeutic content. **Compare diagnoses, not verdicts.** (Validates the prereg's behavioral-signature
  co-primary.) Do NOT score G as a loss — it's a craft andon.
- **Counter-thesis mechanism, legible:** M's methodeutic pruning *rejected a correct hypothesis*
  ("underscores handled naturally") that G's flat enumeration kept → M recall < G recall here. Holding-
  and-pruning can delete true causes naive enumeration retains. (M still won because craft hit the gate
  and fixed the underscore case itself — the scaffold recovered the diagnostic miss.)

### M-recall landscape (free, 95 frozen UNDER diagnoses vs gold)
Median recall **0.50** (small gold ≤4 regions) / **0.19** (diffuse >10) — yet the pipeline resolves ~95%.
**The outer loop recovers low-recall diagnoses to wins.** Scaffold-not-prose, quantified beyond n=1.
(Recall undercounts — line-drift + cause-described-not-cited — so 0.50 is a floor. Gold is *one* solution,
not the truth set, so a "miss" can be a different valid fix — every M>G gap must be read, not trusted.)

### G recon-only sweep (running)
8 clean candidates (small gold, high M-recall). So far all M=1.0=G=1.0 (tiny-gold, non-discriminating).
The 3–5 region cases are where discrimination would show. `driver/gsweep.sh` → `/tmp/gsweep_results.tsv`.

### Conceptual relocations (the dialogue — refinement, not retreat, IF the null is owned)
1. **test-and-verify IS induction** ⇒ "generic rigor" (G) is already *implicit, unlabeled methodeutic*.
   The real non-methodeutic floor is T, and **T loses (0.50)**. So instructed inquiry is load-bearing
   (T→G); the Peircean-specific apparatus on top adds nothing (G→M). The *only* methodeutic-distinctive
   piece left is **rival-maintenance** (abduction) — everything else is good engineering.
2. **Active search** unifies it: perturbation + test-and-verify = querying the world vs passive inference.
   Existence proof = "active search necessary." Rival-maintenance = the *query-efficient* form (pick
   discriminating experiments to minimize queries) → **only pays when queries are expensive.** SWE-bench's
   gate is free → serial test-and-revise (G) resolves rivals empirically → **predicts G≈M**, observed.
   M's edge is predicted only in expensive-query / no-oracle regimes (off-bench).
3. **The hypothesis graph = a compression of the inquiry trace, with a receipt.** The alternative is
   keeping the full context window and re-understanding it (= what G does). Each compressed node's kill
   condition is a re-runnable **execution** (code's reproducible/deterministic/perturbable substrate) →
   *verifiable* lossy compression → auditable/modular provenance. So **M-vs-G = compression-with-receipt
   vs raw-context-attention.**
4. Two value props, keep separate: **(a) accuracy/search-efficiency** — deep-search-only, dormant on a
   shallow cheap-oracle bench (→ G≈M); **(b) provenance/audit/modularity** — present always, independent
   of accuracy (M's *mis-prune was auditable*; G's single-track wasn't). Don't let (b) smuggle in as a
   solve-rate win — it isn't one.

### Compression measurement (frozen M traces)
- Handoff is a **bounded ~3–6KB receipt**; raw inquiry it compresses ranges **~20KB–720KB** (median ~47KB)
  → ratio **5–170×** (median ~10×), driven by inquiry size, not output. Bounded-output-over-variable-input
  *is* the compression operation.
- A few cases reach **~127–180K tokens (near context cap)** — the regime where raw-context (G) breaks and
  the receipt earns its keep. The bench rarely reaches it → another reason G≈M.
- **CORRECTION (my over-read):** an earlier "ratio declines with hardness, r=−0.21" was a **bucketing
  artifact** — `experiments` mis-buckets re-entry-heavy cases as "shallow." Do NOT report anything indexed
  on `experiments` as hardness. The robust statement is the bounded-receipt / inquiry-size distribution.

### Honest synthesis
Today **relocated** the methodeutic claim from "superior reasoning solves more" — *null* here: G≈M on
diagnosis, and minimal T can win outright via the loop — to **"verifiable provenance via bounded
compression, valuable in expensive-query / long-context regimes the bench doesn't reach."** Not a retreat
**iff** (a) the solve-rate null is owned, and (b) the provenance/audit claim is made falsifiable: *on hard
problems, structured graph-provenance measurably improves review (accuracy/time), gap growing with
hardness — else it's a safe harbor.* Paper scoping: keep "compression is intelligence" **out** (definitional
fight, dilutes the falsifiable claim). State the mechanism; let the reader draw the halo.
