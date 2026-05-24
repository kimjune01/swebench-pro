#!/bin/bash
# local_iso.sh — isolate ONE SWE-bench instance as a local container for hands-on
# iteration. Mac/OrbStack translation of the driver's setup→warm→helpers flow:
# no ssh, no sudo, x86_64 images run under --platform linux/amd64 emulation.
#
# Usage:  driver/local_iso.sh <instance_id> [task.json]
#   e.g.  driver/local_iso.sh django__django-15987
#         (defaults to tasks/not_won/<instance_id>.json)
#
# Produces under iso/<iid>/:
#   cid           — running container id (SUT, offline-able)
#   failbase.txt  — fail-on-base capture (audit's pre-existing-failure baseline)
#   gate          — run the official FAIL_TO_PASS/PASS_TO_PASS test_cmd in the container
#   box           — run an arbitrary command at repo root in the container
#
# Iterate: edit via ./iso/<iid>/box '<cmd>', verify via ./iso/<iid>/gate.
# Tear down: docker kill $(cat iso/<iid>/cid)
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PY:-$REPO/../swebench-verified/.venv/bin/python}"
PLATFORM="${PLATFORM:-linux/amd64}"

iid="${1:?usage: local_iso.sh <instance_id> [task.json]}"
task="${2:-$REPO/tasks/not_won/$iid.json}"
[ -f "$task" ] || { echo "no task json: $task" >&2; exit 1; }

read -r IMG ROOT ACT < <("$PY" - "$task" "$iid" <<'PYEOF'
import json,sys
task,iid=sys.argv[1],sys.argv[2]
d=next(t for t in json.load(open(task)) if t["instance_id"]==iid)
print(d["image_name"].replace("docker.io/",""), d.get("repo_dir","/testbed"),
      d.get("env_activate","").replace(" ","\x1f"))
PYEOF
)
ACT="${ACT//$'\x1f'/ }"
TC="$("$PY" -c "import json,sys; d=next(t for t in json.load(open(sys.argv[1])) if t['instance_id']==sys.argv[2]); print(d['install_config']['test_cmd'])" "$task" "$iid")"

OUT="$REPO/iso/$iid"; mkdir -p "$OUT"
pre=""; [ -n "$ACT" ] && pre="$ACT 2>/dev/null; "

echo ">> pull $IMG (--platform $PLATFORM, emulated)"
docker pull --platform "$PLATFORM" "$IMG" 2>&1 | tail -1

echo ">> run container"
cid=$(docker run -d --platform "$PLATFORM" "$IMG" sleep infinity)
echo "$cid" > "$OUT/cid"

echo ">> apply test patch (staged in /tmp, committed — keeps tp.patch out of the tree)"
"$PY" -c "import json,sys; d=next(t for t in json.load(open(sys.argv[1])) if t['instance_id']==sys.argv[2]); sys.stdout.write(d['test_patch'])" "$task" "$iid" \
  | docker exec -i "$cid" bash -c 'cat > /tmp/tp.patch'
docker exec "$cid" bash -lc "cd $ROOT && git apply /tmp/tp.patch && \
  git -c user.email=r4@x -c user.name=r4 add -A && \
  git -c user.email=r4@x -c user.name=r4 commit -q -m testpatch && \
  echo APPLIED \$(git rev-parse HEAD)"

# gate: run the official test command in the container
cat > "$OUT/gate" <<GEOF
#!/bin/bash
docker exec $cid bash -lc "cd $ROOT && ${pre}$TC 2>&1 | tail -\${1:-200}"
GEOF
chmod +x "$OUT/gate"

# box: run an arbitrary command at repo root in the container
cat > "$OUT/box" <<BEOF
#!/bin/bash
docker exec $cid bash -lc "cd $ROOT && ${pre}\$*"
BEOF
chmod +x "$OUT/box"

echo ">> warm + capture fail-on-base"
{ echo "\$ $TC"; echo; "$OUT/gate" 200; } > "$OUT/failbase.txt" 2>&1 || true

echo
echo "ready: $OUT"
echo "  gate:     $OUT/gate"
echo "  box:      $OUT/box '<cmd>'"
echo "  failbase: $OUT/failbase.txt"
echo "  teardown: docker kill $cid"
