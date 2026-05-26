#!/bin/bash
# run_fleet.sh — run the §2 scored measurement (agent loop) sharded across N EC2 boxes.
# Sibling to audit_fleet.sh. The audit fleet gold-grades at $0 with no model auth; THIS fleet runs
# the recon→craft→audit agent (Sonnet 4.5 generator + GPT-5.5 codex volley), so it must additionally:
#   (1) install the claude + codex CLIs on each box (npm global),
#   (2) push the Max OAuth creds (claude) and codex auth so the run bills Max/$0 not PAYG,
#   (3) git-init the repo root (codex refuses untrusted dirs),
#   (4) ship runs/audit/eligible.txt (the 728 denominator) — rsync excludes runs/, so it's scp'd.
# Each box runs `pro_run.py --mode run --shard i/N --eligible runs/audit/eligible.txt` over the frozen
# order (prereg §3). Ledger: runs/scored/run_iofN.jsonl (states WIN|LOSS|INCOMPLETE). Resume = skip recorded.
#
#   driver/run_fleet.sh smoke               # 1 box, 1 instance — validates install+auth+dispatch+grade
#   driver/run_fleet.sh provision <N>       # provision+bootstrap+dispatch N boxes; writes manifest
#   driver/run_fleet.sh status              # one-line progress per box (won/lost/incomplete)
#   driver/run_fleet.sh checkpoint          # pull current run ledgers WITHOUT merging (crash-safety)
#   driver/run_fleet.sh collect             # pull+merge ledgers -> runs/scored/run.jsonl + scoreboard
#   driver/run_fleet.sh teardown            # terminate all boxes + clean SG/keys
#
# Boxes self-terminate at +WATCHDOG_MIN (default 720) as a backstop. Manifest: /tmp/run_fleet.manifest
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
MANIFEST=/tmp/run_fleet.manifest
SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10"
WATCHDOG_MIN="${WATCHDOG_MIN:-720}"
ELIGIBLE="$REPO/runs/audit/eligible.txt"

# --- local-side: extract Max OAuth creds from the macOS keychain to a temp file for scp ---
# claude reads ~/.claude/.credentials.json on Linux; on this Mac it lives in the keychain.
stage_creds() {
  CLAUDE_CREDS=/tmp/claude_credentials.json
  security find-generic-password -s "Claude Code-credentials" -w > "$CLAUDE_CREDS" 2>/dev/null \
    || { echo "FATAL: could not read 'Claude Code-credentials' from keychain"; exit 1; }
  [ -s "$HOME/.codex/auth.json" ] || { echo "FATAL: ~/.codex/auth.json missing (codex not logged in)"; exit 1; }
  [ -s "$ELIGIBLE" ] || { echo "FATAL: $ELIGIBLE missing — run the §6 audit first"; exit 1; }
}

# Bring a box to READY: rsync the tree, push auth + eligible list, install CLIs, bootstrap, preflight.
# Leaves no agent running — used by both the static dispatch path AND the coordinator (which then
# feeds the box one instance at a time). Re-runnable (idempotent installs).  $1=box-name
setup_box() {
  local NAME="$1"
  . /tmp/${NAME}.env; local PEM=/tmp/${KEY}.pem
  rsync -az -e "$SSH -i $PEM" --exclude .venv --exclude .git --exclude runs --exclude scratch \
    "$REPO/" ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/ >/dev/null 2>&1
  # auth + eligible list (rsync excludes runs/, so these go explicitly)
  $SSH -i $PEM ec2-user@${PUBIP} "mkdir -p ~/.claude ~/.codex ~/swebench-pro/runs/audit ~/swebench-pro/runs/scored" 2>/dev/null
  scp -o StrictHostKeyChecking=no -i $PEM "$CLAUDE_CREDS"          "ec2-user@${PUBIP}:/home/ec2-user/.claude/.credentials.json" >/dev/null 2>&1
  scp -o StrictHostKeyChecking=no -i $PEM "$HOME/.codex/auth.json" "ec2-user@${PUBIP}:/home/ec2-user/.codex/auth.json"          >/dev/null 2>&1
  scp -o StrictHostKeyChecking=no -i $PEM "$ELIGIBLE"             "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/audit/eligible.txt" >/dev/null 2>&1
  $SSH -i $PEM ec2-user@${PUBIP} "
    set -e
    sudo shutdown -c 2>/dev/null; sudo shutdown -h +${WATCHDOG_MIN} >/dev/null 2>&1
    sudo dnf install -y -q git python3.11 python3.11-pip nodejs npm >/dev/null 2>&1
    command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
    export PATH=\$HOME/.local/bin:\$PATH
    npm config set prefix ~/.npm-global 2>/dev/null
    export PATH=\$HOME/.npm-global/bin:\$PATH
    command -v claude >/dev/null || npm i -g @anthropic-ai/claude-code >/dev/null 2>&1
    command -v codex  >/dev/null || npm i -g @openai/codex            >/dev/null 2>&1
    cd ~/swebench-pro
    git init -q 2>/dev/null || true   # codex refuses untrusted (non-git) dirs
    UV_PYTHON=3.11 bash driver/bootstrap.sh >/tmp/boot.log 2>&1 && echo BOOT_OK || (tail -3 /tmp/boot.log; exit 1)
    . driver/.proenv
    claude --version >/dev/null 2>&1 && codex --version >/dev/null 2>&1 || { echo 'CLI_PREFLIGHT_FAIL'; exit 1; }
    echo READY_${NAME}
  "
}

