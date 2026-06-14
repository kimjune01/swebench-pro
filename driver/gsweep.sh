#!/bin/bash
# Diagnosis-accuracy sweep: run G (and optionally T) recon-only on candidate instances where
# M diagnosed well, score each handoff vs the gold oracle. Finds instances where M's recall > G's
# (= methodeutic reasoning more accurate than generic). M's frozen recall is read from
# /tmp/M_under_recall.json. Output: /tmp/gsweep_results.tsv  (iid  M_recall  G_recall  T_recall)
set -u
cd "$(dirname "$0")/.."
export SWEAP_OS_REPO=/tmp/swebench-pro-os CLAUDE_SUBSCRIPTION=1 PLATFORM=linux/amd64
CANDS="${1:-/tmp/gsweep_cands.txt}"
ARMS="${ARMS:-generic}"            # space-sep: "generic" or "generic minimal"
OUT="${GSWEEP_OUT:-/tmp/gsweep_results.tsv}"
PY=.venv/bin/python
[ -f "$OUT" ] || printf "iid\tM\tgeneric\tminimal\n" > "$OUT"

m_recall() { $PY - "$1" <<'PYEOF'
import json,sys
res={r['iid']:r['recall'] for r in json.load(open('/tmp/M_under_recall.json'))}
print(res.get(sys.argv[1],''))
PYEOF
}

while read -r IID; do
  [ -z "$IID" ] && continue
  grep -q "^$IID	" "$OUT" && { echo "skip (done): $IID"; continue; }
  SHORT=$(echo "$IID" | sed 's/.*__//; s/-v.*//' | cut -c1-24)
  TASK="tasks/sweep_${SHORT}.json"
  echo "=== $IID ==="
  if [ ! -f "$TASK" ]; then
    BENCH=pro $PY driver/make_task.py "$IID" "$TASK" 2>&1 | tail -1 || { echo "make_task FAIL"; continue; }
  fi
  MR=$(m_recall "$IID")
  GEN_R=""; MIN_R=""
  for ARM in $ARMS; do
    SK="skills/$ARM/skill.md"
    ARM_NAME=$ARM ARM_SKILL=$SK RECON_ONLY=1 $PY driver/pro_arm.py "$TASK" "$IID" > "/tmp/sweep_${ARM}_${SHORT}.log" 2>&1
    TAG=$(echo "$IID" | tr '/' '_')
    HO="runs/dev/${ARM}_handoff_${TAG}.txt"
    if [ -s "$HO" ]; then
      RC=$($PY driver/diag_oracle.py "$IID" "$HO" --label "$ARM" 2>/dev/null | head -1 | sed -n 's/.*recall=\([0-9.]*\).*/\1/p')
    else
      RC="ERR"
    fi
    [ "$ARM" = "generic" ] && GEN_R="$RC"
    [ "$ARM" = "minimal" ] && MIN_R="$RC"
    echo "  $ARM recall=${RC:-?} (M=$MR)"
  done
  printf "%s\t%s\t%s\t%s\n" "$IID" "$MR" "$GEN_R" "$MIN_R" >> "$OUT"
done < "$CANDS"
echo "=== GSWEEP DONE -> $OUT ==="
cat "$OUT"
