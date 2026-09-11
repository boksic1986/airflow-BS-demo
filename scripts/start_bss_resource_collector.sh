#!/usr/bin/env bash
set -euo pipefail
root="${BSS_COLLECTOR_CONFIG_ROOT:?set BSS_COLLECTOR_CONFIG_ROOT}"
: "${WGS_PYTHON:?set WGS_PYTHON}"
: "${BSS_EVIDENCE_ROOT:?set BSS_EVIDENCE_ROOT}"
test -x "$WGS_PYTHON"
test -r "$root/collect_bss_resources.py"
test -r "$root/bss_resource_snapshot.py"
test -d "$BSS_EVIDENCE_ROOT"
test ! -L "$BSS_EVIDENCE_ROOT"
# Credentials deliberately optional: absence publishes honest not_configured.
nohup setsid flock -n "$root/bss-resource.lock" "$WGS_PYTHON" "$root/collect_bss_resources.py" \
  --root "$BSS_EVIDENCE_ROOT" </dev/null >>"$root/bss-resource.log" 2>&1 &
