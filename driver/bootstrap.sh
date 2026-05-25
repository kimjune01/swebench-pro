#!/bin/bash
# bootstrap.sh — one idempotent command to make the Pro pipeline runnable. Pins everything,
# writes the env the other scripts read, and validates itself with the $0 gold smoke. Re-run
# anytime; safe. Nothing below should require a human to guess a path, version, or flag.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SWEAP_OS_REPO="${SWEAP_OS_REPO:-/tmp/swebench-pro-os}"
EVAL_COMMIT="ca10a60a5fcae51e6948ffe1485d4153d421e6c5"
VENV="$REPO/.venv"
SMOKE_IID="instance_ansible__ansible-5e369604e1930b1a2e071fecd7ec5276ebd12cb1-v0f01c69f1e2528b935359cfe578530722bca2c59"

echo ">> [1/4] eval repo @ $SWEAP_OS_REPO (pinned ${EVAL_COMMIT:0:12})"
[ -d "$SWEAP_OS_REPO/.git" ] || git clone -q https://github.com/scaleapi/SWE-bench_Pro-os.git "$SWEAP_OS_REPO"
git -C "$SWEAP_OS_REPO" fetch -q origin "$EVAL_COMMIT" 2>/dev/null || git -C "$SWEAP_OS_REPO" fetch -q --all
git -C "$SWEAP_OS_REPO" checkout -q "$EVAL_COMMIT"

echo ">> [2/4] venv @ $VENV (pinned deps)"
[ -x "$VENV/bin/python" ] || { command -v uv >/dev/null && uv venv "$VENV" >/dev/null || python3 -m venv "$VENV"; }
if ! "$VENV/bin/python" -c "import swebench,datasets,pandas,docker" 2>/dev/null; then
  "$VENV/bin/pip" install -q "swebench==4.1.0" "datasets==4.8.5" "pandas==3.0.3" "docker==7.1.0"
fi

echo ">> [3/4] docker host"
docker version --format '   server {{.Server.Version}} ({{.Server.Arch}})' \
  || { echo "   ERROR: Docker not running. Start Docker/OrbStack (Mac) or run provision.sh (EC2)."; exit 1; }

echo ">> [4/4] write env -> driver/.proenv  (every script sources this; no manual exports)"
printf 'export SWEAP_OS_REPO=%q\nexport PY=%q\n' "$SWEAP_OS_REPO" "$VENV/bin/python" > "$REPO/driver/.proenv"

echo ">> validate: \$0 gold smoke ($SMOKE_IID)"
( . "$REPO/driver/.proenv" && SWEAP_OS_REPO="$SWEAP_OS_REPO" "$PY" "$REPO/driver/pro_smoke.py" "$SMOKE_IID" >/dev/null 2>&1 ) \
  && echo "READY — env validated (gold patch resolved). Source it: . driver/.proenv" \
  || { echo "SMOKE FAILED — env not ready; run: $VENV/bin/python driver/pro_smoke.py $SMOKE_IID"; exit 1; }
