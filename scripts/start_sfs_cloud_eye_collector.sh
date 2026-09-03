#!/usr/bin/env bash
set -euo pipefail

config_root="${SFS_CLOUD_EYE_CONFIG_ROOT:-/home/hanjj/.config/airflow-wgs}"
python_bin="${WGS_PYTHON:-/bi/software/mamba/envs/WGS/bin/python}"
collector="${config_root}/collect_sfs_cloud_eye.py"
pid_file="${config_root}/sfs-cloud-eye.pid"
lock_file="${config_root}/sfs-cloud-eye.lock"
log_file="${config_root}/sfs-cloud-eye.error.log"

if [[ ! -x "${python_bin}" || ! -r "${collector}" ]]; then
  echo "SFS Cloud Eye collector runtime is unavailable" >&2
  exit 1
fi

if [[ -s "${pid_file}" ]]; then
  existing_pid="$(cat "${pid_file}")"
  if [[ "${existing_pid}" =~ ^[0-9]+$ ]] \
    && kill -0 "${existing_pid}" 2>/dev/null \
    && grep -Fq "${collector}" "/proc/${existing_pid}/cmdline" 2>/dev/null; then
    printf '{"status":"running","pid":%s}\n' "${existing_pid}"
    exit 0
  fi
fi

nohup setsid flock -n "${lock_file}" \
  "${python_bin}" "${collector}" --interval-seconds 60 \
  </dev/null >>"${log_file}" 2>&1 &
collector_pid=$!
printf '%s\n' "${collector_pid}" >"${pid_file}"
sleep 1
if ! kill -0 "${collector_pid}" 2>/dev/null; then
  echo "SFS Cloud Eye collector failed to stay running" >&2
  exit 1
fi
printf '{"status":"started","pid":%s}\n' "${collector_pid}"
