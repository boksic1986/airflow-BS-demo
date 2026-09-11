#!/usr/bin/env bash
set -euo pipefail
root=/home/ctapa/.config/airflow-wgs
python=/sg2/33.chenjiucheng/software/miniforge3/envs/nipttest/bin/python
test -r "$root/heavy_global_snapshot.py"
nohup setsid flock -n "$root/heavy-global.lock" "$python" "$root/heavy_global_snapshot.py" \
  --config /home/ctapa/.config/wgs/cce.yaml \
  --root /sg2/50.ctapa/project/HWcloud/airflow-wgs/runtime/cce-evidence \
  </dev/null >>"$root/heavy-global.log" 2>&1 &
