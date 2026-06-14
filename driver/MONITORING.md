# Monitoring a batch run

A `launch_generic.sh` batch runs unattended for 30-60 min. Without a live watch,
a silent failure (e.g. the batch_005 regression: 30/30 zero-byte patches) only
shows at the end — an hour and real box-hours wasted. So stream a monitor that
surfaces trouble mid-flight.

Poll two sources every 60s, **emit only on change**:
- **launch log** `/tmp/launch_<prefix>.log` — all per-box driver stdout/stderr:
  stage lines, the `EMPTY patch` warning, tracebacks, terminal `ALL SHARDS DONE`.
- **per-box ledgers** `/tmp/swebench-abduction/rung4_results_<prefix>_*.jsonl` —
  one JSON line per stage; `"stage": "done"` = instance complete.

Track `done`/`empty`/`err` across iterations; print only on a delta or terminal.

The monitor runs in the user's shell (**zsh**), which — unlike bash — does **not**
expand a glob stored in a variable when used unquoted. So `LED='…b_*.jsonl'; grep … $LED`
matches nothing and silently counts 0 (this blinded the batch_005 monitor end to
end). Pipe `cat <literal-glob>` instead, so zsh expands the glob on the command line:

```bash
LOG=/tmp/launch_b2.log; LG='/tmp/swebench-abduction/rung4_results_b_*.jsonl'
pd=-1; pe=0; perr=0
while true; do
  done=$(cat $~LG 2>/dev/null | grep -c '"stage": "done"'); done=${done:-0}
  empty=$(cat $~LG 2>/dev/null | grep -c 'EMPTY patch'); empty=${empty:-0}
  err=$(grep -cE "Traceback|Killed|OOM|Connection refused|Permission denied" "$LOG" 2>/dev/null); err=${err:-0}
  [ "$empty" -gt "$pe" ] && { echo "!! EMPTY ($empty):"; cat $~LG 2>/dev/null | grep 'EMPTY patch' | tail -n +$((pe+1)); pe=$empty; }
  [ "$err" -gt "$perr" ] && { echo "!! ERRORS:"; grep -E "Traceback|Killed|OOM|Connection refused|Permission denied" "$LOG" | tail -3; perr=$err; }
  [ "$done" -ne "$pd" ] && { echo "progress $(date +%H:%M): done=$done/30 empty=$empty err=$err"; pd=$done; }
  grep -q "ALL SHARDS DONE" "$LOG" 2>/dev/null && { echo "TERMINAL: done=$done/30 empty=$empty err=$err"; break; }
  sleep 60
done
```

`$~LG` forces zsh to glob-expand the variable; under bash, plain `$LG` works too.
Run under the `Monitor` tool (each line = one notification), 60-min timeout; it
self-exits on `ALL SHARDS DONE`. **Before arming, sanity-check the counter prints
non-zero once instances finish** — a silently-zero counter is worse than none.

**Principles:** (1) *Emit on change, not on a tick* — volume scales with events,
not time; a quiet run is quiet. (2) *Silence ≠ success* — the alternation covers
crash signatures, not just `done`; ask "if a box crashed now, would this emit?".
(3) *Monitor is early warning, not the gate* — the authoritative check is the
`wc -c` sweep + official grade. (4) *Two sources cross-check* — ledger (`done`)
vs log (`EMPTY`); a bug in one path still shows in the other. (5) *Line-buffer*
any `tail -f | grep` variant (`grep --line-buffered`) or events stall in the pipe.

**After the run:** sweep for zero-byte patches before trusting the batch, then
grade + archive.

```bash
for t in $(python3 -c "import json;[print(x['instance_id'].replace('/','_')) for x in json.load(open('tasks/batch_NNN.json'))]"); do
  printf "%8s  %s\n" "$(wc -c </tmp/swebench-abduction/r4_patch_$t.diff 2>/dev/null||echo NA)" "$t"; done | sort -n | head
```

## Fleet-run lessons (feynman exemption rerun, 2026-06-06)

Three operational traps from a 7-box EC2 rerun, each cost real minutes:

1. **`pgrep -f <runner>.py` self-matches the launching shell.** A redispatch guard
   `if pgrep -f "feynman_run.py"; then skip` ran inside a command whose own argv also
   contained `driver/feynman_run.py` (the `nohup … &` launch line), so pgrep matched
   *itself* and skipped every box — nothing relaunched, silently. The `[f]eynman`
   bracket trick does **not** help: it stops grep matching its own process, not a
   *sibling* shell whose argv carries the plain string. **Check liveness in a command
   that does not also contain the launch string**, e.g. `ps -eo args | grep
   "driver/feynman" | grep -v grep | wc -l`, and confirm with a 2-snapshot log-growth
   check, never a self-referential pgrep.

2. **`ARM_LEDGER` defaults to `untyped`.** `ablation_fleet.sh` was launched with
   `ARM_RUNNER=feynman_run.py` but **not** `ARM_LEDGER=feynman`, so the runner wrote
   `feynman_Nof7.jsonl` while `status` polled `untyped_Nof7.jsonl` → `done=0` forever
   while the run was fine. When overriding the runner, override the ledger prefix too,
   or the monitor reads an empty file and reports a false stall.

3. **An operator `/login` mid-run rotates the OAuth token → auth-death on every
   in-flight call.** Short shards (2–3 instances) burned through the worklist on the
   dead token before fresh creds landed → 17/19 came back INCOMPLETE. The hardening
   held (auth-death → non-terminal INCOMPLETE, never LOSS, so zero contamination), but
   the recovery is: re-extract keychain creds (`security find-generic-password -s
   "Claude Code-credentials" -w`), scp to every box's `~/.claude/.credentials.json`,
   **canary one real call** (`echo ok | claude -p` → expect `OK`, not a 401), then
   resume (terminal verdicts skipped, INCOMPLETE retried). **Detect via liveness +
   verdict *type*, not ledger counts**: a wall of fast no-verdict INCOMPLETEs with 0
   patch bytes is the auth-death signature; the too-clean "deprived arm loses 31-0" is
   the red flag, same as the round-1 contamination.

**Meta-principle:** trust *liveness and verdict type*, not row counts. A ledger can
read `done=0` because the monitor points at the wrong file, because the process never
relaunched, or because every call auth-died — three different bugs, one symptom.
Cross-check the process table and the verdict detail before concluding "stalled."
