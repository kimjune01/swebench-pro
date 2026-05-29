#!/bin/bash
# scale_fleet.sh — single-knob declarative scale.
#
# Writes the desired-state file; fleet_reconciler.sh picks it up on its next poll
# (default 30s) and converges the fleet.
#
# usage:
#   bash driver/scale_fleet.sh <N>            # graceful (default; preserves in-flight on scale-down)
#   bash driver/scale_fleet.sh <N> --force    # immediate (kills in-flight; for quota emergencies)
#
# Examples:
#   bash driver/scale_fleet.sh 8           # ramp up to 8 (always lossy restart)
#   bash driver/scale_fleet.sh 4           # graceful drain to 4
#   bash driver/scale_fleet.sh 2 --force   # quota emergency: drop to 2 immediately

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

STATE_FILE="runs/scored/fleet_state"

N="${1:-}"
MODE_ARG="${2:-}"
MODE="graceful"
[ "$MODE_ARG" = "--force" ] && MODE="force"

if ! [[ "$N" =~ ^[1-9]$ ]] ; then
  echo "usage: $0 <N> [--force]   where N is 1..8 (vCPU-limited)" >&2
  exit 1
fi

mkdir -p "$(dirname "$STATE_FILE")"
{
  echo "# fleet_state — single source of truth for fleet size. fleet_reconciler.sh reads this each poll."
  echo "desired_boxes=${N}"
  echo "mode=${MODE}"
  echo "updated_at=$(date -u +%FT%TZ)"
} > "$STATE_FILE"

echo "wrote $STATE_FILE: desired_boxes=$N mode=$MODE"
echo "fleet_reconciler will converge on next poll (≤30s)"
