#!/bin/bash
# audit_fleet.sh — run the §6 full-731 gold-patch defect audit sharded across N EC2 boxes.
# Gold-grade only ($0 tokens, no model auth needed — unlike the agent run). Each box runs a
# deterministic stripe `pro_run.py --mode audit --shard i/N` of the frozen order (prereg §3).
#
#   driver/audit_fleet.sh provision <N>   # provision+bootstrap+dispatch N boxes; writes manifest
#   driver/audit_fleet.sh status          # one-line progress per box
#   driver/audit_fleet.sh collect         # pull+merge ledgers -> runs/audit/{eligible.txt,defects.jsonl}
#   driver/audit_fleet.sh teardown        # terminate all boxes + clean SG/keys
#
# Boxes self-terminate at +600min (provision watchdog) as a backstop. Manifest: /tmp/audit_fleet.manifest
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST=/tmp/audit_fleet.manifest
SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"

WATCHDOG_MIN="${WATCHDOG_MIN:-720}"   # audit needs ~6-8h; provision_box default +180 killed it mid-run

setup_and_dispatch() {  # $1=box-name $2=shard-i $3=N
  local NAME="$1" I="$2" N="$3"
  . /tmp/${NAME}.env; local PEM=/tmp/${KEY}.pem
  rsync -az -e "$SSH -i $PEM" --exclude .venv --exclude .git --exclude runs --exclude scratch \
    "$REPO/" ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/ >/dev/null 2>&1
  # RESUME-SEED: push the local checkpoint ledger (if any) so pro_run skips already-graded
  # instances instead of restarting — survives a box death mid-shard.
  local ckpt="$REPO/runs/audit/shards/audit_${I}of${N}.jsonl"
  $SSH -i $PEM ec2-user@${PUBIP} "mkdir -p ~/swebench-pro/runs/audit" 2>/dev/null
  [ -f "$ckpt" ] && scp -o StrictHostKeyChecking=no -i $PEM "$ckpt" \
    "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/audit/audit_${I}of${N}.jsonl" >/dev/null 2>&1
  $SSH -i $PEM ec2-user@${PUBIP} "
    set -e
    sudo shutdown -c 2>/dev/null; sudo shutdown -h +${WATCHDOG_MIN} >/dev/null 2>&1   # extend watchdog past +180 default
    sudo dnf install -y -q git python3.11 python3.11-pip >/dev/null 2>&1
    command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
    export PATH=\$HOME/.local/bin:\$PATH
    cd ~/swebench-pro && UV_PYTHON=3.11 bash driver/bootstrap.sh >/tmp/boot.log 2>&1 && echo BOOT_OK || (tail -3 /tmp/boot.log; exit 1)
    . driver/.proenv
    nohup \$PY driver/pro_run.py --mode audit --shard ${I}/${N} > ~/audit_shard.log 2>&1 &
    echo DISPATCHED ${NAME} shard ${I}/${N} pid \$! watchdog +${WATCHDOG_MIN}m
  "
}

