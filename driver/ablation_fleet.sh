#!/bin/bash
# ablation_fleet.sh -- run the untyped (/ask) ablation arm sharded across N EC2 boxes.
# Adaptation of run_fleet.sh for prereg-pro-v1-untyped. The untyped arm is the FULL headline
# pipeline (Sonnet generator + GPT-5.5 codex challenger + gate + outer loop) with only the
# inquiry skill swapped (recon -> ask), so it needs the SAME box setup as the headline fleet:
#   (1) claude + codex CLIs (npm global, pinned), (2) Max OAuth + codex auth pushed,
#   (3) git-init the repo root (codex refuses untrusted dirs).
# Each box runs `ablation_run.py --shard i/N` over tasks/ablation_sample.txt (ships via rsync).
# Ledger: runs/scored/untyped_iofN.jsonl (WIN|LOSS|INCOMPLETE). Resume = skip recorded.
#
#   driver/ablation_fleet.sh smoke            # 1 box, 1 instance -- validates install+auth+dispatch+grade
#   driver/ablation_fleet.sh provision <N>    # provision+bootstrap+dispatch N boxes; writes manifest
#   driver/ablation_fleet.sh status           # one-line progress per box (won/lost/incomplete)
#   driver/ablation_fleet.sh checkpoint       # pull current untyped ledgers WITHOUT merging (crash-safety)
#   driver/ablation_fleet.sh delta            # pull + merge -> runs/scored/untyped.jsonl + Delta_typing verdict
#   driver/ablation_fleet.sh teardown         # terminate all boxes + clean SG/keys
#
# Boxes self-terminate at +WATCHDOG_MIN (default 720). Manifest: /tmp/ablation_fleet.manifest
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST=/tmp/ablation_fleet.manifest
SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"
WATCHDOG_MIN="${WATCHDOG_MIN:-720}"
ELIGIBLE="$REPO/runs/audit/eligible.txt"
AUTH_MODE="${AUTH_MODE:-subscription}"   # untyped arm needs Sonnet (Max) + codex (sub)

stage_creds() {
  if [ "$AUTH_MODE" != "subscription" ]; then
    echo "FATAL: ablation_fleet supports AUTH_MODE=subscription only (Max/\$0 OAuth + codex sub)."; exit 1
  fi
  echo "================ AUTH_MODE=subscription  ->  billing: Max/\$0 (OAuth) + codex sub ================"
  CLAUDE_CREDS=/tmp/claude_credentials.json
  security find-generic-password -s "Claude Code-credentials" -w > "$CLAUDE_CREDS" 2>/dev/null \
    || { echo "FATAL: could not read 'Claude Code-credentials' from keychain"; exit 1; }
  [ -s "$HOME/.codex/auth.json" ] || { echo "FATAL: ~/.codex/auth.json missing (codex not logged in)"; exit 1; }
  [ -s "$REPO/tasks/ablation_sample.txt" ] || { echo "FATAL: tasks/ablation_sample.txt missing (driver/ablation_bayes.py sample)"; exit 1; }
}

