#!/usr/bin/env bash
# pull_artifacts.sh — pull per-instance run artifacts off live fleet boxes to the laptop so they
# survive box teardown. READ-ONLY on the box side (rsync pull) -> safe to run during a live
# coordinator run.
#
# Fulfills prereg §10 provenance (captured diff + agent logs + per-box ledger), which the
# coordinator's verdict-only checkpoint does NOT capture. The artifacts accumulate on the box
# (instance-named, not overwritten), so even one pull before teardown recovers full history; the
# loop just bounds worst-case loss to one interval.
#
# Operator infra (long-running daemon). Re-reads /tmp/coord*.env each cycle, so it follows
# reprovisioned boxes automatically.
#
# Bring it up:
#   cd /path/to/swebench-pro
#   nohup bash driver/pull_artifacts.sh > runs/scored/artifact_puller.log 2>&1 &
#
# Tail:  tail -f runs/scored/artifact_puller.log
# Stop:  pkill -f pull_artifacts.sh
#
# Env: INTERVAL (seconds between cycles, default 600).
set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DEST="$REPO/runs/scored/artifacts"
INTERVAL="${INTERVAL:-600}"
SSH="ssh -o StrictHostKeyChecking=no -o ConnectTimeout=15"
log(){ echo "[$(date +%H:%M:%S)] $*"; }
mkdir -p "$DEST"
log "artifact puller up -> $DEST (interval ${INTERVAL}s)"
while true; do
  for env in /tmp/coord*.env; do
    [ -f "$env" ] || continue
    ( NAME="$(basename "$env" .env)"; . "$env"; PEM="/tmp/${KEY}.pem"; [ -f "$PEM" ] || exit 0
      d="$DEST/$NAME"; mkdir -p "$d/patches" "$d/claude" "$d/codex"
      # captured source-only diffs (the patches; most important artifact)
      rsync -az --timeout=60 -e "$SSH -i $PEM" \
        "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/dev/pro_patch_instance_*.diff" "$d/patches/" 2>/dev/null
      # per-box ledger (redundant with authoritative laptop ledger, kept for cross-check)
      rsync -az --timeout=60 -e "$SSH -i $PEM" \
        "ec2-user@${PUBIP}:/home/ec2-user/swebench-pro/runs/scored/run.jsonl" "$d/run_${NAME}.jsonl" 2>/dev/null
      # agent trajectories (claude recon/craft/audit sessions + codex challenger sessions)
      rsync -az --timeout=120 -e "$SSH -i $PEM" \
        "ec2-user@${PUBIP}:/home/ec2-user/.claude/projects/" "$d/claude/" 2>/dev/null
      rsync -az --timeout=120 -e "$SSH -i $PEM" \
        "ec2-user@${PUBIP}:/home/ec2-user/.codex/sessions/" "$d/codex/" 2>/dev/null
      n=$(ls "$d"/patches/*.diff 2>/dev/null | wc -l | tr -d ' ')
      log "$NAME ($PUBIP): patches=$n claude=$(du -sh "$d/claude" 2>/dev/null | cut -f1)"
    )
  done
  log "cycle done; sleep ${INTERVAL}s"
  sleep "$INTERVAL"
done
