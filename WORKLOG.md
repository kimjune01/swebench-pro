# swebench-pro worklog

Newest first.

## 2026-05-24 — source-only gate committed + rec #2 re-confirmed

Applied FAILURE_ATTRIBUTION.md (verified repo) to pro. The four recs map: #1 source-only
gate and #4 de-biasing protocol were already in hand (the gate as an uncommitted diff, the
protocol as `hypotheses/97-to-100.md`); #3 (from-scratch run) stays future.

- **#1 committed** (`7e3f697`): the iteration gate and `verify_gate` now `git checkout {tsha}
  -- {testfiles}` to restore gold tests before every run; recon/craft prompts state tests are
  gold-locked; `_strip_test_blocks` gained the `_is_testfile` convention fallback for the
  private split. py_compile clean; all three callers (`helpers`/`verify_gate`/`capture_patch`)
  thread `tsha`.
- **#2 re-confirmed** via `testify.py` on django-14170 (`patch.diff` from the 20260524T031903Z
  run). Local verdict == official, by construction: `RESOLVED_NO`, F2P 2/0, P2P 67 pass / **9
  fail** — the BETWEEN-filter index optimization assertions the agent weakened ("Tests updated
  to reflect this intentional behavior change," craft log). pred sha256 `cecf6d72…`. The
  source-only capture strips the test edit, so gold-test restoration exposes the false-green:
  local-green/official-red is now impossible for this class. (Re-confirmation of the earlier
  same-day lever-#3 catch, not a new finding.)

## 2026-05-24 — rename: the bench attestation tool is `testify`

`attest.py` → `testify.py`; the rung5 function/stage/ledger fields are `testify*`. Reason:
the global `/attest` skill (sweep's kanban behavioral gate) is a different thing — `testify`
is deterministic bench code that re-grades a captured prediction, not an LLM skill. The
*concept* word "attestation" (official-attested win, attestation trail) stays as-is; only the
tool name moved.

## 2026-05-24 — rung5: attestation contract wired into the driver

`driver/rung5_driver.py` = rung4 + two changes:
1. **Local dispatch.** `ssh()` now runs commands in a local shell (`_localize` drops `sudo`,
   forces `--platform linux/amd64` on pull/run); box/gate helpers call `docker exec`
   directly. Invocation drops the box-env arg: `rung5_driver.py <tasks.json> <iid>...`.
2. **The contract.** After `capture_patch`, `testify()` re-grades the serialized
   source-only prediction on a FRESH clean container via swebench's own parser
   (`get_logs_eval`/`get_eval_tests_report`/`get_resolution_status`). The **final verdict is
   the attestation, not the agent's audit**: the PATCHES ledger records `submittable` (=
   resolved AND decided) + `prediction_sha256`, and `gate_divergence_caught` fires when the
   agent said RESOLVED but the clean re-grade is red. No green attestation → not submittable.
   Markers wrapped in Python, not shell, to dodge the nested single-quote trap.

**Validated (contract path, not full loop).** Exercised the new code through the driver's
own module on pytest-5787: `decision=decided, resolved=false, RESOLVED_NO`,
`p2p_failures=[test_deserialization_failure]`, sha256 `9c7c4f3d…` — identical to the
standalone `testify.py`. Fresh container spun and torn down by the function; no leak. So a
real run where the agent claims RESOLVED here yields `gate_divergence_caught=true,
submittable=false`.

**Not yet run:** the full recon→craft→audit loop locally under rung5 (token/time cost). The
agent loop is host-agnostic already (claude on the plan machine, box/gate over docker exec),
so the local seam is the only untested-at-scale part. Next: a single full-loop smoke run on a
cheap instance to confirm the loop drives end-to-end under local dispatch.

## 2026-05-24 — django-14170 re-grade: lever #3 confirmed on the 2nd case

Ran `testify.py` on django-14170 (prediction from
`results/django__django-14170/20260524T031903Z/patch.diff`). Verdict matches the committed
official report **field-for-field**: `resolved=false`, F2P pass=2 (no failures), **9 P2P
regressions** — the identical 9 (Extract-year BETWEEN-filter optimization + the
`test_extract_trunc` DateFunction/WithTimeZone suite). sha256 `cecf6d72…`.

Same divergence signature as pytest-5787: our committed ledger shows craft `claim=true`,
audit `verdict=RESOLVED`, with the regressed tests sitting in `passing_tests_our_gate.txt` —
green on the live tree, red on clean re-attestation of the captured prediction. Two
independent gate-divergence cases now reproduce official under the contract. The lever isn't
a one-instance fluke; both targets in PRO_PORT's gate-divergence row are closed by clean
apply + official-parser verdict.

## 2026-05-24 — `testify` mode built + mechanically validated

`driver/testify.py`: clean-base apply of a serialized prediction → pinned-test run → verdict
from swebench's **own** parser (`get_logs_eval` + `get_eval_tests_report` +
`get_resolution_status`), so the local verdict agrees with the official grader by
construction, not by a hand-rolled re-implementation. Emits a structured verdict +
`prediction_sha256` (the hash-as-precondition), writes `iso/<iid>/testify.json`, one-shot
teardown. `--keep` to retain the container.

Re-ran pytest-5787 through it: `resolved=false`, `RESOLVED_NO`, F2P pass=2 (no failures),
P2P fail=`[test_deserialization_failure]`, P2P pass=122, sha256
`9c7c4f3d…`. Matches the official report field-for-field — the manual repro below, now
mechanical. (One bug en route: double-prefixed the image namespace; `instance_image_key`
already includes `swebench/`.)

Next: re-grade django-14170 (second gate-divergence target) the same way.

## 2026-05-24 — attestation re-grade: pytest-5787 (lever #3 validated)

**Attribution.** Re-attestation of an *existing* committed artifact, not a new solve.
The graded patch is `swebench-verified/results/pytest-dev__pytest-5787/20260523T213600Z/patch.diff`,
produced by the frozen artifact on 2026-05-23; official verdict already recorded there as
`resolved: false`. This run re-grades that exact prediction locally. Telemetry only —
no-credit rule (`PRO_PORT.md`); not routed to any `results/` tree.

**Result — local attestation = official, deterministically.** Applied the committed
prediction to a clean local container (test patch committed off-tree, then `git apply`
the source-only prediction) and ran the pinned suite: **1 failed, 124 passed**. Both
FAIL_TO_PASS pass (`test_chained_exceptions[TestReport|CollectReport]`); the PASS_TO_PASS
`test_deserialization_failure` fails — exactly the official report.

**Validated against the Verified worklog + ledger.** The Verified WORKLOG's final taxonomy
(line 218) files pytest-5787 as a reasoning loss, "applied cleanly, graded UNRESOLVED —
oversized ~10KB patch." That's half the story. The committed ledger
(`results/.../20260523T213600Z/ledger.jsonl`) shows **craft claim=true, audit
verdict=RESOLVED**, and `test_deserialization_failure` sits in `passing_tests_our_gate.txt`
— yet official + this clean-apply repro show it failing. So it is a genuine **gate-divergence**
(matching PRO_PORT's failed-set table), compounded with overfit: the fix is wrong (regresses
a P2P) **and** our gate wrongly passed it. Earlier I called it "overfit, not divergence" —
that was wrong; it is both, and the gate-divergence is the part the attestation lever closes.

**Mechanism (the PRO_PORT thesis, confirmed).** Our gate earned green on the **live container
tree**, but the **captured source-only prediction** (`git diff HEAD`) applied to a clean base
fails — the artifact that earned green ≠ the artifact that gets graded. Concretely the patch
splits deserialization into chain / non-chain branches and breaks the unknown-entry-type
guard: `_report_unserialization_failure` no longer raises, so `test_deserialization_failure`
gets "DID NOT RAISE RuntimeError". The live-tree gate masked it; the clean re-attestation
surfaces it.

**Lever validated.** An attestation gate that (a) applies the *serialized source-only*
prediction to a clean base and (b) derives the verdict from the *full pinned* report via
swebench's own parser — not the agent's prose tally on the live tree — goes red here,
matching official, and would refuse the submission. This is the hash-as-precondition contract
(`PRO_PORT.md` lever #3), confirmed reproducible locally. Next: lift it into a mechanical
`testify` mode (clean apply + official parser + structured verdict + prediction hash), then
re-grade django-14170 the same way.

## 2026-05-24 — local isolation harness for the 16 not-won

Set up local-Docker iteration on the Mac so the known Verified failures can be worked
without provisioning EC2. Telemetry only — conversions on this set are not Verified wins
(no-credit rule, `PRO_PORT.md`).

- **OrbStack**: engine wedged in "Starting" (stale `vmgr` handoff socket lock); fixed by
  full quit + kill leftover procs + relaunch. Native `aarch64`; x86_64 eval images run
  under `--platform linux/amd64` (Rosetta). Confirmed: `alpine uname -m` → `x86_64`.
- **Tasks**: generated all 16 not-won JSONs into `tasks/not_won/` via the Verified venv
  (`../swebench-verified/.venv`, swebench 4.1.0). Image-name convention intact
  (`swebench/sweb.eval.x86_64.<repo>_1776_<repo>-<n>`).
- **Harness**: wrote `driver/local_iso.sh` — the EC2 driver's setup→warm→helpers flow with
  the ssh/sudo/platform substitutions (documented in `LOCAL_ISO.md`). Produces
  `iso/<iid>/{cid,failbase,gate,box}` for a manual edit→gate loop.
- **Validated end-to-end** on django-15987: pull → run → test-patch apply (committed off-tree)
  → gate. Fail-on-base capture shows the F2P test failing as expected
  (`test_fixture_dirs_with_default_fixture_path_as_pathlib`: ImproperlyConfigured not raised),
  58 tests in 0.13s.

Next: pick a lever to validate. Lowest-friction is suite-selection on a heavy-suite hang
(sympy/matplotlib) or the gate-divergence pair (pytest-5787, django-14170) for the
attestation contract.