setup_and_dispatch() {  # static path: setup_box then nohup a whole shard.  $1=name $2=i $3=N [$4=extra]
  local NAME="$1" I="$2" N="$3" EXTRA="${4:-}"
  setup_box "$NAME" || return 1
  . /tmp/${NAME}.env; local PEM=/tmp/${KEY}.pem
  local ckpt="$REPO/runs/scored/shards/run_${I}of${N}.jsonl"
  [ -f "$ckpt" ] && scp -o StrictHostKeyChecking=no -i $PEM "$ckpt" \
    "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/scored/run_${I}of${N}.jsonl" >/dev/null 2>&1
  $SSH -i $PEM ec2-user@${PUBIP} "
    cd ~/swebench-pro && . driver/.proenv
    export PATH=\$HOME/.local/bin:\$HOME/.npm-global/bin:\$PATH CLAUDE_SUBSCRIPTION=1
    nohup env PATH=\$PATH CLAUDE_SUBSCRIPTION=1 \$PY driver/pro_run.py --mode run --shard ${I}/${N} --eligible runs/audit/eligible.txt ${EXTRA} > ~/run_shard.log 2>&1 &
    echo DISPATCHED ${NAME} shard ${I}/${N} pid \$! watchdog +${WATCHDOG_MIN}m ${EXTRA}
  "
}

provision_boxes() {  # $1=N
  local N="$1"
  : > $MANIFEST
  echo "=== provisioning $N run boxes (EBS 100G, parallel) ==="
  for i in $(seq 1 $N); do EBS_GB=100 bash "$REPO/driver/provision_box.sh" run$i >/tmp/prov_run$i.log 2>&1 & done
  wait
  for i in $(seq 1 $N); do
    ip=$(grep PUBIP /tmp/run$i.env 2>/dev/null | cut -d= -f2)
    [ -n "${ip:-}" ] && echo "run$i $i $N $ip" >> $MANIFEST || echo "PROVISION FAILED run$i: $(tail -1 /tmp/prov_run$i.log)"
  done
}

