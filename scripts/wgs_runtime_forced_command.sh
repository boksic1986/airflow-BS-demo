#!/usr/bin/env bash
set -euo pipefail
umask 007

readonly config_dir="/home/hanjj/.config/airflow-wgs"
readonly runtime_env="${config_dir}/runtime.env"
readonly runtime_gate="${config_dir}/wgs_runtime_gate.py"

if [[ ! -r "${runtime_env}" || ! -r "${runtime_gate}" ]]; then
    echo "WGS restricted runtime is not configured" >&2
    exit 78
fi

set -a
# shellcheck disable=SC1090
source "${runtime_env}"
set +a

# Airflow invokes this wrapper by its absolute path. In that mode ssh exports
# the full remote command as SSH_ORIGINAL_COMMAND, while the validated command
# is already present in argv. Keep SSH_ORIGINAL_COMMAND only for an
# authorized_keys forced-command invocation, where the wrapper receives no
# positional arguments.
if (( $# > 0 )); then
    unset SSH_ORIGINAL_COMMAND
fi

exec "${WGS_PYTHON}" "${runtime_gate}" "$@"
