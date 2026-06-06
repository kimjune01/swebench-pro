# G / T arm prompts — authorship, parity, and freeze record

Supports `docs/PREREGISTRATION-methodeutic-content-ablation.md`. Records the two non-methodeutic
diagnosis skills that pair against the frozen methodeutic `recon` (M) for the §0a side-by-side
reasoning exhibit and the (optional) §2–§5 statistical tier.

## Arms

| arm | skill | role |
|---|---|---|
| **M** | `skills/recon/skill.md` (FROZEN) | methodeutic: rival hypotheses, discriminating tests, abduction/deduction/induction taxonomy, kill-the-fix, hypothesis graph |
| **G** | `skills/generic/skill.md` | steelman generic rigor: reproduce-first, localize, root-cause, smallest-fix, test-and-verify, revise-on-failure — **no** rival set, no discriminating-between-rivals, no falsify-stance, no mode taxonomy |
| **T** | `skills/minimal/skill.md` | task-only floor: resolve the issue, pass the tests, report what changed |

## Authorship (anti-sandbag, prereg §6)

G and T were authored by **codex (gpt-5.4), a third party**, not the experimenter — the bias guard
against an experimenter-weakened control. Codex was given M verbatim as the parity target and
instructed to author G **to win** with the strongest evidence-based generic-rigor techniques for
current-gen LLM coding agents, excluding only the methodeutic-distinctive moves. Brief +
boundary note: `/tmp/codex_author_GT.txt`, codex transcript `/tmp/codex_GT_out.md`.

Codex's self-reported boundary: G keeps reproduce-first, localization, root-cause, scope control,
enumeration-before-assertion, smallest-correct-fix, audit-driven revision, explicit edit-site
handoff; it forbids live rival hypotheses, discriminating-tests-between-rivals, falsification/kill
framing, the reasoning-mode taxonomy, hypothesis graveyards, and graph maintenance. Hardest place to
keep generic: the re-entry section (outer-loop correction invites "the gate killed your hypothesis"
language) — held generic by framing audit as execution feedback revealing incomplete scope / mistaken
reading, not as hypothesis-killing.

## Parity check (mechanical, prereg §6)

- **Word count.** M 1097 · G 1005 (≈92%) · T 215 (intentional floor). G runs ~8% under M; the gap is
  exactly the methodeutic content M legitimately carries (the competing-hypotheses + rejected-
  hypotheses + mode-taxonomy passages). Padding G to ±5% would inject filler, so the honest call is to
  leave G shorter and record why. Sections: M 17 · G 15 · T 5.
- **Banned-word check (the load-bearing parity gate).** The methodeutic-distinctive vocabulary
  (`rival`, `competing hypothes*`, `discriminat*`, `falsif*`, `disconfirm`, `abduction/abduce`,
  `hypothesis graph`) appears **only in M**. Grep count in G = 0, in T = 0. M carries all of it.
  This is the real isolation: the manipulated variable is present in M and absent in G/T.
- **Wrapper neutrality (disclosure).** The adapter wrapper around the skill (`driver/pro_arm.py`) is
  held neutral and identical for G and T — "Jot working notes" not "Append hypothesis nodes", `# Recon:`
  handoff marker, same ENVIRONMENT/gate/source-only rules. So the only methodeutic vocabulary anywhere
  in the G/T arms is whatever the skill carries — which is zero. M's frozen wrapper (`rung5_driver.recon`)
  says "Append hypothesis nodes"; that wrapper-vocab difference is itself part of the methodeutic
  framing and is attributed to M, not controlled out. Disclosed, not hidden (prereg §11).

## SHA-256 (freeze hashes)

```
recon   05e7e31592160f75b989617d099150432dfd2e2f94d231386d1f2b6c3f4e1992
generic 0fd0d146543ccac882b1928bf44fe3f679004f7af54cf77c5265bcf51319b56c
minimal f58cfe4997d3626828c4d022d2c6d2f4663aad58c2a1259428a7e55feace3699
```

## Runner

`driver/pro_arm.py` — parameterized clone of `pro_untyped.py`; imports the frozen harness verbatim
(`craft`, `audit`, setup/gate/capture/grade), swaps only the injected diagnosis skill via
`ARM_NAME` + `ARM_SKILL`. Full-execution box + real gate + outer loop (identical to M; **not** the
read-only static arm). Runs locally on OrbStack under `--platform linux/amd64` emulation, same as the
feynman recovery, so the §0a exhibit costs no fleet.
