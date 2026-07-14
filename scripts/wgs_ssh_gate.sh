#!/usr/bin/env bash
set -euo pipefail

WGS_PROJECT_ROOT="${WGS_PROJECT_ROOT:-/mnt/biodevrwbi/33.chenjiucheng/project/airflow-WGS}"
HOST_ENV_FILE="${WGS_HOST_ENV_FILE:-$WGS_PROJECT_ROOT/env/wgs-host.env}"

if [[ -r "$HOST_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$HOST_ENV_FILE"
  set +a
fi

[[ -n "${SSH_ORIGINAL_COMMAND:-}" ]] || {
  echo "A forced WGS command is required." >&2
  exit 2
}

exec "$WGS_PROJECT_ROOT/envs/wgs-snakemake9/bin/python" \
  "$WGS_PROJECT_ROOT/current/dags/wgs_host_runner.py"
