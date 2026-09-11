#!/usr/bin/env bash
set -euo pipefail
root="${HEAVY_COLLECTOR_CONFIG_ROOT:?set HEAVY_COLLECTOR_CONFIG_ROOT}"
python="${WGS_PYTHON:?set WGS_PYTHON}"
: "${CCE_OPERATOR_CONFIG:?set CCE_OPERATOR_CONFIG}"
: "${HEAVY_EVIDENCE_ROOT:?set HEAVY_EVIDENCE_ROOT}"
test -d "$HEAVY_EVIDENCE_ROOT"
test ! -L "$HEAVY_EVIDENCE_ROOT"
test -x "$python"
test -r "$root/heavy_global_snapshot.py"
test -r "$root/heavy_snapshot_core.py"
nohup setsid flock -n "$root/heavy-global.lock" "$python" "$root/heavy_global_snapshot.py" \
  --config "$CCE_OPERATOR_CONFIG" \
  --root "$HEAVY_EVIDENCE_ROOT" \
  </dev/null >>"$root/heavy-global.log" 2>&1 &