case "${1:-}" in
  smoke)
    stage_creds
    echo "=== SMOKE: 1 box, 1 instance (validates install+auth+dispatch+grade) ==="
    provision_boxes 1
    while read -r NAME I NN IP; do setup_and_dispatch "$NAME" 1 1 "--limit 1"; done < $MANIFEST
    echo "smoke dispatched; poll: driver/run_fleet.sh status  (then teardown)"
    ;;
  provision)
    N="${2:?usage: run_fleet.sh provision <N>}"
    stage_creds
    provision_boxes "$N"
    echo "=== bootstrap + dispatch (parallel) ==="
    while read -r NAME I NN IP; do setup_and_dispatch "$NAME" "$I" "$NN" & done < $MANIFEST
    wait
    echo "=== manifest ==="; cat $MANIFEST
    echo "run dispatched; poll: driver/run_fleet.sh status"
    ;;
  status)
    while read -r NAME I N IP; do
      . /tmp/${NAME}.env; PEM=/tmp/${KEY}.pem
      out=$($SSH -n -i $PEM ec2-user@${PUBIP} "L=~/swebench-pro/runs/scored/run_${I}of${N}.jsonl; echo done=\$(wc -l < \$L 2>/dev/null || echo 0); echo won=\$(grep -c '\"state\": \"WIN\"' \$L 2>/dev/null || echo 0); echo lost=\$(grep -c '\"state\": \"LOSS\"' \$L 2>/dev/null || echo 0); echo inc=\$(grep -c '\"state\": \"INCOMPLETE\"' \$L 2>/dev/null || echo 0)" 2>/dev/null)
      total=$(( (731 + N - 1 - (I-1)) / N ))
      echo "  $NAME (shard $I/$N): $(echo "$out" | tr '\n' ' ') /~${total} eligible-subset"
    done < $MANIFEST
    ;;
  checkpoint)
    mkdir -p "$REPO/runs/scored/shards"
    while read -r NAME I N IP; do
      . /tmp/${NAME}.env; PEM=/tmp/${KEY}.pem
      scp -o StrictHostKeyChecking=no -i $PEM "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/scored/run_${I}of${N}.jsonl" \
        "$REPO/runs/scored/shards/run_${I}of${N}.jsonl" 2>/dev/null && echo "ckpt $NAME $(wc -l < "$REPO/runs/scored/shards/run_${I}of${N}.jsonl" 2>/dev/null)"
    done < $MANIFEST
    ;;
  collect)
    mkdir -p "$REPO/runs/scored/shards"
    while read -r NAME I N IP; do
      . /tmp/${NAME}.env; PEM=/tmp/${KEY}.pem
      scp -o StrictHostKeyChecking=no -i $PEM "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/scored/run_${I}of${N}.jsonl" \
        "$REPO/runs/scored/shards/run_${I}of${N}.jsonl" 2>/dev/null && echo "pulled $NAME"
    done < $MANIFEST
    python3 - "$REPO" <<'PY'
import sys, json, pathlib, glob
from collections import Counter
repo = pathlib.Path(sys.argv[1]); d = repo/"runs"/"scored"
elig = set((repo/"runs"/"audit"/"eligible.txt").read_text().split())
recs = {}
for f in glob.glob(str(d/"shards"/"run_*.jsonl")):
    for l in open(f):
        try: r = json.loads(l); recs[r["instance_id"]] = r
        except Exception: pass
c = Counter(r["state"] for r in recs.values())
won = [i for i,r in recs.items() if r["state"]=="WIN"]
inc = sorted(i for i,r in recs.items() if r["state"]=="INCOMPLETE")
(d/"run.jsonl").write_text("".join(json.dumps(recs[i])+"\n" for i in sorted(recs)))
graded = [i for i in recs if recs[i]["state"] in ("WIN","LOSS")]
print(f"merged {len(recs)} of {len(elig)} eligible — {dict(c)}")
print(f"  WINS={len(won)}  graded(WIN+LOSS)={len(graded)}  resolve-rate={len(won)/max(1,len(graded)):.3f}")
if inc: print(f"  INCOMPLETE (re-run, prereg §4): {len(inc)} — "+" ".join(inc[:10]))
missing = len(elig) - len(graded) - len(inc)
if missing>0: print(f"  WARNING: {missing} eligible instances ungraded — run not complete")
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
  setup-box)  # provision ONE box and bring it to READY (no dispatch) — used by coordinator.py
    NAME="${2:?usage: run_fleet.sh setup-box <name>}"
    stage_creds
    EBS_GB=100 bash "$REPO/driver/provision_box.sh" "$NAME" >/tmp/prov_${NAME}.log 2>&1 \
      || { echo "PROVISION_FAIL ${NAME}: $(tail -1 /tmp/prov_${NAME}.log)"; exit 1; }
    setup_box "$NAME"   # prints READY_<name> or fails
    ;;
  kill-box)  # terminate ONE box + clean its SG/key — used by coordinator.py on box death
    NAME="${2:?usage: run_fleet.sh kill-box <name>}"
    [ -f /tmp/${NAME}.env ] || { echo "no env for ${NAME}"; exit 0; }
    . /tmp/${NAME}.env
    aws ec2 terminate-instances --instance-ids $IID --region $REGION >/dev/null 2>&1
    aws ec2 delete-security-group --group-id $SG --region $REGION 2>/dev/null
    aws ec2 delete-key-pair --key-name $KEY --region $REGION 2>/dev/null
    echo "terminated ${NAME} ($IID)"
    ;;
  *) echo "usage: run_fleet.sh {smoke|provision <N>|setup-box <name>|kill-box <name>|status|checkpoint|collect|teardown}"; exit 1 ;;
esac
