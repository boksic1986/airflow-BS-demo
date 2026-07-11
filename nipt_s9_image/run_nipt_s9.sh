#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 6 ]]; then
  echo "usage: $0 <config_yaml> <workdir> <cores> <owner> <analysis_id> <events_path>" >&2
  exit 2
fi

config_yaml="$1"
workflow_workdir="$2"
snakemake_cores="$3"
chown_uid_gid="$4"
analysis_id="$5"
events_path="$6"

pipeline_root=/code/NIPTPro_pipeline/niptplus
mkdir -p "$(dirname "$events_path")" "$workflow_workdir/logs"
control_owner="$(stat -c '%u:%g' "$workflow_workdir/logs")"
cd "$pipeline_root"

if [[ -x "$pipeline_root/scripts/patch_aneuscreen2_mapper_v2.sh" ]]; then
  "$pipeline_root/scripts/patch_aneuscreen2_mapper_v2.sh"
fi

/opt/conda/bin/python - <<'PY'
from AneuScreen2 import feature_loading

if not hasattr(feature_loading, "mapper_v2_load_aneuscreen_bin"):
    raise SystemExit(f"AneuScreen2 mapper v2 runtime is unavailable: {feature_loading.__file__}")
print("AneuScreen2_mapper_v2_runtime_ready=PASS", feature_loading.__file__)
PY

export PATH="/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export PYTHONPATH="/opt/airflow-demo-plugins${PYTHONPATH:+:$PYTHONPATH}"
export PYTHONUNBUFFERED=1

set +e
/opt/snakemake9/bin/snakemake \
  --snakefile Snakefile \
  --configfile "$config_yaml" \
  --cores "$snakemake_cores" \
  --keep-going \
  --rerun-incomplete \
  --printshellcmds \
  --show-failed-logs \
  --latency-wait 60 \
  --nocolor \
  --directory "$workflow_workdir" \
  --logger airflow-demo \
  --logger-airflow-demo-analysis-id "$analysis_id" \
  --logger-airflow-demo-workdir "$workflow_workdir" \
  --logger-airflow-demo-events-path "$events_path"
status=$?
set -e

if [[ -n "$chown_uid_gid" ]]; then
  chown -R "$chown_uid_gid" "$workflow_workdir" /tmp/NIPTPro@matridx 2>/dev/null || true
  for control_dir in config logs reports; do
    if [[ -e "$workflow_workdir/$control_dir" ]]; then
      chown -R "$control_owner" "$workflow_workdir/$control_dir"
    fi
  done
fi

exit "$status"