setup_box() {  # $1=box-name -- rsync tree, push auth, install CLIs, bootstrap, preflight
  local NAME="$1"
  . /tmp/${NAME}.env; local PEM=/tmp/${KEY}.pem
  rsync -az -e "$SSH -i $PEM" --exclude .venv --exclude .git --exclude runs --exclude scratch \
    "$REPO/" ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/ >/dev/null 2>&1
  $SSH -i $PEM ec2-user@${PUBIP} "mkdir -p ~/.claude ~/.codex ~/swebench-pro/runs/audit ~/swebench-pro/runs/scored" 2>/dev/null
  scp -o StrictHostKeyChecking=no -i $PEM "$CLAUDE_CREDS"          "ec2-user@${PUBIP}:/home/ec2-user/.claude/.credentials.json" >/dev/null 2>&1
  scp -o StrictHostKeyChecking=no -i $PEM "$HOME/.codex/auth.json" "ec2-user@${PUBIP}:/home/ec2-user/.codex/auth.json"          >/dev/null 2>&1
  [ -s "$ELIGIBLE" ] && scp -o StrictHostKeyChecking=no -i $PEM "$ELIGIBLE" "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/audit/eligible.txt" >/dev/null 2>&1
  $SSH -i $PEM ec2-user@${PUBIP} "
    set -e
    sudo shutdown -c 2>/dev/null; sudo shutdown -h +${WATCHDOG_MIN} >/dev/null 2>&1
    sudo dnf install -y -q git python3.11 python3.11-pip nodejs npm >/dev/null 2>&1
    command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
    export PATH=\$HOME/.local/bin:\$PATH
    npm config set prefix ~/.npm-global 2>/dev/null
    export PATH=\$HOME/.npm-global/bin:\$PATH
    npm i -g @anthropic-ai/claude-code@2.1.150 @openai/codex@0.134.0 >/dev/null 2>&1
    cd ~/swebench-pro
    git init -q 2>/dev/null || true   # codex refuses untrusted (non-git) dirs
    UV_PYTHON=3.11 bash driver/bootstrap.sh >/tmp/boot.log 2>&1 && echo BOOT_OK || (tail -3 /tmp/boot.log; exit 1)
    . driver/.proenv
    claude --version >/dev/null 2>&1 && codex --version >/dev/null 2>&1 || { echo 'CLI_PREFLIGHT_FAIL'; exit 1; }
    [ -s ~/.claude/.credentials.json ] || { echo 'AUTH_ASSERT_FAIL: no OAuth creds'; exit 1; }
    [ -s ~/.codex/auth.json ] || { echo 'AUTH_ASSERT_FAIL: no codex auth'; exit 1; }
    [ -s tasks/ablation_sample.txt ] || { echo 'SAMPLE_ASSERT_FAIL: no ablation_sample.txt'; exit 1; }
    echo READY_${NAME}
  "
}

setup_and_dispatch() {  # $1=name $2=i $3=N [$4=extra]
  local NAME="$1" I="$2" N="$3" EXTRA="${4:-}"
  setup_box "$NAME" || return 1
  . /tmp/${NAME}.env; local PEM=/tmp/${KEY}.pem
  local ckpt="$REPO/runs/scored/shards/untyped_${I}of${N}.jsonl"
  [ -f "$ckpt" ] && scp -o StrictHostKeyChecking=no -i $PEM "$ckpt" \
    "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/scored/untyped_${I}of${N}.jsonl" >/dev/null 2>&1
  $SSH -i $PEM ec2-user@${PUBIP} "
    cd ~/swebench-pro && . driver/.proenv
    export PATH=\$HOME/.local/bin:\$HOME/.npm-global/bin:\$PATH CLAUDE_SUBSCRIPTION=1
    nohup env PATH=\$PATH CLAUDE_SUBSCRIPTION=1 \$PY driver/ablation_run.py --shard ${I}/${N} ${EXTRA} > ~/ablation_shard.log 2>&1 &
    echo DISPATCHED ${NAME} shard ${I}/${N} pid \$! watchdog +${WATCHDOG_MIN}m ${EXTRA}
  "
}

provision_boxes() {  # $1=N
  local N="$1"; : > $MANIFEST
  echo "=== provisioning $N untyped-arm boxes (EBS 100G, parallel) ==="
  for i in $(seq 1 $N); do EBS_GB=100 bash "$REPO/driver/provision_box.sh" abl$i >/tmp/prov_abl$i.log 2>&1 & done
  wait
  for i in $(seq 1 $N); do
    ip=$(grep PUBIP /tmp/abl$i.env 2>/dev/null | cut -d= -f2)
    [ -n "${ip:-}" ] && echo "abl$i $i $N $ip" >> $MANIFEST || echo "PROVISION FAILED abl$i: $(tail -1 /tmp/prov_abl$i.log)"
  done
}

