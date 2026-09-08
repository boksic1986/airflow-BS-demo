#!/usr/bin/env bash
set -euo pipefail
umask 007

readonly config_dir="${GATK_HOST_CONFIG_DIR:-/home/ctapa/.config/airflow-gatk}"
readonly runtime_env="${config_dir}/runtime.env"
readonly runtime_gate="${config_dir}/gatk_runtime_gate.py"

if [[ ! -r "${runtime_env}" || ! -r "${runtime_gate}" ]]; then
    echo "GATK restricted runtime is not configured" >&2
    exit 78
fi

set -a
# shellcheck disable=SC1090
source "${runtime_env}"
set +a

if (( $# > 0 )); then
    unset SSH_ORIGINAL_COMMAND
fi

exec "${GATK_PYTHON}" "${runtime_gate}" "$@"
