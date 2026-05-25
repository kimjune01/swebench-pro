#!/bin/bash
# pro_batch.sh — run pro_pilot.py over a list of instance_ids, collect official verdicts.
# Dev-mode subset runner (no scoreboard). Usage: pro_batch.sh <name> <iid> [<iid>...]
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-/Users/junekim/Documents/swebench-verified/.venv/bin/python}"
export SWEAP_OS_REPO="${SWEAP_OS_REPO:-/tmp/swebench-pro-os}"
NAME="$1"; shift
mkdir -p "$REPO/tasks/pro" /tmp/smoke
RESULTS="/tmp/smoke/batch_${NAME}.tsv"
printf "instance\tofficial_resolved\tpatch_bytes\tagent_verdict\n" > "$RESULTS"
for iid in "$@"; do
  echo "=== $(date +%H:%M:%S) $iid ==="
  task="$REPO/tasks/pro/b_${NAME}_${iid:9:34}.json"
  BENCH=pro "$PY" "$REPO/driver/make_task.py" "$iid" "$task" >/dev/null 2>&1 \
    || { printf "%s\tMAKE_TASK_FAILED\t\t\n" "$iid" >> "$RESULTS"; continue; }
  out="$("$PY" "$REPO/driver/pro_pilot.py" "$task" "$iid" 2>&1)"
  res="$(printf '%s' "$out" | grep -oE 'OFFICIAL RESOLVED: [A-Za-z]+' | tail -1 | awk '{print $3}')"
  pb="$(printf '%s' "$out" | grep -oE 'patch_bytes: [0-9]+' | tail -1 | awk '{print $2}')"
  av="$(printf '%s' "$out" | grep -oE 'agent_verdict: [A-Za-z_]+' | tail -1 | awk '{print $2}')"
  printf "%s\t%s\t%s\t%s\n" "$iid" "${res:-NONE}" "${pb:-?}" "${av:-?}" >> "$RESULTS"
  echo "  -> resolved=${res:-NONE} patch_bytes=${pb:-?} agent=${av:-?}"
done
echo "=== BATCH DONE: $RESULTS ==="
cat "$RESULTS"