case "${1:-}" in
  smoke)
    stage_creds
    echo "=== SMOKE: 1 box, 1 instance (validates /ask -> craft+codex -> gate -> official grade) ==="
    provision_boxes 1
    while read -r NAME I NN IP; do setup_and_dispatch "$NAME" 1 1 "--limit 1"; done < $MANIFEST
    echo "smoke dispatched; poll: driver/ablation_fleet.sh status"
    ;;
  provision)
    N="${2:?usage: ablation_fleet.sh provision <N>}"
    stage_creds
    provision_boxes "$N"
    echo "=== bootstrap + dispatch (parallel) ==="
    while read -r NAME I NN IP; do setup_and_dispatch "$NAME" "$I" "$NN" & done < $MANIFEST
    wait
    echo "=== manifest ==="; cat $MANIFEST
    echo "run dispatched; poll: driver/ablation_fleet.sh status ; verdict: driver/ablation_fleet.sh delta"
    ;;
  status)
    while read -r NAME I N IP; do
      . /tmp/${NAME}.env; PEM=/tmp/${KEY}.pem
      out=$($SSH -n -i $PEM ec2-user@${PUBIP} "L=~/swebench-pro/runs/scored/untyped_${I}of${N}.jsonl; echo done=\$(wc -l < \$L 2>/dev/null || echo 0); echo won=\$(grep -c '\"state\": \"WIN\"' \$L 2>/dev/null || echo 0); echo lost=\$(grep -c '\"state\": \"LOSS\"' \$L 2>/dev/null || echo 0); echo inc=\$(grep -c '\"state\": \"INCOMPLETE\"' \$L 2>/dev/null || echo 0)" 2>/dev/null)
      echo "  $NAME (shard $I/$N): $(echo "$out" | tr '\n' ' ')"
    done < $MANIFEST
    ;;
  checkpoint)
    mkdir -p "$REPO/runs/scored/shards"
    while read -r NAME I N IP; do
      . /tmp/${NAME}.env; PEM=/tmp/${KEY}.pem
      scp -o StrictHostKeyChecking=no -i $PEM "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/scored/untyped_${I}of${N}.jsonl" \
        "$REPO/runs/scored/shards/untyped_${I}of${N}.jsonl" 2>/dev/null && echo "ckpt $NAME $(wc -l < "$REPO/runs/scored/shards/untyped_${I}of${N}.jsonl" 2>/dev/null)"
    done < $MANIFEST
    ;;
  delta)
    mkdir -p "$REPO/runs/scored/shards"
    while read -r NAME I N IP; do
      . /tmp/${NAME}.env; PEM=/tmp/${KEY}.pem
      scp -o StrictHostKeyChecking=no -i $PEM "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/scored/untyped_${I}of${N}.jsonl" \
        "$REPO/runs/scored/shards/untyped_${I}of${N}.jsonl" 2>/dev/null && echo "pulled $NAME"
    done < $MANIFEST
    python3 - "$REPO" <<'PY'
import sys, json, pathlib, glob
repo = pathlib.Path(sys.argv[1]); d = repo/"runs"/"scored"
recs = {}
for f in glob.glob(str(d/"shards"/"untyped_*.jsonl")):
    for l in open(f):
        try: r = json.loads(l); recs[r["instance_id"]] = r
        except Exception: pass
(d/"untyped.jsonl").write_text("".join(json.dumps(recs[i])+"\n" for i in sorted(recs)))
print(f"merged {len(recs)} untyped records -> runs/scored/untyped.jsonl")
PY
    "$REPO/.venv/bin/python" "$REPO/driver/ablation_bayes.py" status
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
  *) echo "usage: ablation_fleet.sh {smoke|provision <N>|status|checkpoint|delta|teardown}"; exit 1 ;;
esac