case "${1:-}" in
  provision)
    N="${2:?usage: audit_fleet.sh provision <N>}"
    : > $MANIFEST
    echo "=== provisioning $N audit boxes (EBS 100G, parallel) ==="
    for i in $(seq 1 $N); do EBS_GB=100 bash "$REPO/driver/provision_box.sh" audit$i >/tmp/prov_$i.log 2>&1 & done
    wait
    for i in $(seq 1 $N); do
      ip=$(grep PUBIP /tmp/audit$i.env 2>/dev/null | cut -d= -f2)
      [ -n "${ip:-}" ] && echo "audit$i $i $N $ip" >> $MANIFEST || echo "PROVISION FAILED audit$i: $(tail -1 /tmp/prov_$i.log)"
    done
    echo "=== bootstrap + dispatch (parallel) ==="
    while read -r NAME I NN IP; do setup_and_dispatch "$NAME" "$I" "$NN" & done < $MANIFEST
    wait
    echo "=== manifest ==="; cat $MANIFEST
    echo "audit dispatched; poll with: driver/audit_fleet.sh status"
    ;;
  status)
    # ssh -n: do NOT let ssh consume the `while read` manifest stream (else only box 1 polls)
    while read -r NAME I N IP; do
      . /tmp/${NAME}.env; PEM=/tmp/${KEY}.pem
      out=$($SSH -n -i $PEM ec2-user@${PUBIP} "L=~/swebench-pro/runs/audit/audit_${I}of${N}.jsonl; echo graded=\$(wc -l < \$L 2>/dev/null || echo 0); echo defects=\$(grep -c '\"state\": \"defect\"' \$L 2>/dev/null || echo 0)" 2>/dev/null)
      total=$(( (731 + N - 1 - (I-1)) / N ))
      echo "  $NAME (shard $I/$N): $(echo "$out" | tr '\n' ' ') /~${total}"
    done < $MANIFEST
    ;;
  checkpoint)  # pull current ledgers to local WITHOUT merging/writing final lists — for periodic
    mkdir -p "$REPO/runs/audit/shards"  # crash-safety during the run; survives a box death
    while read -r NAME I N IP; do
      . /tmp/${NAME}.env; PEM=/tmp/${KEY}.pem
      scp -o StrictHostKeyChecking=no -i $PEM "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/audit/audit_${I}of${N}.jsonl" \
        "$REPO/runs/audit/shards/audit_${I}of${N}.jsonl" 2>/dev/null && echo "ckpt $NAME $(wc -l < "$REPO/runs/audit/shards/audit_${I}of${N}.jsonl" 2>/dev/null)"
    done < $MANIFEST
    ;;
  collect)
    mkdir -p "$REPO/runs/audit/shards"
    while read -r NAME I N IP; do
      . /tmp/${NAME}.env; PEM=/tmp/${KEY}.pem
      scp -o StrictHostKeyChecking=no -i $PEM "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/audit/audit_${I}of${N}.jsonl" \
        "$REPO/runs/audit/shards/audit_${I}of${N}.jsonl" 2>/dev/null && echo "pulled $NAME"
    done < $MANIFEST
    python3 - "$REPO" <<'PY'
import sys, json, pathlib, glob
repo = pathlib.Path(sys.argv[1]); d = repo/"runs"/"audit"
recs = {}
for f in glob.glob(str(d/"shards"/"audit_*.jsonl")):
    for l in open(f):
        try: r = json.loads(l); recs[r["instance_id"]] = r
        except Exception: pass
from collections import Counter
c = Counter(r["state"] for r in recs.values())
elig = sorted(i for i,r in recs.items() if r["state"]=="eligible")
defs = [r for r in recs.values() if r["state"]=="defect"]
inc  = sorted(i for i,r in recs.items() if r["state"]=="incomplete")
(d/"eligible.txt").write_text("\n".join(elig)+"\n")
(d/"defects.jsonl").write_text("".join(json.dumps(r)+"\n" for r in defs))
print(f"merged {len(recs)} of 731 — {dict(c)}")
print(f"  eligible={len(elig)}  defects={len(defs)}  incomplete={len(inc)}")
if inc: print("  INCOMPLETE (retry): "+" ".join(inc[:15]))
if len(recs) < 731: print(f"  WARNING: {731-len(recs)} instances ungraded — shards not complete")
PY
    ;;
  teardown)
    while read -r NAME I N IP; do
      . /tmp/${NAME}.env
      aws ec2 terminate-instances --instance-ids $IID --region $REGION >/dev/null 2>&1
      aws ec2 delete-security-group --group-id $SG --region $REGION 2>/dev/null
      aws ec2 delete-key-pair --key-name $KEY --region $REGION 2>/dev/null
      echo "terminated $NAME ($IID)"
    done < $MANIFEST
    ;;
  *) echo "usage: audit_fleet.sh {provision <N>|status|collect|teardown}"; exit 1 ;;
esac
